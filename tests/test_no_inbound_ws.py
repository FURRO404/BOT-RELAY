from backend.receiver import create_app


def test_no_inbound_ws_srebot_route():
    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/ws/srebot" not in paths
