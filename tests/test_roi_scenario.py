import importlib.util
from pathlib import Path


def test_hypothetical_losses_are_preserved_and_free_scenario_has_no_infinite_roi():
    spec = importlib.util.spec_from_file_location(
        "roi", Path(__file__).resolve().parents[1] / "tools/roi_scenario.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.scenario(10, -1, 60, 5, 0, 1)
    assert result["net_value_assumed"] == -15 and result["roi_fraction_assumed"] == -3
    free = module.scenario(0, 0, 0, 0, 0, 1)
    assert free["roi_fraction_assumed"] is None
