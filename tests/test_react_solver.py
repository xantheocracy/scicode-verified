"""Exercise the built-in ReAct loop without paid inference or hidden targets."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from inspect_ai import Task, eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.log import read_eval_log
from inspect_ai.model import GenerateConfig, ModelOutput, ModelUsage, get_model
from inspect_ai.tool import ToolCall
from inspect_ai.util import ExecResult

import scicode_inspect as wrapper
import scicode_react as agent


def problem():
    return {
        "problem_id": "21",
        "problem_description_main": "Solve both functions.",
        "problem_background_main": "OPTIONAL_MAIN_BACKGROUND",
        "required_dependencies": "import numpy as np",
        "general_tests": ["HIDDEN_MAIN_TEST"],
        "general_solution": "HIDDEN_GOLD",
        "sub_steps": [
            {
                "step_number": f"21.{i}",
                "step_description_prompt": f"Implement f{i}.",
                "step_background": f"OPTIONAL_BACKGROUND_{i}",
                "function_header": f"def f{i}():",
                "return_line": "return result",
                "test_cases": ["HIDDEN_STEP_TEST"],
                "ground_truth_code": "HIDDEN_GOLD",
            }
            for i in [1, 2]
        ],
    }


def output(calls=None, tokens=5, text="", reasoning=0):
    result = ModelOutput.from_content("mockllm/model", text)
    result.choices[0].message.tool_calls = calls
    result.choices[0].stop_reason = "tool_calls" if calls else "max_tokens"
    result.usage = ModelUsage(
        input_tokens=1000,
        output_tokens=tokens,
        total_tokens=1000 + tokens,
        reasoning_tokens=reasoning,
    )
    return result


def submit(solutions=None):
    return ToolCall(
        id="submit-1",
        function="submit",
        arguments={
            "solutions": solutions
            or {
                "21.1": "def f1(): return 1",
                "21.2": "def f2(): return f1() + 1",
            }
        },
    )


def run_mock(
    tmp_path, outputs, multiplier=10, scorer=None, metadata=None, max_tokens=None
):
    model = get_model(
        "mockllm/model",
        custom_outputs=outputs,
        config=GenerateConfig(max_tokens=max_tokens),
        memoize=False,
    )
    task = Task(
        dataset=MemoryDataset(
            [Sample(id="21", input="21", metadata=metadata or problem())]
        ),
        solver=agent.solve_scicode_react(False, multiplier),
        scorer=scorer,
    )
    environment = AsyncMock()
    environment.exec.return_value = ExecResult(True, 0, "self-check passed", "")
    with (
        patch.object(model, "generate", wraps=model.generate) as generate,
        patch.object(agent, "sandbox", return_value=environment),
    ):
        logs = eval(task, model=model, log_dir=str(tmp_path), display="none")
    assert logs[0].status == "success", logs[0].error
    resolved = read_eval_log(logs[0].location, resolve_attachments=True)
    return resolved.samples[0], generate, environment


def test_whole_problem_prompt_omits_hidden_content():
    prompt = agent.problem_prompt(problem(), False, {})
    assert "21.1" in prompt and "21.2" in prompt
    assert "HIDDEN" not in prompt and "OPTIONAL" not in prompt
    assert "OPTIONAL_MAIN_BACKGROUND" in agent.problem_prompt(problem(), True, {})


def test_budget_countdown_and_terminal_submission(tmp_path):
    sample, generate, environment = run_mock(
        tmp_path,
        [
            output(
                [
                    ToolCall(
                        id="py-1", function="python", arguments={"code": "print(1)"}
                    )
                ],
                reasoning=3,
            ),
            output([submit()]),
        ],
    )
    assert generate.call_count == 2
    assert environment.exec.await_count == 1
    assert [c.kwargs["config"].max_tokens for c in generate.call_args_list] == [10, 10]
    prompts = [e.input for e in sample.events if e.event == "model"]
    assert any("15 generated tokens remaining out of 20" in m.text for m in prompts[1])
    assert any(
        "must submit your complete solution before exhausting" in m.text
        for m in prompts[1]
    )
    report = sample.store[agent.RUN_KEY]
    assert report["output_tokens"] == 10  # Reasoning is included, not double counted.
    assert report["input_tokens"] == 2000
    assert report["termination"] == "submitted"
    assert report["remaining_tokens"] == 10
    assert sample.store["scicode_codes"] == [
        "def f1(): return 1",
        "def f2(): return f1() + 1",
    ]
    assert any(
        m.tool_calls and m.tool_calls[0].function == "submit"
        for m in sample.messages
        if m.role == "assistant"
    )


def test_invalid_submission_can_be_corrected(tmp_path):
    sample, generate, _ = run_mock(
        tmp_path, [output([submit({"21.1": "def f1(): return 1"})]), output([submit()])]
    )
    assert generate.call_count == 2
    assert sample.store[agent.RUN_KEY]["submitted"]
    assert any(m.error for m in sample.messages if m.role == "tool")


def test_exhaustion_does_not_recover_drafts_or_grade_them(tmp_path):
    sample, generate, environment = run_mock(
        tmp_path,
        [
            output(tokens=10, text="def f1(): return 1"),
            output(tokens=10, text="def f2(): return 2"),
        ],
        scorer=wrapper.verify_scicode(sandbox_name="grader"),
    )
    assert generate.call_count == 2
    assert environment.exec.await_count == 0
    assert sample.store[agent.RUN_KEY]["termination"] == "token_limit"
    assert sample.store[agent.SUBMISSION_KEY] is None
    assert sample.store["scicode_codes"] == ["", ""]
    score = next(iter(sample.scores.values()))
    assert score.value == {"21.1": 0.0, "21.2": 0.0}


def test_no_python_execution_after_submit_in_same_turn(tmp_path):
    sample, generate, environment = run_mock(
        tmp_path,
        [
            output(
                [
                    submit(),
                    ToolCall(
                        id="py-late",
                        function="python",
                        arguments={"code": "print('late')"},
                    ),
                ]
            )
        ],
    )
    assert generate.call_count == 1
    assert environment.exec.await_count == 0
    assert sample.store[agent.RUN_KEY]["submitted"]


def test_provided_implementations_are_fixed_and_do_not_add_budget(tmp_path):
    p = problem()
    p["sub_steps"].append({**p["sub_steps"][0], "step_number": "76.3"})
    sample, _, _ = run_mock(tmp_path, [output([submit()])], metadata=p)
    assert sample.store[agent.RUN_KEY]["token_budget"] == 20
    assert "def generate_dna" in sample.store["scicode_codes"][2]


def test_generation_cap_respects_remaining_budget_and_config(tmp_path):
    sample, generate, _ = run_mock(
        tmp_path,
        [output(tokens=7), output(tokens=7), output([submit()], tokens=5)],
        max_tokens=7,
    )
    assert [c.kwargs["config"].max_tokens for c in generate.call_args_list] == [7, 7, 6]
    assert sample.store[agent.RUN_KEY]["remaining_tokens"] == 1


def test_empty_submission_is_not_accepted(tmp_path):
    sample, generate, _ = run_mock(
        tmp_path,
        [
            output(
                [submit({"21.1": "import numpy as np", "21.2": "def f2(): return 2"})]
            ),
            output([submit()]),
        ],
    )
    assert generate.call_count == 2
    assert sample.store[agent.RUN_KEY]["submitted"]


def test_task_mode_and_resource_routing(monkeypatch):
    sample = Sample(
        id="21",
        input="21",
        metadata=problem(),
        files={"test_data_cleaned.h5": "target"},
    )
    monkeypatch.setattr(wrapper, "get_dataset", lambda *a, **k: MemoryDataset([sample]))
    task = wrapper.scicode_verified(solver_mode="react")
    assert sample.files == {"grader:test_data_cleaned.h5": "target"}
    assert "react-compose.yaml" in task.sandbox.config
    # Hawk detects Compose files by suffix, before converting them to Helm values.
    assert Path(task.sandbox.config).name.endswith(("compose.yaml", "compose.yml"))
    assert task.metadata["solver_mode"] == "react"
    assert (
        "react-compose.yaml"
        in wrapper.scicode_verified(
            solver_mode="react", generate_only=True
        ).sandbox.config
    )
    assert (
        wrapper.scicode_verified(generate_only=True).metadata["solver_mode"]
        == "single_call"
    )


@pytest.mark.parametrize(
    "kwargs",
    [{"solver_mode": "bad"}, {"tokens_per_subproblem": 0}, {"python_timeout": 0}],
)
def test_invalid_options(kwargs):
    with pytest.raises(ValueError):
        wrapper.scicode_verified(generate_only=True, **kwargs)
