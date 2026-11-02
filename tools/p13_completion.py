"""Opt-in final P13 local measurements and deterministic archived scoring."""

import argparse
import asyncio
import base64
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import httpx
from p11_local_smoke import main as lifecycle
from pydantic import SecretStr, ValidationError

from vmarket_ai.contracts import ChatRequest, Message
from vmarket_ai.database import create_db_engine
from vmarket_ai.datasets.release import InputRecord, load_mapping_input
from vmarket_ai.evaluation.new_score import aggregate, score_qa
from vmarket_ai.mapping.evaluate import MeasuredModel
from vmarket_ai.mapping.policy import StandalonePolicy
from vmarket_ai.mapping.service import MappingService
from vmarket_ai.mapping.spec import MappingError, MappingRequest
from vmarket_ai.mapping.store import SQLDraftStore
from vmarket_ai.providers.ollama import OllamaChatModel
from vmarket_ai.providers.openrouter import ProviderError
from vmarket_ai.qa.backend import DEMO_ACTOR, DEMO_COLLECTIONS, DEMO_SUPPLIERS, PostgresEvidence
from vmarket_ai.qa.service import SYSTEM, supported_quote
from vmarket_ai.qa.spec import Proposal
from vmarket_ai.retrieval.metrics import latency
from vmarket_ai.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def sha(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def score_all(raw):
    qa_gold = {r["id"]: r for r in rows(ROOT / "evals/p13/new-questions-v1/labels.jsonl")}
    mapping_gold = {r["case_id"]: r for r in rows(ROOT / "data/v1/labels/mapping.jsonl")}
    qa_ids = {r["id"] for r in rows(ROOT / "evals/p13/new-questions-v1/inputs.jsonl")}
    mapping_ids = {
        r["id"]
        for r in rows(ROOT / "data/v1/inputs.jsonl")
        if r["partition"] == "test" and r["contract"] == "supplier_three"
    }
    expected = {(i, m) for i in qa_ids for m in ("with_sources", "without_sources")} | {
        (i, m) for i in mapping_ids for m in ("rule", "ai")
    }
    identities = [(r["case_id"], r["method"]) for r in raw]
    if len(identities) != len(expected) or set(identities) != expected:
        raise ValueError("Missing, repeated, or unexpected final evaluation cases")
    scored = []
    for row in raw:
        if row["domain"] == "qa":
            score = score_qa(row, qa_gold[row["case_id"]])
        else:
            label = mapping_gold[row["case_id"]]
            response = row.get("response")
            predicted = (
                {a["target_field"]: a["source_header"] for a in response["assignments"]}
                if response
                else {}
            )
            target = label["target_to_source"]
            score = {
                "exact_mapping": predicted == target if target is not None else None,
                "status_correct": row["status"] == label["expected_suggestion"],
                "model_output_rejected": bool(
                    response and "MODEL_OUTPUT_INVALID" in response["warnings"]
                ),
                "model_unavailable": bool(response and "MODEL_UNAVAILABLE" in response["warnings"]),
            }
        scored.append({**row, "score": score})
    summary = aggregate([r for r in scored if r["domain"] == "qa"], [])
    for method in ("rule", "ai"):
        group = [r for r in scored if r["domain"] == "mapping" and r["method"] == method]
        for metric in (
            "exact_mapping",
            "status_correct",
            "model_output_rejected",
            "model_unavailable",
        ):
            measured = [r["score"][metric] for r in group if r["score"][metric] is not None]
            summary.append(
                {
                    "domain": "mapping",
                    "method": method,
                    "metric": metric,
                    "value": sum(measured) / len(measured) if measured else None,
                    "n": len(measured),
                }
            )
        for name, value in latency([r["latency_ms"] for r in group]).items():
            summary.append(
                {
                    "domain": "mapping",
                    "method": method,
                    "metric": name,
                    "value": value,
                    "n": len(group),
                }
            )
    return scored, summary


def exercise(*, sql_connect, snapshot, report, migration_env, **unused):
    def business():
        with sql_connect() as connection:
            return snapshot(connection)

    before = business()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    settings = Settings(
        _env_file=None,
        mode="standalone",
        provider_mode="local",
        live_enabled=False,
        database_url=SecretStr(migration_env["AI_DATABASE_URL"]),
        qa_embedding_mode="local",
        qa_model_bundle=Path(migration_env["AI_QA_MODEL_BUNDLE"]),
    )
    engine = create_db_engine(settings)
    model = MeasuredModel(OllamaChatModel(settings))
    journal = ROOT / ".local" / ("p13-final-" + uuid4().hex + ".jsonl")
    paths = [
        ROOT / p
        for p in (
            "data/v1/inputs.jsonl",
            "data/v1/labels/mapping.jsonl",
            "data/releases/v1.lock.json",
            "evals/p13/new-questions-v1/inputs.jsonl",
            "evals/p13/new-questions-v1/labels.jsonl",
            "evals/p13/runs/new-questions-v1/raw.jsonl",
            "tools/p13_completion.py",
            "evals/p13/completion-protocol.md",
        )
    ]
    paths += [
        ROOT / f"evals/retrieval/runs/{p}-v1/predictions.jsonl" for p in ("train", "dev", "test")
    ]
    config = {
        "source_commit": commit,
        "input_sha256_lf": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
        "qa_system_sha256": hashlib.sha256(SYSTEM.encode()).hexdigest(),
        "qa_parser_schema": Proposal.model_json_schema(),
        "qa_max_tokens": 512,
        "context": 4096,
        "seed": 42,
        "temperature": 0.2,
        "thinking": False,
        "mapping_policy": "standalone synthetic profiles; Java business acceptance not measured",
        "human_review": "pending",
        "external_provider_calls": 0,
        "provider_charge_usd": 0,
        "energy_hardware_cost": "not measured",
    }
    config["implementation_sha256_lf"] = {
        p.relative_to(ROOT).as_posix(): sha(p)
        for p in sorted((ROOT / "src/vmarket_ai").rglob("*.py"))
    }
    with httpx.Client(base_url="http://127.0.0.1:11434", trust_env=False, timeout=180) as client:
        config["model"] = next(
            t
            for t in client.get("/api/tags").json()["models"]
            if t["name"] == settings.ollama_model
        )
        config["runtime"] = client.get("/api/version").json()
        warm = client.post(
            "/api/generate", json={"model": settings.ollama_model, "options": {"num_ctx": 4096}}
        )
        warm.raise_for_status()
    from vmarket_ai.evaluation.tool_questions import DATASET

    if (
        config["model"]["digest"]
        != json.loads((DATASET / "protocol.json").read_text())["model_digest"]
    ):
        raise ValueError("Pinned model digest changed")
    observed = []
    try:
        with journal.open("x", encoding="utf-8", newline="\n") as sink:

            def record(row):
                observed.append(row)
                sink.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                sink.flush()
                os.fsync(sink.fileno())

            async def run():
                evidence = PostgresEvidence(engine, settings)
                mapping = MappingService(
                    StandalonePolicy(),
                    SQLDraftStore(engine),
                    model,
                    evidence,
                    mode="local",
                    deadline_seconds=30,
                )
                inputs = [
                    InputRecord.model_validate_json(line)
                    for line in (ROOT / "data/v1/inputs.jsonl").read_text().splitlines()
                ]
                selected = [
                    r for r in inputs if r.partition == "test" and r.contract == "supplier_three"
                ]
                for item in selected:
                    data = load_mapping_input(
                        ROOT / "data/v1", ROOT / "data/releases/v1.lock.json", item.id
                    )
                    for method in ("rule", "ai"):
                        request = MappingRequest(
                            raw_base64=base64.b64encode(data.raw_bytes).decode(),
                            declared_encoding=data.declared_encoding,
                            selected_vendor_code=data.selected_vendor_code,
                            method=method,
                            synthetic=True,
                        )
                        started, attempts, count = (
                            time.perf_counter(),
                            model.attempts,
                            len(model.results),
                        )
                        row = {"domain": "mapping", "case_id": item.id, "method": method}
                        try:
                            response = await mapping.suggest(DEMO_ACTOR, request, uuid4())
                            row.update(
                                status=response.status, response=response.model_dump(mode="json")
                            )
                        except MappingError as error:
                            row.update(
                                status="input_error" if error.status in (400, 413) else "error",
                                response=None,
                                error=error.code,
                            )
                        row.update(
                            latency_ms=(time.perf_counter() - started) * 1000,
                            model_attempts=model.attempts - attempts,
                            model_outputs=[
                                r.model_dump(mode="json") for r in model.results[count:]
                            ],
                        )
                        record(row)
                # Reuse exact retained source text, not approximated document sections.
                lookup = {}
                for part in ("train", "dev", "test"):
                    for row in rows(ROOT / f"evals/retrieval/runs/{part}-v1/predictions.jsonl"):
                        for hit in row["result"]["hits"]:
                            c = hit["citation"]
                            if c["chunk_id"] in lookup and lookup[c["chunk_id"]] != c:
                                raise ValueError("Inconsistent retained chunk")
                            lookup[c["chunk_id"]] = c
                retained = {
                    r["case_id"]: r
                    for r in rows(ROOT / "evals/p13/runs/new-questions-v1/raw.jsonl")
                    if r["domain"] == "retrieval" and r["method"] == "dense"
                }
                for case in rows(ROOT / "evals/p13/new-questions-v1/inputs.jsonl"):
                    citations = [lookup[h["chunk_id"]] for h in retained[case["id"]]["hits"]]
                    scope = DEMO_COLLECTIONS[0 if case["collection"] == "a" else 1]
                    for method in ("with_sources", "without_sources"):
                        sources = citations if method == "with_sources" else []
                        payload = {
                            "question": case["question"],
                            "language": case["language"],
                            "selected_supplier": DEMO_SUPPLIERS[scope],
                            "sources": [
                                {"chunk_id": c["chunk_id"], "text": c["text"]} for c in sources
                            ],
                        }
                        started, count = time.perf_counter(), len(model.results)
                        row = {"domain": "qa", "case_id": case["id"], "method": method}
                        try:
                            completion = await model.complete(
                                ChatRequest(
                                    messages=(
                                        Message(role="system", content=SYSTEM),
                                        Message(
                                            role="user",
                                            content=json.dumps(payload, ensure_ascii=False),
                                        ),
                                    ),
                                    max_output_tokens=512,
                                    structured_output=Proposal.model_json_schema(),
                                )
                            )
                            proposal = Proposal.model_validate_json(completion.text)
                            by_id = {c["chunk_id"]: c for c in sources}
                            if any(
                                str(c.chunk_id) not in by_id
                                or not supported_quote(by_id[str(c.chunk_id)]["text"], c.quote)
                                for c in proposal.claims
                            ):
                                raise ValueError("Unsupported quote or source")
                            row.update(
                                http_status=200,
                                response={
                                    "status": "answered"
                                    if proposal.decision == "answer"
                                    else "abstained",
                                    "answer": " ".join(c.quote for c in proposal.claims) or None,
                                    "reason": "CONFLICTING_EVIDENCE"
                                    if proposal.decision == "conflict"
                                    else "NO_SUPPORTED_EVIDENCE"
                                    if proposal.decision != "answer"
                                    else None,
                                    "citations": [
                                        {
                                            "document_id": by_id[str(c.chunk_id)]["document_id"],
                                            "locator": {
                                                "kind": "section",
                                                "value": by_id[str(c.chunk_id)][
                                                    "locator"
                                                ].removeprefix("section:"),
                                            },
                                        }
                                        for c in proposal.claims
                                    ],
                                },
                            )
                        except (ProviderError, ValidationError, ValueError) as error:
                            row.update(http_status=502, response=None, error=type(error).__name__)
                        row.update(
                            latency_ms=(time.perf_counter() - started) * 1000,
                            model_outputs=[
                                r.model_dump(mode="json") for r in model.results[count:]
                            ],
                        )
                        record(row)

            asyncio.run(run())
        scored, summary = score_all(observed)  # Labels parsed only after all calls are journaled.
        after = business()
        if before != after:
            raise ValueError("Business snapshot changed")
        report.update(
            status="PASS",
            config=config,
            final_predictions=scored,
            final_summary=summary,
            journal_file=journal.name,
            business_before=before,
            business_after=after,
            business_unchanged_11_tables=True,
            actual_model_attempts=model.attempts,
        )
    finally:
        engine.dispose()


def package(report_path, output):
    report = json.loads(report_path.read_text(encoding="utf-8"))
    raw_path = ROOT / ".local" / report["journal_file"]
    raw = rows(raw_path)
    scored, summary = score_all(raw)
    if scored != report["final_predictions"] or summary != report["final_summary"]:
        raise ValueError("Recorded scores differ")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(raw_path, output / "raw.jsonl")
    for name, content in (
        ("config.json", report["config"]),
        (
            "report.json",
            {
                "predictions": scored,
                "summary": summary,
                "business_unchanged_11_tables": report["business_unchanged_11_tables"],
                "business_before": report["business_before"],
                "business_after": report["business_after"],
            },
        ),
    ):
        (output / name).write_text(
            json.dumps(content, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    sink = io.StringIO(newline="")
    writer = csv.DictWriter(sink, fieldnames=list(summary[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(summary)
    (output / "summary.csv").write_text(sink.getvalue(), encoding="utf-8", newline="\n")
    manifest = {p.name: sha(p) for p in output.iterdir()}
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def verify(output):
    manifest = json.loads((output / "manifest.json").read_text())
    if set(manifest) != {"raw.jsonl", "config.json", "report.json", "summary.csv"}:
        raise ValueError("Artifact inventory differs")
    for name, digest in manifest.items():
        if sha(output / name) != digest:
            raise ValueError("Artifact hash differs")
    config = json.loads((output / "config.json").read_text())
    for name, digest in config["implementation_sha256_lf"].items():
        historical = subprocess.check_output(
            ["git", "show", config["source_commit"] + ":" + name], cwd=ROOT
        )
        if hashlib.sha256(historical.replace(b"\r\n", b"\n")).hexdigest() != digest:
            raise ValueError("Historical implementation differs")
    for name, digest in config["input_sha256_lf"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Frozen input differs")
        historical = subprocess.check_output(
            ["git", "show", config["source_commit"] + ":" + name], cwd=ROOT
        )
        if hashlib.sha256(historical.replace(b"\r\n", b"\n")).hexdigest() != digest:
            raise ValueError("Historical provenance differs")
    scored, summary = score_all(rows(output / "raw.jsonl"))
    report = json.loads((output / "report.json").read_text())
    if (
        report["predictions"] != scored
        or report["summary"] != summary
        or report["business_before"] != report["business_after"]
    ):
        raise ValueError("Recomputed report differs")
    with (output / "summary.csv").open(newline="", encoding="utf-8") as handle:
        if list(csv.DictReader(handle)) != [
            {k: "" if v is None else str(v) for k, v in r.items()} for r in summary
        ]:
            raise ValueError("CSV differs")
    print(json.dumps({"status": "PASS", "observations": len(scored), "human_review": "pending"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project2", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pack", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify(args.output)
    elif args.pack:
        package(args.pack, args.output)
    else:
        if (
            args.project2 is None
            or subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT).strip()
        ):
            raise ValueError("Clean committed protocol and Project2 path required")
        lifecycle(args.project2, args.output, qa=True, checks=exercise)
