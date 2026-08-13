import httpx
import pytest

from resume_agent.ui.client import (
    AgentUnavailable,
    ApiConflict,
    ApiNotFound,
    ApiTransportError,
    ApiValidationError,
    HttpResumeAgentClient,
    InvalidAgentOutput,
)


def client_for(handler):
    http_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://resume.test",
    )
    return HttpResumeAgentClient("http://resume.test", client=http_client)


def test_client_parses_fact_base_model():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "id": "00000000-0000-0000-0000-000000000001",
                "revision": 0,
                "target": {"role": "Data Analyst"},
                "experiences": [],
                "confirmed_proposal_ids": [],
                "created_at": "2026-08-13T00:00:00Z",
                "updated_at": "2026-08-13T00:00:00Z",
            },
        )

    base = client_for(handler).get_fact_base(
        "00000000-0000-0000-0000-000000000001"
    )

    assert base.target.role == "Data Analyst"


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (404, ApiNotFound),
        (409, ApiConflict),
        (422, ApiValidationError),
        (502, InvalidAgentOutput),
        (503, AgentUnavailable),
    ],
)
def test_client_maps_api_errors(status, error_type):
    client = client_for(
        lambda request: httpx.Response(status, json={"detail": "failure"})
    )

    with pytest.raises(error_type, match="failure"):
        client.health()


def test_transport_error_is_typed():
    def handler(request):
        raise httpx.ConnectError("offline", request=request)

    with pytest.raises(ApiTransportError) as error:
        client_for(handler).health()

    assert error.value.retryable is True


def test_mutation_is_not_automatically_retried():
    attempts = 0

    def handler(request):
        nonlocal attempts
        attempts += 1
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(ApiTransportError):
        client_for(handler).create_fact_base()

    assert attempts == 1
