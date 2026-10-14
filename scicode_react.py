"""Whole-problem SciCode solving using Inspect's built-in ReAct agent."""

import json
from typing import Any

from inspect_ai.agent import AgentPrompt, AgentState, AgentSubmit, react, run
from inspect_ai.model import ChatMessageUser, GenerateConfig, get_model
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import Tool, ToolDef, ToolError, tool
from inspect_ai.util import sandbox, token_limit

from eval_clean.run_deepseek_eval import extract_code

RUN_KEY = "scicode_react_run"
SUBMISSION_KEY = "scicode_react_submission"


def countdown(remaining: int, total: int) -> str:
    return (
        f"You have {max(0, remaining):,} generated tokens remaining out of {total:,}. "
        "Use the available budget for careful reasoning, meaningful Python checks, "
        "and reviewing your assumptions before submitting. "
        "You must submit your complete solution before exhausting this budget to "
        "complete the task successfully. Calling submit ends the attempt immediately. "
        "You may submit as soon as you are ready; you do not need to use all remaining tokens."
    )


def problem_prompt(
    problem: dict[str, Any], background: bool, provided: dict[str, str]
) -> str:
    """Present all task descriptions, never tests, targets, or reference solutions."""
    sections = [
        f"Programming problem {problem['problem_id']}",
        "Required dependencies:\n" + problem["required_dependencies"],
    ]
    for step in problem["sub_steps"]:
        sid = step["step_number"]
        section = [f"Subproblem {sid}", step.get("step_description_prompt") or ""]
        if background:
            section.append(step.get("step_background") or "")
        section.extend(
            [step.get("function_header") or "", step.get("return_line") or ""]
        )
        if sid in provided:
            section.append(
                "Fixed author-provided implementation:\n```python\n"
                + provided[sid]
                + "\n```"
            )
        sections.append("\n\n".join(section))
    return "\n\n".join(sections)


