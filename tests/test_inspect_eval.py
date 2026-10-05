"""Checks for the Inspect wrapper without model API calls or released targets."""

import asyncio
import hashlib
import json
from unittest.mock import AsyncMock, patch

import pytest
import h5py
from inspect_ai import Task, eval
from inspect_ai.model import ChatMessageAssistant, ModelOutput
from inspect_ai.scorer import SampleScore, Score, Target
from inspect_ai.solver import TaskState
from inspect_ai.util import ExecResult

import scicode_inspect as wrapper
from eval_clean.run_deepseek_eval import build_prompt, extract_code


def state_for(problem):
    return TaskState(
        model="mockllm/model",
        sample_id=problem["problem_id"],
        epoch=1,
        input=problem["problem_id"],
        messages=[],
        metadata=problem,
    )


def test_released_dataset():
    dataset = wrapper.get_dataset(require_targets=False)
    assert len(dataset) == 64
    assert "2" not in {sample.id for sample in dataset}
    steps = [step for sample in dataset for step in sample.metadata["sub_steps"]]
    assert len(steps) == 290
    assert (
        sum(step["step_number"] not in wrapper.PROVIDED_STEPS for step in steps) == 287
    )
    assert all(not sample.files for sample in dataset)


def test_manifest_verification(tmp_path, monkeypatch):
    data = tmp_path / "problems_test.jsonl"
    payload = json.dumps({"problem_id": "1", "sub_steps": []}).encode() + b"\n"
    data.write_bytes(payload)
    targets = tmp_path / "targets.h5"
    with h5py.File(targets, "w"):
        pass
    manifest = {
        "version": "test",
        "problem_order": ["1"],
        "problems_test_jsonl_md5": hashlib.md5(payload).hexdigest(),
        "h5_md5": hashlib.md5(targets.read_bytes()).hexdigest(),
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(wrapper, "DATA_DIR", tmp_path)
    monkeypatch.setattr(wrapper.Path, "home", lambda: tmp_path)
    dataset = wrapper.get_dataset(str(targets))
    assert dataset[0].files["test_data_cleaned.h5"] != str(targets)
    targets.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="checksum mismatch"):
        wrapper.get_dataset(str(targets))
    with pytest.raises(FileNotFoundError, match="Download"):
        wrapper.get_dataset(str(tmp_path / "missing.h5"))
    data.write_text("wrong")
    with pytest.raises(ValueError, match="checksum mismatch"):
        wrapper.get_dataset(require_targets=False)


@pytest.mark.parametrize("background", [True, False])
def test_solver_matches_canonical_prompts(background):
    problem = next(
        sample.metadata
        for sample in wrapper.get_dataset(require_targets=False)
        if sample.id == "76"
    )
    state = state_for(problem)
    prompts = []

    async def generate(state):
        prompts.append(state.messages[0].text)
        assert len(state.messages) == 1
        response = "```python\nimport numpy as np\ndef example():\n    return 1\n```"
        state.output = ModelOutput.from_content("mockllm/model", response)
        state.messages.append(ChatMessageAssistant(content=response))
        return state

    result = asyncio.run(wrapper.solve_scicode(background)(state, generate))
    codes = result.store.get("scicode_codes")
    assert len(codes) == len(problem["sub_steps"])
    assert "def generate_dna" in codes[2]
    assert "import numpy" not in codes[0]
    expected = [
        build_prompt(problem, index, codes[:index], background)
        for index, step in enumerate(problem["sub_steps"])
        if step["step_number"] not in wrapper.PROVIDED_STEPS
    ]
    assert prompts == expected


@pytest.mark.parametrize("full_envs", [True, False])
def test_scoring_or_and_skip(full_envs):
    problem = {
        "problem_id": "76",
        "required_dependencies": "import numpy as np",
        "sub_steps": [
            {"step_number": "76.1", "test_cases": ["assert f() == target"]},
            {"step_number": "76.2", "test_cases": ["assert f() == target"]},
            {"step_number": "76.3", "test_cases": []},
            {"step_number": "76.4", "test_cases": ["assert dna() == target"]},
        ],
    }
    state = state_for(problem)
    state.store.set(
        "scicode_codes", ["def f(): return 1", "x = 2", "def dna(): return 3", "y = 4"]
    )
    calls = []

    async def execute(cmd, **kwargs):
        calls.append((cmd, kwargs))
        code = cmd[-1]
        if code.startswith("from scicode.compare"):
            return ExecResult(True, 0, "", "")
        if "'76.2'" in code:
            raise TimeoutError()
        # Step one passes only in the modern environment; step four passes in both.
        success = "'76.4'" in code or cmd[0] == wrapper.GRADING_ENVS["2025"]
        return ExecResult(
            success, 0 if success else 1, "", "" if success else "AssertionError"
        )

    environment = AsyncMock()
    environment.exec.side_effect = execute
    with patch.object(wrapper, "sandbox", return_value=environment):
        result = asyncio.run(
            wrapper.verify_scicode(5, full_envs=full_envs)(state, Target(""))
        )
    assert result.value == {"76.1": 1.0, "76.2": 0.0, "76.4": 1.0}
    breakdown = result.metadata["per_environment"]
    assert len(breakdown["76.1"]) == 2
    assert len(breakdown["76.4"]) == (2 if full_envs else 1)
    scripts = [
        cmd[-1] for cmd, _ in calls if not cmd[-1].startswith("from scicode.compare")
    ]
    assert "def dna(): return 3" in scripts[-1]
    assert "y = 4" not in scripts[0]
    assert all(
        options["timeout_retry"] is False
        for cmd, options in calls
        if cmd[-1] in scripts
    )


