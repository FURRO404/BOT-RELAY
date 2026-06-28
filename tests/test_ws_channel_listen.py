from backend.core import srebot_ws


def test_listen_channel_and_all_exist():
    assert hasattr(srebot_ws, "listen_channel")
    assert hasattr(srebot_ws, "listen_all")
    assert not hasattr(srebot_ws, "listen_forever")
