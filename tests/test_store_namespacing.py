from backend.core.srebot_store import SREBOTEventStore


async def test_latest_filters_by_source():
    s = SREBOTEventStore()
    await s.add({"type": "sqb.x", "source": "sqb", "payload": {}})
    await s.add({"type": "tss.replay_batch", "source": "tss", "payload": {}})
    assert (await s.latest(source="tss")).event_type == "tss.replay_batch"
    assert (await s.latest(source="sqb")).source == "sqb"


async def test_stats_filters_by_source():
    s = SREBOTEventStore()
    await s.add({"type": "sqb.x", "source": "sqb", "payload": {}})
    await s.add({"type": "tss.y", "source": "tss", "payload": {}})
    stats = await s.stats(source="tss")
    assert stats["total_events"] == 1


async def test_list_filters_by_source():
    s = SREBOTEventStore()
    await s.add({"type": "sqb.x", "source": "sqb", "payload": {}})
    await s.add({"type": "tss.y", "source": "tss", "payload": {}})
    items = await s.list(source="sqb")
    assert len(items) == 1
    assert items[0].source == "sqb"
