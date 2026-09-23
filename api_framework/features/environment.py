"""Behave lifecycle hooks and Allure API evidence."""
from __future__ import annotations

import json
import os

import allure

from core.api_client import ApiClient
from core.execution_state import execution_tracker
from core.security_mask import mask_sensitive_data


def before_all(context):
    context.created_users = []
    context.api_client = ApiClient()
    context.has_real_token = bool(context.api_client.token) and not context.api_client.token.lower().startswith("dummy")
    context.execution_tracker = execution_tracker
    execution_tracker.start_run()


def before_scenario(context, scenario):
    context.execution_tracker.start_test(scenario.name)
    if "requires_auth" in scenario.effective_tags and not context.has_real_token:
        scenario.skip("A valid GOREST_TOKEN is required for authenticated GoRest scenarios.")


def after_scenario(context, scenario):
    status = getattr(scenario.status, "name", str(scenario.status)).upper()
    detail = ""
    if status in {"FAILED", "BROKEN"}:
        failed_step = next((step for step in scenario.steps if getattr(step.status, "name", str(step.status)).upper() == "FAILED"), None)
        detail = failed_step.error_message if failed_step and failed_step.error_message else "See Allure details."
    context.execution_tracker.finish_test(status, detail)


def _request_body(request):
    body = request.body
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return body or ""


def after_step(context, step):
    response = getattr(context, "response", None)
    if response is None or response.request is None:
        return
    request = response.request
    evidence = {
        "Request URL": request.url,
        "Request Method": request.method,
        "Request Headers": dict(request.headers),
        "Request Body": _request_body(request),
        "Response Status": response.status_code,
        "Response Body": response.text,
    }
    allure.attach(
        mask_sensitive_data(json.dumps(evidence, indent=2, default=str)),
        name=f"API evidence - {step.name}",
        attachment_type=allure.attachment_type.JSON,
    )


def after_all(context):
    client = getattr(context, "api_client", None)
    if client is None:
        return
    for user_id in context.created_users:
        try:
            client.delete(f"/users/{user_id}", track_execution=False)
        except Exception as error:
            allure.attach(str(error), name=f"Cleanup failure for user {user_id}", attachment_type=allure.attachment_type.TEXT)
    execution_tracker.finish_run()
