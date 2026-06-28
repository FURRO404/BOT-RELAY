from backend.receiver import create_app
from tests._route_utils import all_paths


def test_no_inbound_ws_srebot_route():
    assert "/ws/srebot" not in all_paths(create_app())