def test_grading_setup_failure_raises():
    state = state_for(
        {
            "problem_id": "1",
            "required_dependencies": "",
            "sub_steps": [{"step_number": "1.1", "test_cases": []}],
        }
    )
    state.store.set("scicode_codes", ["pass"])
    environment = AsyncMock()
    environment.exec.return_value = ExecResult(False, 1, "", "missing targets")
    with patch.object(wrapper, "sandbox", return_value=environment):
        with pytest.raises(RuntimeError, match="Grading setup failed"):
            asyncio.run(wrapper.verify_scicode()(state, Target("")))


def test_metrics_weight_steps():
    scores = [
        SampleScore(score=Score(value={"1.1": 1.0})),
        SampleScore(score=Score(value={"2.1": 1.0, "2.2": 0.0, "2.3": 0.0})),
    ]
    assert wrapper.problem_accuracy()(scores) == 0.5
    assert wrapper.subproblem_accuracy()(scores) == 0.5


def test_mock_scoring_log(tmp_path):
    task = Task(
        dataset=wrapper.get_dataset(require_targets=False),
        solver=wrapper.solve_scicode(),
        scorer=wrapper.verify_scicode(),
    )
    environment = AsyncMock()
    environment.exec.return_value = ExecResult(True, 0, "", "")
    with patch.object(wrapper, "sandbox", return_value=environment):
        logs = eval(
            task, model="mockllm/model", limit=1, log_dir=str(tmp_path), display="none"
        )
    assert logs[0].status == "success"
    sample = logs[0].samples[0]
    score = next(iter(sample.scores.values()))
    assert all(value == 1.0 for value in score.value.values())
    assert score.metadata["per_environment"]
    metrics = logs[0].results.scores[0].metrics
    assert metrics["problem_accuracy"].value == 1.0
    assert metrics["subproblem_accuracy"].value == 1.0


def test_mock_generation_log(tmp_path):
    logs = eval(
        wrapper.scicode_verified(generate_only=True),
        model="mockllm/model",
        limit=1,
        log_dir=str(tmp_path),
        display="none",
    )
    assert logs[0].status == "success"
    assert len(logs[0].samples) == 1
    sample = logs[0].samples[0]
    assert len(sample.store["scicode_codes"]) == len(sample.metadata["sub_steps"])
    assert not sample.scores


def test_task_options():
    task = wrapper.scicode_verified(generate_only=True)
    assert task.sandbox is None
    with pytest.raises(ValueError, match="positive"):
        wrapper.scicode_verified(timeout=0, generate_only=True)
    with pytest.raises(ValueError, match="grading_environments"):
        wrapper.verify_scicode(grading_environments="bad")


def test_extractor_parity():
    assert extract_code("```\nimport os\nprint(1)\n```") == "\nprint(1)\n"


def test_target_shards_preserve_groups_and_exclude_other_problems(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(wrapper.Path, "home", lambda: tmp_path)
    targets = tmp_path / "targets.h5"
    with h5py.File(targets, "w") as source:
        group = source.create_group("5.1/test1")
        group.attrs["kind"] = "fixture"
        group.create_dataset("value", data=[1.5, 2.5])
        source.create_group("13.6")
        source.create_group("99.1")
    sample = wrapper.Sample(
        input="5",
        id="5",
        metadata={"sub_steps": [{"step_number": "5.1"}, {"step_number": "13.6"}]},
    )
    wrapper.prepare_target_shards([sample], targets, "fixture")
    shard_path = wrapper.Path(sample.files["test_data_cleaned.h5"])
    with h5py.File(shard_path, "r") as shard:
        assert list(shard) == ["5.1"]
        assert shard["5.1/test1"].attrs["kind"] == "fixture"
        assert list(shard["5.1/test1/value"][()]) == [1.5, 2.5]
    before = shard_path.stat().st_mtime_ns
    wrapper.prepare_target_shards([sample], targets, "fixture")
    assert shard_path.stat().st_mtime_ns == before
    sample.metadata["sub_steps"] = [{"step_number": "missing"}]
    with pytest.raises(ValueError, match="missing step"):
        wrapper.prepare_target_shards([sample], targets, "fixture")
    assert not wrapper.Path(sample.files["test_data_cleaned.h5"]).exists()
    assert not list(shard_path.parent.glob("*.partial"))
