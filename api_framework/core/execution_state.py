"""Small, opt-in execution event store for the local live workflow page."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Any


AUTHENTICATED_WORKFLOW_STAGES = (
    ("STARTED", "Test Started"),
    ("AUTHENTICATING", "Authentication"),
    ("PREPARING_REQUEST", "Prepare Request"),
    ("REQUEST_SENT", "Send Request"),
    ("RESPONSE_RECEIVED", "Receive Response"),
    ("ASSERTIONS_RUNNING", "Validate Response"),
    ("RESULT", "Test Result"),
)

ANONYMOUS_WORKFLOW_STAGES = (
    ("STARTED", "Test Started"),
    ("PREPARING_REQUEST", "Prepare Request"),
    ("REQUEST_SENT", "Send Request"),
    ("RESPONSE_RECEIVED", "Receive Response"),
    ("ASSERTIONS_RUNNING", "Validate Response"),
    ("RESULT", "Test Result"),
)


class ExecutionStateTracker:
    """Persists genuine Behave and HTTP events when EXECUTION_STATE_FILE is set."""

    def __init__(self) -> None:
        configured_path = os.getenv("EXECUTION_STATE_FILE")
        self.path = Path(configured_path).expanduser() if configured_path else None
        self._lock = Lock()
        self._started_at: float | None = None
        self._state: dict[str, Any] = self._new_state()

    @property
    def enabled(self) -> bool:
        return self.path is not None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    @staticmethod
    def _workflow(authenticated: bool | None = None) -> list[dict[str, str]]:
        stages = AUTHENTICATED_WORKFLOW_STAGES if authenticated is not False else ANONYMOUS_WORKFLOW_STAGES
        return [{"id": stage_id, "label": label, "status": "pending"} for stage_id, label in stages]

    def _new_state(self) -> dict[str, Any]:
        return {
            "run_status": "IDLE",
            "updated_at": self._now(),
            "current_test": None,
            "workflow": self._workflow(),
            "summary": {"total": 0, "passed": 0, "failed": 0, "broken": 0, "skipped": 0},
            "events": [],
        }

    def _write(self) -> None:
        if not self.enabled:
            return
        assert self.path is not None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._state["updated_at"] = self._now()
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary_path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        temporary_path.replace(self.path)

    def _event(self, message: str, test_name: str | None = None) -> None:
        active_test = self._state.get("current_test")
        event = {
            "timestamp": self._now(),
            "message": message,
            "test": test_name if test_name is not None else (active_test["name"] if active_test else None),
        }
        self._state["events"] = (self._state["events"] + [event])[-100:]

    def _set_stage(self, stage_id: str, status: str) -> None:
        for stage in self._state["workflow"]:
            if stage["status"] == "running" and stage["id"] != stage_id:
                stage["status"] = "completed"
            if stage["id"] == stage_id:
                stage["status"] = status

    def start_run(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._state = self._new_state()
            self._state["run_status"] = "RUNNING"
            self._event("Execution started")
            self._write()

    def start_test(self, name: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._started_at = perf_counter()
            self._state["current_test"] = {"name": name, "status": "RUNNING", "assertions": {"passed": 0, "failed": 0}}
            self._state["workflow"] = self._workflow(authenticated=None)
            self._state["summary"]["total"] += 1
            self._set_stage("STARTED", "running")
            self._event(f"Test started: {name}")
            self._write()

    def prepare_request(self, authenticated: bool) -> None:
        if not self.enabled:
            return
        with self._lock:
            started_stage = next((stage for stage in self._state["workflow"] if stage["id"] == "STARTED"), None)
            self._state["workflow"] = self._workflow(authenticated=authenticated)
            if started_stage and started_stage["status"] in {"running", "completed"}:
                self._set_stage("STARTED", started_stage["status"])
            if authenticated:
                self._set_stage("AUTHENTICATING", "completed")
                self._set_stage("PREPARING_REQUEST", "running")
                self._event("Authentication header prepared; preparing request")
            else:
                self._set_stage("PREPARING_REQUEST", "running")
                self._event("Preparing request")
            self._write()


    def request_sent(self, method: str, endpoint: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._set_stage("REQUEST_SENT", "running")
            if self._state["current_test"]:
                self._state["current_test"].update({"method": method.upper(), "endpoint": endpoint})
            self._event(f"Request sent: {method.upper()} {endpoint}")
            self._write()

    def response_received(self, status_code: int, elapsed_ms: int) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._set_stage("RESPONSE_RECEIVED", "running")
            if self._state["current_test"]:
                self._state["current_test"].update({"http_status": status_code, "response_time_ms": elapsed_ms})
            self._event(f"Response received: HTTP {status_code} in {elapsed_ms} ms")
            self._write()

    def transition(self, stage_id: str, message: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._set_stage(stage_id, "running")
            self._event(message)
            self._write()

    def assertion_started(self, description: str, expected_http: int | None = None) -> None:
        if self.enabled and expected_http is not None:
            with self._lock:
                if self._state["current_test"]:
                    self._state["current_test"]["expected_http"] = expected_http
                self._set_stage("ASSERTIONS_RUNNING", "running")
                self._event(f"Assertion started: {description}")
                self._write()
            return
        self.transition("ASSERTIONS_RUNNING", f"Assertion started: {description}")

    def assertion_passed(self, description: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            current = self._state["current_test"]
            if current:
                current["assertions"]["passed"] += 1
            self._event(f"Assertion passed: {description}")
            self._write()

    def assertion_failed(self, description: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            current = self._state["current_test"]
            if current:
                current["assertions"]["failed"] += 1
                current["failure_detail"] = description
            self._set_stage("ASSERTIONS_RUNNING", "failed")
            self._event(f"Assertion failed: {description}")
            self._write()

    def finish_test(self, status: str, detail: str = "") -> None:
        if not self.enabled:
            return
        normalized = status.upper()
        if normalized not in {"PASSED", "FAILED", "BROKEN", "SKIPPED"}:
            normalized = "BROKEN"
        with self._lock:
            current = self._state["current_test"]
            if current is None or current.get("status") != "RUNNING":
                return
            self._set_stage("RESULT", "completed" if normalized == "PASSED" else normalized.lower())
            current["status"] = normalized
            current["duration_ms"] = round((perf_counter() - self._started_at) * 1000) if self._started_at else None
            self._state["summary"][normalized.lower()] += 1
            message = f"Test {normalized.lower()}: {current['name']}"
            self._event(f"{message}. {detail}".strip())
            self._write()

    def finish_run(self) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._state["run_status"] = "COMPLETED"
            self._event("Execution completed", test_name="")
            self._write()


execution_tracker = ExecutionStateTracker()
