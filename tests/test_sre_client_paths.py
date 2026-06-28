from backend.core.srebot_client import SREBOTClient


def test_paths_are_sre_namespaced():
    c = SREBOTClient(base_url="http://gw")
    assert c._api_prefix == "/api/sre"
