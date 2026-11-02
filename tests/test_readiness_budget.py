import asyncio
import threading

import httpx

from vmarket_ai.app import create_app


async def test_slow_readiness_is_bounded_and_does_not_multiply_db_probes(migrated, monkeypatch):
    released = threading.Event()
    attempts = []

    def slow_database(engine):
        attempts.append(1)
        released.wait(4)
        return False

    monkeypatch.setattr("vmarket_ai.app.database_ready", slow_database)
    app = create_app(migrated)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            responses = await asyncio.wait_for(
                asyncio.gather(*(client.get("/ready") for _ in range(4))), 2
            )
            assert all(r.status_code == 503 for r in responses)
            assert (await client.get("/health")).status_code == 200
            assert len(attempts) == 1
    finally:
        released.set()
        await asyncio.sleep(0.05)
