"""Fixed JSON transport for the AI v2 public API. Submitted code is never run here."""

import asyncio
import base64
from contextlib import redirect_stdout
import json
import sys


def project_request(payload: dict):
    from ai.src.api import ProjectRequest
    raw = dict(payload)
    # Decode the wire encoding to the original bytes required by the AI contract.
    raw["documents"] = [
        {"filename": item["filename"], "media_type": item["media_type"],
         "content": base64.b64decode(item["content_base64"], validate=True)}
        for item in raw.get("documents", [])
    ]
    return ProjectRequest.model_validate(raw)


async def dispatch(message: dict):
    from ai.src.api import (
        ProjectDraft, SampleDataset, Submission, TaskSpec,
        ask_clarifying_questions, evaluate_submission, flush_tracing,
        generate_followup_questions, generate_project, revise_project,
    )
    operation, payload = message.get("operation"), message.get("payload", {})
    context = {key: message[key] for key in ("user_id", "session_id") if key in message}
    if not all(isinstance(value, str) and len(value) <= 200 for value in context.values()):
        raise ValueError("Context must contain short internal IDs")
    try:
        if operation == "clarify":
            result = await ask_clarifying_questions(project_request(payload["request"]), **context)
        elif operation == "generate":
            result = await generate_project(project_request(payload["request"]), **context)
        elif operation == "revise":
            result = await revise_project(
                project_request(payload["request"]), ProjectDraft.model_validate(payload["draft"]),
                payload["feedback"], **context,
            )
        elif operation == "followup":
            result = await generate_followup_questions(
                TaskSpec.model_validate(payload["task"]), Submission.model_validate(payload["submission"]), **context,
            )
        elif operation == "evaluate":
            result = await evaluate_submission(
                TaskSpec.model_validate(payload["task"]), SampleDataset.model_validate(payload["dataset"]),
                Submission.model_validate(payload["submission"]), **context,
            )
        else:
            raise ValueError("Unsupported public AI operation")
        return [item.model_dump(mode="json") for item in result] if isinstance(result, list) else result.model_dump(mode="json")
    finally:
        flush_tracing()


def main() -> int:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        raw = sys.stdin.buffer.read(2_100_001)
        if len(raw) > 2_100_000:
            raise ValueError("Input too large")
        message = json.loads(raw.decode("utf-8"))
        if not isinstance(message, dict):
            raise ValueError("Expected JSON object")
        with redirect_stdout(sys.stderr):
            result = asyncio.run(dispatch(message))
        json.dump({"ok": True, "result": result}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    except Exception as error:
        json.dump({"ok": False, "error": type(error).__name__}, sys.stdout)
        sys.stdout.write("\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
