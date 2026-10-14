"""Opt-in container test: real isolation and OR grading, mocked model responses."""

import os

import h5py
import pytest
from inspect_ai import Task, eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ModelOutput, ModelUsage, get_model
from inspect_ai.tool import ToolCall

import scicode_inspect as wrapper
from scicode_react import solve_scicode_react


@pytest.mark.skipif(
    os.environ.get("SCICODE_DOCKER_TESTS") != "1",
    reason="Set SCICODE_DOCKER_TESTS=1 with sandbox images built.",
)
def test_python_isolation_and_two_environment_grading(tmp_path):
    target = tmp_path / "targets.h5"
    with h5py.File(target, "w") as file:
        for sid, value in [("21.1", 1), ("21.2", 2)]:
            file.create_dataset(f"{sid}/test1/var1", data=value)
    problem = {
        "problem_id": "21",
        "problem_description_main": "Implement two functions.",
        "required_dependencies": "import numpy as np",
        "sub_steps": [
            {
                "step_number": f"21.{i}",
                "step_description_prompt": f"Implement f{i}.",
                "function_header": f"def f{i}():",
                "return_line": "return result",
                "test_cases": [f"assert f{i}() == target"],
            }
            for i in [1, 2]
        ],
    }
    checks = """import importlib.util, pathlib
assert np.__version__ == '2.4.2'
assert importlib.util.find_spec('scicode') is None
assert not pathlib.Path('/opt/scicode-vendor').exists()
assert not list(pathlib.Path('/workspace').rglob('*.h5'))
print('Agent isolation verified; Python self-checks work.')
"""
    solutions = {
        "21.1": "def f1(): return np.trapezoid([1, 1])",
        "21.2": "def f2(): return f1() + 1",
    }
    outputs = []
    for call in [
        ToolCall(id="check", function="python", arguments={"code": checks}),
        ToolCall(id="final", function="submit", arguments={"solutions": solutions}),
    ]:
        output = ModelOutput.from_content("mockllm/model", "")
        output.choices[0].message.tool_calls = [call]
        output.choices[0].stop_reason = "tool_calls"
        output.usage = ModelUsage(input_tokens=1000, output_tokens=5, total_tokens=1005)
        outputs.append(output)
    task = Task(
        dataset=MemoryDataset(
            [
                Sample(
                    id="21",
                    input="21",
                    metadata=problem,
                    files={"grader:test_data_cleaned.h5": str(target)},
                )
            ]
        ),
        solver=solve_scicode_react(False),
        scorer=wrapper.verify_scicode(sandbox_name="grader"),
        sandbox=("docker", str(wrapper.ROOT / "eval_clean/inspect/compose.react.yaml")),
    )
    logs = eval(
        task,
        model=get_model("mockllm/model", custom_outputs=outputs, memoize=False),
        log_dir=str(tmp_path / "logs"),
        display="none",
    )
    assert logs[0].status == "success", logs[0].error
    sample = logs[0].samples[0]
    assert any(
        "Agent isolation verified" in message.text
        for message in sample.messages
        if message.role == "tool"
    )
    score = next(iter(sample.scores.values()))
    assert score.value == {"21.1": 1.0, "21.2": 1.0}
    for result in score.metadata["per_environment"].values():
        assert not result["2024"]["passed"]
        assert result["2025"]["passed"]
