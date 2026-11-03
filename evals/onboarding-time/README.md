# Agent-operated live UI task timings

See the [measurement report and limitations](../../docs/evidence/CLOUD-browser-mapping-time.md).
These are observed agent browser tasks, not a human time-and-motion study.

- V1: invalid two-row fixture and harness failure retained.
- V2: corrected one-row fixtures; all six tasks complete, two instrument failures retained.
- V3: final complete repeat on the same files; all six tasks complete, two failures/recovery retained.

Each protocol and fixture was committed before its collection. The V3 workflow
was also committed before collection. Read reports alongside event errors and
recovery, not just medians. Do not use any of these medians to claim a percentage
reduction in human supplier onboarding time.

```powershell
python tools/browser_mapping_timing.py --check
```

The verifier checks frozen input hashes, trial order, duration arithmetic,
expected mappings, successful real rendered Java preview counts and raw artifact
hashes. It makes no network or model calls. The live CUA workflows require the
documented runtime bindings, a valid operator session, unique unused profile IDs
and quota; their output is deliberately not fabricated in CI.
