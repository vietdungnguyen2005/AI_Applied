import math
import re
import time
from contextlib import suppress
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from vmarket_ai.gateway.agent import AgentService
from vmarket_ai.gateway.wire import GatewayError
from vmarket_ai.runs.spec import RunCommand
from vmarket_ai.runs.store import ACTIVE, RunStore


def public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": str(row["id"]),
        "conversation_id": str(row["conversation_id"]),
        "initial_request_id": str(row["initial_request_id"]),
        **{
            k: row[k]
            for k in (
                "status",
                "phase",
                "revision",
                "step",
                "created_at",
                "updated_at",
                "expires_at",
                "reason",
            )
        },
        "observations": row["summaries"],
        "outcome": row["outcome"],
        "can_resume": (row["status"] == "started" and row["phase"] in {"idle", "ready"})
        or (row["status"] == "waiting_for_operator" and row["reason"] == "OUTCOME_UNKNOWN"),
        "can_cancel": row["status"] in ACTIVE,
    }


def private(row: dict[str, Any]) -> dict[str, Any]:
    known = set(re.findall(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", row["question"]))
    for observation in row["history"]:
        data = observation.get("data")
        if isinstance(data, dict):
            if "imports" in data:
                known.update(j["job_id"] for j in data["imports"])
            if "job" in data:
                known.add(data["job"]["job_id"])
            if "job_id" in data:
                known.add(data["job_id"])
    return {
        "state": public(row),
        "collection_ids": row["collection_ids"],
        "pending_intent": row["pending"],
        "lease_id": str(row["lease_id"]) if row["lease_id"] else None,
        "known_job_ids": sorted(known)[:100],
    }


class RunService:
    def __init__(self, store: RunStore, agent: AgentService):
        self.store, self.agent = store, agent

    async def execute(
        self, command: RunCommand, claims: dict[str, Any], deadline: float
    ) -> dict[str, Any]:
        actor = claims["actor_ref"]
        run = UUID(claims["run_id"])
        request = UUID(claims["request_id"])
        scopes = tuple(claims["collection_ids"])
        try:
            if command.action == "start":
                if (
                    claims["step"] != 0
                    or command.collection_ids is None
                    or command.conversation_id is None
                    or command.question is None
                ):
                    raise GatewayError("INPUT_INVALID", 400)
                if tuple(map(str, command.collection_ids)) != scopes:
                    raise GatewayError("ACCESS_DENIED", 403)
                row = self.store.start(
                    actor, run, command.conversation_id, command.question, scopes, request
                )
            else:
                row = self.store.get(run, actor, scopes, request)
                if command.action == "inspect":
                    return private(row)
                revision = command.expected_revision
                if revision is None:
                    raise GatewayError("INPUT_INVALID", 400)
                if claims["step"] != row["step"]:
                    raise GatewayError("STEP_CONFLICT", 409)
                self.store.expected(row, revision)
                if row["revision"] >= 24 and command.action != "cancel":
                    self.store.fail(row, "BUDGET_EXCEEDED", request)
                    raise GatewayError("BUDGET_EXCEEDED", 429)
                deadline = min(deadline, row["expires_at"])
                if command.action == "cancel":
                    row = self.store.cancel(run, actor, revision, scopes, request)
                elif command.action == "recover":
                    row = self.store.recover(row, revision, request)
                elif command.action == "claim":
                    row = self.store.claim(row, revision, request, math.ceil(deadline))
                elif command.action == "record":
                    if command.lease_id is None or command.observation is None:
                        raise GatewayError("INPUT_INVALID", 400)
                    row = self.store.record(
                        row, revision, command.lease_id, command.observation, request
                    )
                elif command.action == "plan":
                    row = self.store.begin(row, revision, request, math.ceil(deadline))
                    history = row["history"]
                    try:
                        from asyncio import timeout

                        async with timeout(max(0, deadline - time.time())):
                            response = await self.agent.step(
                                {
                                    "protocol_version": 1,
                                    "request_id": str(request),
                                    "run_id": str(run),
                                    "step": row["step"],
                                    "question": row["question"],
                                    "collection_ids": row["collection_ids"],
                                    "previous_results": history[:-1],
                                    "tool_result": history[-1] if history else None,
                                }
                            )
                            row = self.store.planned(row, response, request)
                    except (GatewayError, TimeoutError) as error:
                        code = (
                            error.code if isinstance(error, GatewayError) else "DEADLINE_EXCEEDED"
                        )
                        with suppress(GatewayError):
                            self.store.fail(row, code, request)
                        raise GatewayError(
                            code, error.status if isinstance(error, GatewayError) else 504
                        ) from None
            return private(row)
        except SQLAlchemyError:
            raise GatewayError("DEPENDENCY_UNAVAILABLE", 503) from None
