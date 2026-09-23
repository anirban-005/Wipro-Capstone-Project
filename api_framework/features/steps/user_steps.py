"""BDD steps for GoRest user API coverage."""
from __future__ import annotations

import json
from pathlib import Path

from behave import given, step, then, when
from jsonschema import Draft202012Validator, FormatChecker

from core.api_client import ApiClient
from core.execution_state import execution_tracker
from data.payload_factory import UserPayloadFactory


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "user_schema.json"
USER_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
USER_VALIDATOR = Draft202012Validator(USER_SCHEMA, format_checker=FormatChecker())


@given("I create a new GoRest user")
@when("I create a new GoRest user")
def create_user(context):
    context.payload = UserPayloadFactory.create()
    context.response = context.api_client.post("/users", json=context.payload)
    if context.response.status_code == 201:
        context.user_id = context.response.json()["id"]
        context.created_users.append(context.user_id)


@when("I fetch the created GoRest user")
def fetch_created_user(context):
    context.response = context.api_client.get(f"/users/{context.user_id}")


@when("I update the created GoRest user details")
def update_created_user(context):
    context.update_payload = UserPayloadFactory.create_update_payload()
    context.response = context.api_client.patch(
        f"/users/{context.user_id}", json=context.update_payload
    )


@step("the user response should reflect the updated details")
def verify_updated_details(context):
    execution_tracker.assertion_started("updated user details")
    data = context.response.json()
    try:
        for key, expected_value in context.update_payload.items():
            assert data.get(key) == expected_value, (
                f"Expected updated '{key}' to be '{expected_value}', got '{data.get(key)}'"
            )
    except AssertionError:
        execution_tracker.assertion_failed("updated user details")
        raise
    execution_tracker.assertion_passed("updated user details")


@when("I create a GoRest user without an authentication token")
def create_user_without_token(context):
    context.payload = UserPayloadFactory.create()
    anonymous_client = ApiClient(token="")
    context.response = anonymous_client.post("/users", json=context.payload, authenticated=False)


@when("I fetch non-existent GoRest user ID 999999999")
def fetch_missing_user(context):
    context.response = context.api_client.get("/users/999999999", authenticated=False)


@step("the response status should be {expected_status:d}")
def verify_status(context, expected_status):
    execution_tracker.assertion_started(f"HTTP status is {expected_status}", expected_http=expected_status)
    try:
        assert context.response.status_code == expected_status, (
            f"Expected HTTP {expected_status}, received {context.response.status_code}: {context.response.text}"
        )
    except AssertionError:
        execution_tracker.assertion_failed(f"HTTP status is {expected_status}")
        raise
    execution_tracker.assertion_passed(f"HTTP status is {expected_status}")


@step("the user response should match the user schema")
def verify_user_schema(context):
    execution_tracker.assertion_started("user response schema")
    errors = sorted(USER_VALIDATOR.iter_errors(context.response.json()), key=lambda error: list(error.path))
    try:
        assert not errors, "Schema validation failed: " + "; ".join(error.message for error in errors)
    except AssertionError:
        execution_tracker.assertion_failed("user response schema")
        raise
    execution_tracker.assertion_passed("user response schema")


@step('the response time should be less than {expected_timeout:f} seconds')
def verify_response_time(context, expected_timeout):
    execution_tracker.assertion_started(f"response time is below {expected_timeout:.1f} seconds")
    elapsed = context.response.elapsed.total_seconds()
    try:
        assert elapsed < expected_timeout, f"Response time {elapsed:.3f}s exceeded {expected_timeout:.3f}s SLA"
    except AssertionError:
        execution_tracker.assertion_failed(f"response time is below {expected_timeout:.1f} seconds")
        raise
    execution_tracker.assertion_passed(f"response time is below {expected_timeout:.1f} seconds")
