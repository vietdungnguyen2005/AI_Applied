import importlib.util
from pathlib import Path

import httpx
import pytest


def module():
    spec = importlib.util.spec_from_file_location(
        "ops_probe", Path(__file__).resolve().parents[1] / "tools/ops_probe.py"
    )
    assert spec is not None and spec.loader is not None
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize(
    "base",
    [
        "https://example.com",
        "http://127.0.0.1@evil.invalid",
        "http://localhost:1/?secret=x",
        "http://127.0.0.1/path",
    ],
)
async def test_probe_rejects_nonlocal_or_data_bearing_origins(base):
    with pytest.raises(ValueError):
        await module().probe(base, 1, 1)


async def test_probe_counts_failed_readiness_and_checks_trace_echo():
    def handle(request):
        return httpx.Response(
            200 if request.url.path == "/health" else 503,
            headers={"X-Request-ID": request.headers["X-Request-ID"]},
        )

    result = await module().probe("http://127.0.0.1:8090", 4, 2, httpx.MockTransport(handle))
    assert result["error_rate"] == 0.5 and result["correlation_coverage"] == 1
    assert result["model_calls"] == 0 and len(result["observations"]) == 4
