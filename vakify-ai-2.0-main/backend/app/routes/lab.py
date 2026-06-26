from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import ChatHistory, ChatThreadMessage, CodeLabSubmission, CodeLabTask, DailyTask, LabWorkspaceState
from app.services.code_lab_service import (
    generate_lab_task_from_chat,
    get_challenge,
    list_challenges,
    run_code,
)


lab_bp = Blueprint("lab", __name__, url_prefix="/api/lab")


def _serialize_task(task: CodeLabTask) -> dict:
    return {
        "task_id": task.task_id,
        "user_id": task.user_id,
        "language": task.language,
        "task_key": task.task_key,
        "title": task.title,
        "description": task.description,
        "starter_code": task.starter_code,
        "sample_input": task.sample_input or "",
        "expected_output": task.expected_output or "",
        "hint": task.hint or "",
        "source_chat_id": task.source_chat_id,
        "source_thread_id": task.source_thread_id,
        "source_question": task.source_question,
        "source_answer": task.source_answer,
        "validation_json": task.validation_json or [],
        "is_active": task.is_active,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


def _latest_chat_for_user(user_id: int) -> ChatHistory | None:
    return ChatHistory.query.filter_by(user_id=user_id).order_by(ChatHistory.timestamp.desc()).first()


def _latest_thread_id_for_chat(chat_id: int, user_id: int) -> int | None:
    row = ChatThreadMessage.query.filter_by(chat_id=chat_id, user_id=user_id).first()
    return row.thread_id if row else None


def _build_validation_tests(task: CodeLabTask | DailyTask | None, result: dict, source_code: str) -> list[dict]:
    normalized = (source_code or "").lower()
    tests = [
        {"name": "Program compiled or executed", "passed": result.get("status") == "success"},
    ]

    if task:
        content = getattr(task, "content_json", None) or {}
        expected = (getattr(task, "expected_output", None) or content.get("expected_output") or "").strip()
        if expected:
            stdout = (result.get("stdout") or "").strip()
            tests.append(
                {
                    "name": "Matches sample output",
                    "passed": expected == stdout or expected in stdout,
                }
            )
        validations_source = getattr(task, "validation_json", None) or content.get("validation_json") or []
        validations = [str(item).strip().lower() for item in validations_source if str(item).strip()]
        for item in validations[:3]:
            tests.append(
                {
                    "name": f"Uses {item}",
                    "passed": item in normalized,
                }
            )
        hint = (getattr(task, "hint", None) or content.get("hint") or "").strip()
        if hint:
            tests.append(
                {
                    "name": "Hint-related concept present",
                    "passed": any(word in normalized for word in hint.lower().split()[:3]),
                }
            )
    else:
        tests.extend(
            [
                {"name": "Task available", "passed": False},
                {"name": "Expected output matched", "passed": False},
                {"name": "Validation tags matched", "passed": False},
            ]
        )

    while len(tests) < 4:
        tests.append({"name": f"Check {len(tests) + 1}", "passed": False})
    return tests[:4]


def _fallback_task_payload(language: str) -> dict:
    return {
        **get_challenge(language),
        "task_id": None,
        "user_id": None,
        "source_chat_id": None,
        "source_thread_id": None,
        "source_question": None,
        "source_answer": None,
        "validation_json": [],
        "is_active": False,
    }


def _current_task_for_user(user_id: int, language: str) -> CodeLabTask | None:
    language_key = (language or "python").strip().lower()
    if language_key in {"js", "javascript", "node"}:
        language_key = "javascript"
    elif language_key == "cpp":
        language_key = "c++"
    elif language_key not in {"python", "javascript", "java", "c", "c++"}:
        language_key = "python"

    return (
        CodeLabTask.query.filter_by(user_id=user_id, language=language_key, is_active=True)
        .order_by(CodeLabTask.updated_at.desc())
        .first()
    )


def _daily_task_for_user(user_id: int, task_id: int) -> DailyTask | None:
    return DailyTask.query.filter_by(task_id=task_id, user_id=user_id).first()


def _workspace_key(workspace_type: str, language: str, task_id: int | None) -> tuple[str, str, int | None]:
    workspace = (workspace_type or "training").strip().lower()
    if workspace not in {"training", "chat"}:
        workspace = "training"
    language_key = (language or "python").strip().lower()
    if language_key in {"js", "node"}:
        language_key = "javascript"
    if language_key == "cpp":
        language_key = "c++"
    if language_key not in {"python", "javascript", "java", "c", "c++"}:
        language_key = "python"
    return workspace, language_key, task_id


def _serialize_workspace_state(state: LabWorkspaceState | None) -> dict:
    if not state:
        return {
            "state_id": None,
            "workspace_type": "training",
            "language": "python",
            "task_id": None,
            "chat_id": None,
            "thread_id": None,
            "source_task_key": None,
            "code": "",
            "stdin": "",
            "last_output": "",
            "last_error": "",
            "last_tests_json": [],
            "last_score": 0,
            "last_status": "draft",
            "created_at": None,
            "updated_at": None,
        }
    return {
        "state_id": state.state_id,
        "workspace_type": state.workspace_type,
        "language": state.language,
        "task_id": state.task_id,
        "chat_id": state.chat_id,
        "thread_id": state.thread_id,
        "source_task_key": state.source_task_key,
        "code": state.code or "",
        "stdin": state.stdin or "",
        "last_output": state.last_output or "",
        "last_error": state.last_error or "",
        "last_tests_json": state.last_tests_json or [],
        "last_score": state.last_score,
        "last_status": state.last_status,
        "created_at": state.created_at.isoformat(),
        "updated_at": state.updated_at.isoformat(),
    }


def _load_workspace_state(user_id: int, workspace_type: str, language: str, task_id: int | None) -> LabWorkspaceState | None:
    workspace, language_key, task_id = _workspace_key(workspace_type, language, task_id)
    return LabWorkspaceState.query.filter_by(
        user_id=user_id,
        workspace_type=workspace,
        language=language_key,
        task_id=task_id,
    ).first()


def _upsert_workspace_state(
    user_id: int,
    workspace_type: str,
    language: str,
    task_id: int | None,
    *,
    code: str | None = None,
    stdin: str | None = None,
    chat_id: int | None = None,
    thread_id: int | None = None,
    source_task_key: str | None = None,
    last_output: str | None = None,
    last_error: str | None = None,
    last_tests_json: list[dict] | None = None,
    last_score: int | None = None,
    last_status: str | None = None,
) -> LabWorkspaceState:
    workspace, language_key, task_id = _workspace_key(workspace_type, language, task_id)
    state = LabWorkspaceState.query.filter_by(
        user_id=user_id,
        workspace_type=workspace,
        language=language_key,
        task_id=task_id,
    ).first()
    if not state:
        state = LabWorkspaceState(
            user_id=user_id,
            workspace_type=workspace,
            language=language_key,
            task_id=task_id,
        )
        db.session.add(state)

    if code is not None:
        state.code = code
    if stdin is not None:
        state.stdin = stdin
    if chat_id is not None:
        state.chat_id = chat_id
    if thread_id is not None:
        state.thread_id = thread_id
    if source_task_key is not None:
        state.source_task_key = source_task_key
    if last_output is not None:
        state.last_output = last_output
    if last_error is not None:
        state.last_error = last_error
    if last_tests_json is not None:
        state.last_tests_json = last_tests_json
    if last_score is not None:
        state.last_score = last_score
    if last_status is not None:
        state.last_status = last_status
    state.updated_at = datetime.utcnow()
    return state


@lab_bp.get("/challenges")
@jwt_required()
def challenges():
    return jsonify({"challenges": list_challenges()})


@lab_bp.get("/challenge")
@jwt_required()
def challenge():
    language = (request.args.get("language") or "python").strip().lower()
    return jsonify(get_challenge(language))


@lab_bp.get("/task")
@jwt_required()
def current_task():
    user_id = int(get_jwt_identity())
    language = (request.args.get("language") or "python").strip().lower()
    task = _current_task_for_user(user_id, language)
    return jsonify(_serialize_task(task) if task else _fallback_task_payload(language))


@lab_bp.get("/workspace")
@jwt_required()
def get_workspace():
    user_id = int(get_jwt_identity())
    workspace_type = (request.args.get("workspace_type") or "training").strip().lower()
    language = (request.args.get("language") or "python").strip().lower()
    task_id_raw = request.args.get("task_id")
    try:
        task_id = int(task_id_raw) if task_id_raw not in {None, "", 0, "0"} else None
    except (TypeError, ValueError):
        return jsonify({"error": "task_id must be a number"}), 400

    state = _load_workspace_state(user_id, workspace_type, language, task_id)
    return jsonify({"workspace": _serialize_workspace_state(state)})


@lab_bp.put("/workspace")
@jwt_required()
def save_workspace():
    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}
    workspace_type = str(payload.get("workspace_type", "training")).strip().lower()
    language = str(payload.get("language", "python")).strip().lower()
    task_id_raw = payload.get("task_id")
    try:
        task_id = int(task_id_raw) if task_id_raw not in {None, "", 0, "0"} else None
    except (TypeError, ValueError):
        return jsonify({"error": "task_id must be a number"}), 400

    code = str(payload.get("code", ""))
    stdin = str(payload.get("stdin", ""))
    chat_id_raw = payload.get("chat_id")
    thread_id_raw = payload.get("thread_id")
    try:
        chat_id = int(chat_id_raw) if chat_id_raw not in {None, "", 0, "0"} else None
    except (TypeError, ValueError):
        chat_id = None
    try:
        thread_id = int(thread_id_raw) if thread_id_raw not in {None, "", 0, "0"} else None
    except (TypeError, ValueError):
        thread_id = None

    source_task_key = str(payload.get("source_task_key") or "").strip() or None
    last_output = str(payload.get("last_output") or "")
    last_error = str(payload.get("last_error") or "")
    last_tests_json = payload.get("last_tests_json")
    if not isinstance(last_tests_json, list):
        last_tests_json = None
    try:
        last_score = int(payload.get("last_score")) if payload.get("last_score") is not None else None
    except (TypeError, ValueError):
        last_score = None
    last_status = str(payload.get("last_status") or "").strip().lower() or None

    state = _upsert_workspace_state(
        user_id,
        workspace_type,
        language,
        task_id,
        code=code,
        stdin=stdin,
        chat_id=chat_id,
        thread_id=thread_id,
        source_task_key=source_task_key,
        last_output=last_output,
        last_error=last_error,
        last_tests_json=last_tests_json,
        last_score=last_score,
        last_status=last_status,
    )
    db.session.commit()
    return jsonify({"workspace": _serialize_workspace_state(state)})


