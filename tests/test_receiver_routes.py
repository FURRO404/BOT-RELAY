from backend.receiver import create_app
from tests._route_utils import all_paths


def test_namespaced_routes_present():
    paths = all_paths(create_app())
    assert "/api/{channel}/stats" in paths
    assert "/api/{channel}/latest" in paths
    assert "/api/{channel}/events" in paths
    assert "/api/srebot/stats" not in paths
