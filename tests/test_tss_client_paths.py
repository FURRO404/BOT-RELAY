from backend.core.tss_client import TSSClient
from backend.core.srebot_client import SREBOTClient


def test_tss_prefix():
    assert TSSClient(base_url="http://gw")._api_prefix == "/api/tss"


def test_sqb_prefix_unchanged():
    assert SREBOTClient(base_url="http://gw")._api_prefix == "/api/sqb"
