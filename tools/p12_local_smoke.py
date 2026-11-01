"""Opt-in P12 smoke using the disposable P11 service lifecycle."""

import argparse
from pathlib import Path

from p11_local_smoke import main
from p12_checks import exercise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project2", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.project2, args.output, qa=True, checks=exercise)
    print("LOCAL_P12_SMOKE_PASS")