@solver
def solve_scicode_react(
    provide_scientific_background: bool = True,
    tokens_per_subproblem: int = 20_000,
    python_timeout: int = 60,
) -> Solver:
    """One conversation and one terminal submission under a shared output budget."""
    if tokens_per_subproblem <= 0 or python_timeout <= 0:
        raise ValueError("tokens_per_subproblem and python_timeout must be positive.")

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        from scicode_inspect import PROVIDED_STEPS, THREAD_ENV, VENDOR

        steps = state.metadata["sub_steps"]
        step_ids = [
            step["step_number"]
            for step in steps
            if step["step_number"] not in PROVIDED_STEPS
        ]
        provided = {
            step["step_number"]: extract_code(
                (VENDOR / "eval_data" / f"{step['step_number']}.txt").read_text()
            )
            for step in steps
            if step["step_number"] in PROVIDED_STEPS
        }
        total = tokens_per_subproblem * len(step_ids)
        budget = token_limit(total, type="output")
        inputs = token_limit(None, type="input")
        submission: dict[str, str] | None = None
        state.store.set(SUBMISSION_KEY, None)

        @tool
        def python_checks() -> Tool:
            async def execute(code: str) -> str:
                """Run Python experiments and self-written tests.

                Each call starts a fresh process. Required imports are loaded;
                official tests, target data and grading feedback are unavailable.

                Args:
                    code: Python implementations or self-written checks to execute.
                """
                if submission is not None:
                    return "Attempt complete. No further Python execution is allowed."
                try:
                    result = await sandbox().exec(
                        [
                            "python3",
                            "-c",
                            state.metadata["required_dependencies"] + "\n" + code,
                        ],
                        env=THREAD_ENV,
                        timeout=python_timeout,
                        timeout_retry=False,
                    )
                except TimeoutError as exc:
                    raise ToolError("Python execution timed out.") from exc
                # Bound tool observations without truncating the submitted code.
                return f"Exit code: {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"

            return execute

        @tool
        def submit_solution() -> Tool:
            async def execute(solutions: dict[str, str]) -> str:
                """Submit the complete main-problem solution and END the attempt.

                Include every model-generated subproblem, even if unchanged.
                No further model turns or correctness feedback follow a valid submission.

                Args:
                    solutions: Subproblem IDs mapped to Python implementations,
                        without dependency imports or tests. Do not include author-provided steps.
                """
                nonlocal submission
                if submission is not None:
                    return json.dumps(submission)
                if set(solutions) != set(step_ids):
                    raise ToolError(
                        f"Include all and only these subproblem IDs: {step_ids}"
                    )
                code = {sid: extract_code(solutions[sid]).strip() for sid in step_ids}
                if any(not value for value in code.values()):
                    raise ToolError(
                        "Every subproblem requires a nonempty implementation."
                    )
                submission = code
                state.store.set(SUBMISSION_KEY, code)
                return json.dumps(code)

            return execute

        async def bounded_generate(
            agent_state: AgentState, tools: list[Tool]
        ) -> AgentState:
            """Cap each generation while letting the built-in agent own its tool loop."""
            remaining = max(0, int(budget.remaining or 0))
            if remaining == 0:
                budget.check(raise_for_equal=True)
            model = get_model()
            # The shared budget may exceed a provider's per-response maximum.
            # Default each response to the multiplier; --max-tokens can override it.
            configured_cap = model.config.max_tokens or tokens_per_subproblem
            cap = min(remaining, configured_cap)
            agent_state.output = await model.generate(
                agent_state.messages,
                tools,
                config=GenerateConfig(max_tokens=cap, parallel_tool_calls=False),
            )
            if agent_state.output.usage is None:
                raise RuntimeError(
                    "Model usage is required to enforce the generated-token budget."
                )
            agent_state.messages.append(agent_state.output.message)
            return agent_state

        async def continue_problem(agent_state: AgentState) -> str | bool:
            if submission is not None:
                return False
            return countdown(int(budget.remaining or 0), total)

        agent = react(
            prompt=AgentPrompt(
                instructions=(
                    "Solve every model-generated subproblem in this main problem together. "
                    "You may work in any order and revise any implementation before submitting. "
                    "Author-provided implementations are fixed. Python is available for your own checks. "
                    "Hidden tests and targets are unavailable, and you receive no official grading feedback. "
                    "Use the available budget to develop and verify a well-supported solution. "
                    "Take advantage of multiple turns: reason through the requirements, implement, "
                    "run self-written tests, inspect the results, and revise when needed. "
                    "Check mathematical assumptions, units, boundary cases, and dependencies between subproblems. "
                    "Compare outputs with independently derived expected values or useful invariants; "
                    "merely obtaining finite values or code that runs is not enough to establish correctness. "
                    "If an important uncertainty remains, use another turn to investigate it rather than "
                    "submitting the first plausible implementation. Before submitting, review all implementations "
                    "together for consistency and correctness. You may finish early once satisfied with your "
                    "reasoning and checks; you do not need to spend tokens or take turns without a useful purpose. "
                    "Submit implementations for these IDs: "
                    + json.dumps(step_ids)
                    + ". "
                    + countdown(total, total)
                ),
                handoff_prompt=None,
            ),
            tools=[ToolDef(python_checks(), name="python", parallel=False)],
            submit=AgentSubmit(
                tool=ToolDef(
                    submit_solution(), name="submit", parallel=False, max_output=0
                ),
                answer_only=True,
                keep_in_messages=True,
            ),
            attempts=1,
            on_continue=continue_problem,
            model=bounded_generate,
        )
        agent_state, limit_error = await run(
            agent,
            [
                ChatMessageUser(
                    content=problem_prompt(
                        state.metadata, provide_scientific_background, provided
                    )
                )
            ],
            limits=[budget, inputs],
            name=f"Programming problem {state.sample_id}",
        )
        state.messages = agent_state.messages
        state.output = agent_state.output
        state.store.set(
            "scicode_codes",
            [
                provided.get(
                    step["step_number"], (submission or {}).get(step["step_number"], "")
                )
                for step in steps
            ],
        )
        state.store.set(
            RUN_KEY,
            {
                "solver_mode": "react",
                "token_budget": total,
                "tokens_per_subproblem": tokens_per_subproblem,
                "scored_subproblems": len(step_ids),
                "input_tokens": int(inputs.usage),
                "output_tokens": int(budget.usage),
                "remaining_tokens": max(0, int(budget.remaining or 0)),
                "submitted": submission is not None,
                "termination": "submitted"
                if submission is not None
                else "token_limit"
                if limit_error
                else "no_submission",
                "limit_error": str(limit_error) if limit_error else None,
            },
        )
        return state

    return solve
