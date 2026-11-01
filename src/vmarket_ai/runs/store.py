import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from vmarket_ai.gateway.wire import GatewayError, validate
from vmarket_ai.runs.models import RunEvent, RunRecord

ACTIVE = ("started", "waiting_for_operator")
TTL = 600
RETENTION = 86400


class RunStore:
    def __init__(self, engine: Engine):
        self.engine = engine

    @staticmethod
    def clock(now: int | None) -> int:
        return int(time.time()) if now is None else now

    def _save(
        self, old: dict[str, Any], fields: dict[str, Any], kind: str, request: UUID, now: int
    ) -> dict[str, Any]:
        fields = {**fields, "revision": old["revision"] + 1, "updated_at": now}
        with self.engine.begin() as c:
            row = (
                c.execute(
                    update(RunRecord)
                    .where(
                        RunRecord.id == old["id"],
                        RunRecord.actor_ref == old["actor_ref"],
                        RunRecord.revision == old["revision"],
                    )
                    .values(**fields)
                    .returning(*RunRecord.__table__.columns)
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise GatewayError("STEP_CONFLICT", 409)
            value = dict(row)
            c.execute(
                insert(RunEvent).values(
                    id=uuid4(),
                    run_id=value["id"],
                    revision=value["revision"],
                    request_id=request,
                    kind=kind,
                    status=value["status"],
                    phase=value["phase"],
                    step=value["step"],
                    at=now,
                )
            )
        return value

    def start(
        self,
        actor: str,
        run_id: UUID,
        conversation: UUID,
        question: str,
        scopes: tuple[str, ...],
        request: UUID,
        *,
        now: int | None = None,
    ) -> dict[str, Any]:
        now = self.clock(now)
        with self.engine.connect() as c:
            rows = (
                c.execute(
                    select(RunRecord.id).where(
                        RunRecord.actor_ref == actor, RunRecord.status.in_(ACTIVE)
                    )
                )
                .scalars()
                .all()
            )
        for item in rows:
            self.get(item, actor, scopes, request, now=now, check_scope=False)
        with self.engine.connect() as c:
            slots = set(
                c.execute(
                    select(RunRecord.slot).where(
                        RunRecord.actor_ref == actor, RunRecord.status.in_(ACTIVE)
                    )
                ).scalars()
            )
        free = next((s for s in range(8) if s not in slots), None)
        if free is None:
            raise GatewayError("BUDGET_EXCEEDED", 429)
        value = dict(
            id=run_id,
            actor_ref=actor,
            conversation_id=conversation,
            initial_request_id=request,
            slot=free,
            status="started",
            phase="idle",
            revision=0,
            step=0,
            question=question,
            collection_ids=list(scopes),
            history=[],
            summaries=[],
            pending=None,
            outcome=None,
            reason=None,
            lease_id=None,
            lease_until=None,
            created_at=now,
            updated_at=now,
            expires_at=now + TTL,
            purge_after=now + TTL + RETENTION,
        )
        try:
            with self.engine.begin() as c:
                c.execute(insert(RunRecord).values(**value))
                c.execute(
                    insert(RunEvent).values(
                        id=uuid4(),
                        run_id=run_id,
                        revision=0,
                        request_id=request,
                        kind="start",
                        status="started",
                        phase="idle",
                        step=0,
                        at=now,
                    )
                )
        except IntegrityError:
            raise GatewayError("STEP_CONFLICT", 409) from None
        return value

    def get(
        self,
        run_id: UUID,
        actor: str,
        scopes: tuple[str, ...],
        request: UUID,
        *,
        now: int | None = None,
        check_scope: bool = True,
    ) -> dict[str, Any]:
        now = self.clock(now)
        with self.engine.connect() as c:
            row = (
                c.execute(
                    select(RunRecord.__table__).where(
                        RunRecord.id == run_id, RunRecord.actor_ref == actor
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise GatewayError("RUN_NOT_AVAILABLE", 404)
        value = dict(row)
        if check_scope and not set(value["collection_ids"]).issubset(scopes):
            raise GatewayError("ACCESS_DENIED", 403)
        if value["expires_at"] <= now and value["status"] != "expired":
            return self._save(
                value,
                dict(
                    status="expired",
                    phase="terminal",
                    question="",
                    history=[],
                    summaries=[],
                    pending=None,
                    outcome=None,
                    reason="TTL_EXPIRED",
                    lease_id=None,
                    lease_until=None,
                ),
                "expire",
                request,
                now,
            )
        if (
            value["status"] == "started"
            and value["lease_until"] is not None
            and value["lease_until"] <= now
        ):
            return self._save(
                value,
                dict(
                    status="waiting_for_operator",
                    reason="OUTCOME_UNKNOWN",
                    lease_id=None,
                    lease_until=None,
                ),
                "interrupted",
                request,
                now,
            )
        return value

    @staticmethod
    def expected(row: dict[str, Any], revision: int) -> None:
        if row["revision"] != revision or row["status"] not in ACTIVE:
            raise GatewayError("STEP_CONFLICT", 409)

    def cancel(
        self,
        run_id: UUID,
        actor: str,
        revision: int,
        scopes: tuple[str, ...],
        request: UUID,
        *,
        now: int | None = None,
    ) -> dict[str, Any]:
        now = self.clock(now)
        row = self.get(run_id, actor, scopes, request, now=now)
        self.expected(row, revision)
        return self._save(
            row,
            dict(
                status="cancelled",
                phase="terminal",
                pending=None,
                lease_id=None,
                lease_until=None,
                reason="OPERATOR_CANCELLED",
            ),
            "cancel",
            request,
            now,
        )

    def begin(
        self,
        row: dict[str, Any],
        revision: int,
        request: UUID,
        deadline: int,
        *,
        now: int | None = None,
    ) -> dict[str, Any]:
        now = self.clock(now)
        self.expected(row, revision)
        if row["status"] != "started" or row["phase"] != "idle" or deadline <= now:
            raise GatewayError("STEP_CONFLICT", 409)
        return self._save(
            row,
            dict(phase="planning", lease_id=uuid4(), lease_until=min(deadline, now + 30)),
            "planning",
            request,
            now,
        )

    def planned(
        self,
        row: dict[str, Any],
        response: dict[str, Any],
        request: UUID,
        *,
        now: int | None = None,
    ) -> dict[str, Any]:
        now = self.clock(now)
        if row["phase"] != "planning" or row["lease_until"] <= now:
            raise GatewayError("STEP_CONFLICT", 409)
        validate("AgentStepResponse", response)
        if response["run_id"] != str(row["id"]) or response["step"] != row["step"]:
            raise GatewayError("STEP_CONFLICT", 409)
        fields: dict[str, Any] = dict(lease_id=None, lease_until=None)
        if response["kind"] == "tool_intent":
            if row["step"] >= 3:
                raise GatewayError("BUDGET_EXCEEDED", 429)
            if response["intent"]["call_id"] in {h["call_id"] for h in row["history"]}:
                raise GatewayError("STEP_CONFLICT", 409)
            fields.update(phase="ready", pending=response["intent"])
        else:
            handoff = response["kind"] == "handoff"
            fields.update(
                status="waiting_for_operator" if handoff else "completed",
                phase="terminal",
                pending=None,
                reason="BUSINESS_HANDOFF" if handoff else None,
                outcome={
                    "kind": response["kind"],
                    "status": response["status"],
                    "handoff_reason": response["handoff_reason"],
                },
            )
        return self._save(row, fields, "planned", request, now)

    def claim(
        self,
        row: dict[str, Any],
        revision: int,
        request: UUID,
        deadline: int,
        *,
        now: int | None = None,
    ) -> dict[str, Any]:
        now = self.clock(now)
        self.expected(row, revision)
        if (
            row["status"] != "started"
            or row["phase"] != "ready"
            or not row["pending"]
            or deadline <= now
        ):
            raise GatewayError("STEP_CONFLICT", 409)
        return self._save(
            row,
            dict(phase="executing", lease_id=uuid4(), lease_until=min(deadline, now + 30)),
            "read_claimed",
            request,
            now,
        )

    @staticmethod
    def summarized(observation: dict[str, Any]) -> dict[str, Any]:
        data = observation["data"]
        count = 0
        if isinstance(data, dict):
            count = next((len(data[k]) for k in ("profiles", "imports", "hits") if k in data), 1)
        return {
            k: observation[k]
            for k in ("call_id", "tool_name", "status", "observed_at", "truncated", "error_code")
        } | {"item_count": count}

    def record(
        self,
        row: dict[str, Any],
        revision: int,
        lease: UUID,
        observation: dict[str, Any],
        request: UUID,
        *,
        now: int | None = None,
    ) -> dict[str, Any]:
        now = self.clock(now)
        self.expected(row, revision)
        if (
            row["status"] != "started"
            or row["phase"] != "executing"
            or row["lease_id"] != lease
            or row["lease_until"] <= now
        ):
            raise GatewayError("STEP_CONFLICT", 409)
        validate("ToolResult", observation)
        if len(json.dumps(observation, ensure_ascii=False, separators=(",", ":")).encode()) > 16384:
            raise GatewayError("INPUT_TOO_LARGE", 413)
        if any(observation[k] != row["pending"][k] for k in ("call_id", "tool_name")):
            raise GatewayError("STEP_CONFLICT", 409)
        safe = dict(observation)
        if safe["tool_name"] == "search_supplier_knowledge" and safe["status"] == "ok":
            safe["data"] = {
                "hits": []
            }  # Never checkpoint doc text/citations as reusable authorization.
        return self._save(
            row,
            dict(
                phase="idle",
                step=row["step"] + 1,
                history=[*row["history"], safe],
                summaries=[*row["summaries"], self.summarized(observation)],
                pending=None,
                lease_id=None,
                lease_until=None,
            ),
            "read_recorded",
            request,
            now,
        )

    def recover(
        self, row: dict[str, Any], revision: int, request: UUID, *, now: int | None = None
    ) -> dict[str, Any]:
        now = self.clock(now)
        self.expected(row, revision)
        if row["status"] != "waiting_for_operator" or row["reason"] != "OUTCOME_UNKNOWN":
            raise GatewayError("STEP_CONFLICT", 409)
        fields: dict[str, Any] = dict(
            status="started",
            phase="idle",
            reason=None,
            pending=None,
            lease_id=None,
            lease_until=None,
        )
        if row["phase"] == "executing":
            result = {
                "call_id": row["pending"]["call_id"],
                "tool_name": row["pending"]["tool_name"],
                "status": "unavailable",
                "observed_at": datetime.fromtimestamp(now, UTC).isoformat(),
                "truncated": False,
                "data": None,
                "error_code": "UPSTREAM_UNAVAILABLE",
            }
            fields.update(
                step=row["step"] + 1,
                history=[*row["history"], result],
                summaries=[*row["summaries"], self.summarized(result)],
            )
        return self._save(row, fields, "operator_resumed", request, now)

    def fail(
        self, row: dict[str, Any], code: str, request: UUID, *, now: int | None = None
    ) -> dict[str, Any]:
        return self._save(
            row,
            dict(
                status="failed",
                phase="terminal",
                pending=None,
                lease_id=None,
                lease_until=None,
                reason=code,
            ),
            "failed",
            request,
            self.clock(now),
        )

    def purge(self, *, now: int | None = None) -> int:
        # Owner maintenance only: ai_app deliberately has no DELETE permission.
        now = self.clock(now)
        with self.engine.begin() as c:
            eligible = select(RunRecord.id).where(RunRecord.purge_after <= now).limit(500)
            result = c.execute(delete(RunRecord).where(RunRecord.id.in_(eligible)))
            return int(result.rowcount)

    def maintain(self, *, now: int | None = None) -> dict[str, int]:
        now = self.clock(now)
        with self.engine.connect() as c:
            rows = c.execute(
                select(RunRecord.id, RunRecord.actor_ref)
                .where(RunRecord.expires_at <= now, RunRecord.status != "expired")
                .limit(500)
            ).all()
        for run, actor in rows:
            self.get(run, actor, (), uuid4(), now=now, check_scope=False)
        return {"expired": len(rows), "purged": self.purge(now=now)}
