from backend.receiver import create_app


def test_namespaced_routes_present():
    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/api/{channel}/stats" in paths
    assert "/api/{channel}/latest" in paths
    assert "/api/{channel}/events" in paths
    assert "/api/srebot/stats" not in paths
