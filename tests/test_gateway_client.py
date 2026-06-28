from backend.core.gateway_client import ws_url_for


def test_ws_url_derivation(monkeypatch):
    monkeypatch.setenv("RELAY_GATEWAY_URL", "http://host:18081")
    assert ws_url_for("sre") == "ws://host:18081/ws/sre"
    assert ws_url_for("tss") == "ws://host:18081/ws/tss"


def test_ws_url_https(monkeypatch):
    monkeypatch.setenv("RELAY_GATEWAY_URL", "https://host")
    assert ws_url_for("tss") == "wss://host/ws/tss"
