"""Opt-in disposable real integration plus explicitly mocked browser fault checks."""

import argparse
import json
import os
import subprocess
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from p11_local_smoke import ROOT, main
from p12_checks import exercise as real_checks


def exercise(*, operator_login, report, project2, base, **options):
    operator, csrf = operator_login()
    samples = []
    with closing(operator):
        for name, body, headers, expected in (
            ("missing_csrf", {"action": "start", "question": "List imports"}, {}, 403),
            (
                "cross_origin",
                {"action": "start", "question": "List imports"},
                {"Origin": "https://evil.invalid", "X-CSRF-TOKEN": csrf},
                403,
            ),
            (
                "injected_url",
                {"action": "start", "question": "List imports", "url": "http://169.254.169.254/"},
                {"X-CSRF-TOKEN": csrf},
                400,
            ),
            (
                "unknown_scope",
                {"action": "start", "question": "List imports", "collection_ids": [str(uuid4())]},
                {"X-CSRF-TOKEN": csrf},
                403,
            ),
        ):
            response = operator.post("/api/ops/ai/runs", json=body, headers=headers)
            assert response.status_code == expected, (name, response.status_code)
            samples.append(
                {"case": name, "http_status": response.status_code, "response": response.json()}
            )
    report["rejection_samples"] = samples
    real_checks(
        operator_login=operator_login, report=report, project2=project2, base=base, **options
    )
    output = ROOT / ".local" / ("p14-browser-faults-" + uuid4().hex)
    env = dict(os.environ, BASE_URL=base, QA_ARTIFACT_DIR=str(output))
    result = subprocess.run(
        ["python", "tools/qa_copilot.py"],
        cwd=project2,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "Mocked browser fault checks failed; inspect private local logs"
    report["mocked_browser_faults"] = json.loads(
        (output / "report.json").read_text(encoding="utf-8")
    )
    report["source_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    report["project2_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=project2, text=True
    ).strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project2", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    main(args.project2, args.output, qa=True, checks=exercise)
    print("LOCAL_P14_ACCEPTANCE_PASS")
