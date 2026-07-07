import pytest
import responses as responses_lib

from dtrpg_mcp.client import BASE_URL, DriveThruRPGClient

AUTH_RESPONSE = {
    "token": "test-token",
    "refreshToken": "test-refresh",
    "refreshTokenTTL": 171235,
}


@pytest.fixture
def mocked_responses():
    with responses_lib.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            responses_lib.POST,
            BASE_URL + "auth_key",
            json=AUTH_RESPONSE,
            status=200,
        )
        yield rsps


@pytest.fixture
def client(mocked_responses):
    return DriveThruRPGClient(api_key="fake-key")