@lab_bp.post("/task/sync")
@jwt_required()
def sync_task_from_chat():
    user_id = int(get_jwt_identity())
    payload = request.get_json(silent=True) or {}
    language = str(payload.get("language", "python")).strip().lower()
    try:
        chat_id = int(payload.get("chat_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "chat_id is required"}), 400

    chat = ChatHistory.query.filter_by(chat_id=chat_id, user_id=user_id).first()
    if not chat:
        return jsonify({"error": "chat not found"}), 404

    thread_id = _latest_thread_id_for_chat(chat.chat_id, user_id)
    generated = generate_lab_task_from_chat(chat.question, chat.response, language)
    existing = _current_task_for_user(user_id, generated["language"])
    if existing:
        existing.is_active = False

    task = CodeLabTask(
        user_id=user_id,
        language=generated["language"],
        task_key=generated["task_key"],
        title=generated["title"],
        description=generated["description"],
        starter_code=generated["starter_code"],
        sample_input=generated["sample_input"],
        expected_output=generated["expected_output"],
        hint=generated["hint"],
        source_chat_id=chat.chat_id,
        source_thread_id=thread_id,
        source_question=chat.question,
        source_answer=chat.response[:4000],
        validation_json=generated["validation_json"],
        is_active=True,
    )
    db.session.add(task)
    db.session.commit()
    return jsonify(_serialize_task(task))


@lab_bp.post("/run")
@jwt_required()
def run():
    user_id = int(get_jwt_identity())
    payload = request.get_json() or {}
    source_code = str(payload.get("source_code", "")).rstrip()
    language = str(payload.get("language", "python")).strip().lower()
    task_id = payload.get("task_id")
    try:
        task_id = int(task_id) if task_id not in {None, "", 0} else None
    except (TypeError, ValueError):
        return jsonify({"error": "task_id must be a number"}), 400
    challenge_key = str(payload.get("challenge_key", "")).strip()
    title = str(payload.get("title", "")).strip()
    stdin_text = str(payload.get("stdin", ""))

    if not source_code.strip():
        return jsonify({"error": "source_code is required"}), 400

    task = None
    daily_task = None
    if task_id is not None:
        task = CodeLabTask.query.filter_by(task_id=task_id, user_id=user_id).first()
        if task:
            language = task.language
            challenge_key = challenge_key or task.task_key
            title = title or task.title
            if not stdin_text.strip():
                stdin_text = task.sample_input or ""
        else:
            daily_task = _daily_task_for_user(user_id, task_id)
            if not daily_task:
                return jsonify({"error": "task not found"}), 404
            content = daily_task.content_json or {}
            language = str(content.get("language") or language or "python").strip().lower()
            challenge_key = challenge_key or str(content.get("task_key") or f"daily-{daily_task.task_id}")
            title = title or daily_task.title
            if not stdin_text.strip():
                stdin_text = str(content.get("sample_input") or "")

    if not challenge_key:
        challenge_key = get_challenge(language)["key"]
    if not title:
        if task:
            title = task.title
        elif daily_task:
            title = daily_task.title
        else:
            title = get_challenge(language)["title"]

    result = run_code(language, source_code, stdin_text)
    tests = result.get("tests", [])
    passed_tests = sum(1 for item in tests if item.get("passed"))
    total_tests = len(tests)
    score = int(round((passed_tests / total_tests) * 100)) if total_tests else 0
    if task or daily_task:
        tests = _build_validation_tests(task or daily_task, result, source_code)
        passed_tests = sum(1 for item in tests if item.get("passed"))
        total_tests = len(tests)
        score = int(round((passed_tests / total_tests) * 100)) if total_tests else 0

    row = CodeLabSubmission(
        user_id=user_id,
        task_id=(task.task_id if task else daily_task.task_id if daily_task else None),
        language=result.get("language", language),
        challenge_key=challenge_key,
        title=title,
        source_code=source_code,
        stdout=result.get("stdout", ""),
        stderr=result.get("stderr", ""),
        status=result.get("status", "error"),
        passed_tests=passed_tests,
        total_tests=total_tests,
        score=score,
    )
    db.session.add(row)

    workspace_type = "chat" if task else "training"
    workspace_task_id = task.task_id if task else daily_task.task_id if daily_task else None
    workspace_language = result.get("language", language)
    workspace_source_task_key = task.task_key if task else str((daily_task.content_json or {}).get("task_key") or "") if daily_task else None
    _upsert_workspace_state(
        user_id,
        workspace_type,
        workspace_language,
        workspace_task_id,
        code=source_code,
        stdin=stdin_text,
        chat_id=task.source_chat_id if task else None,
        thread_id=task.source_thread_id if task else None,
        source_task_key=workspace_source_task_key or None,
        last_output=result.get("stdout", ""),
        last_error=result.get("stderr", ""),
        last_tests_json=tests,
        last_score=score,
        last_status=result.get("status", "error"),
    )
    db.session.commit()

    return jsonify(
        {
            **result,
            "submission_id": row.submission_id,
            "task": _serialize_task(task) if task else None,
            "daily_task": None
            if not daily_task
            else {
                "task_id": daily_task.task_id,
                "title": daily_task.title,
                "description": daily_task.description,
                "task_type": daily_task.task_type,
                "difficulty": daily_task.difficulty,
                "status": daily_task.status,
                "points_reward": daily_task.points_reward,
                "due_date": daily_task.due_date.isoformat(),
                "content": daily_task.content_json or {},
            },
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "score": score,
        }
    )


@lab_bp.get("/submissions")
@jwt_required()
def submissions():
    user_id = int(get_jwt_identity())
    rows = (
        CodeLabSubmission.query.filter_by(user_id=user_id)
        .order_by(CodeLabSubmission.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify(
        {
            "rows": [
                {
                    "submission_id": row.submission_id,
                    "task_id": row.task_id,
                    "language": row.language,
                    "challenge_key": row.challenge_key,
                    "title": row.title,
                    "status": row.status,
                    "score": row.score,
                    "passed_tests": row.passed_tests,
                    "total_tests": row.total_tests,
                    "stdout": row.stdout,
                    "stderr": row.stderr,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        }
    )
