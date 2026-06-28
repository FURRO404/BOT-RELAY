from backend.core.srebot_store import SREBOTEventStore


async def test_latest_filters_by_source():
    s = SREBOTEventStore()
    await s.add({"type": "sqb.x", "source": "sre", "payload": {}})
    await s.add({"type": "tss.replay_batch", "source": "tss", "payload": {}})
    assert (await s.latest(source="tss")).event_type == "tss.replay_batch"
    assert (await s.latest(source="sre")).source == "sre"


async def test_stats_filters_by_source():
    s = SREBOTEventStore()
    await s.add({"type": "sqb.x", "source": "sre", "payload": {}})
    await s.add({"type": "tss.y", "source": "tss", "payload": {}})
    stats = await s.stats(source="tss")
    assert stats["total_events"] == 1


async def test_list_filters_by_source():
    s = SREBOTEventStore()
    await s.add({"type": "sqb.x", "source": "sre", "payload": {}})
    await s.add({"type": "tss.y", "source": "tss", "payload": {}})
    items = await s.list(source="sre")
    assert len(items) == 1
    assert items[0].source == "sre"


async def test_channel_overrides_envelope_source():
    # A real SREBOT envelope carries source "srebot" but arrives on the "sre"
    # channel; it must be queryable as "sre" (the receiver namespaces by channel).
    s = SREBOTEventStore()
    await s.add({"type": "spectra.replay_batch", "source": "srebot", "payload": {}}, channel="sre")
    assert (await s.latest(source="sre")) is not None
    assert (await s.latest(source="srebot")) is None
    rec = await s.latest(source="sre")
    assert rec.raw["source"] == "srebot"  # original preserved in raw
