# ADR 0007: a bounded SQL controller for durable read investigations

Status: implemented for opt-in P11 local integration, 2026-11-02.

The workflow has at most three sequential read tool attempts and a final/handoff
step. Java business actions stay in the existing P10 UI. We need owner checks,
current authorization, compare-and-swap transitions, uncertain-read handling and
retention; no parallel graph, subagents or business approval continuation is
required by this workflow.

| Concern | Explicit controller chosen here | LangGraph alternative |
| --- | --- | --- |
| Persistence | Existing dedicated AI PostgreSQL, two versioned tables | Durable checkpointer and stable thread ID |
| Resume | Current OPERATOR/CSRF, expected revision, leased phase | Command/resume plus the same application authorization checks |
| Replay | Persist a claim before dispatch; uncertain read becomes an observation, no redispatch | Interrupted nodes restart; I/O still needs explicit replay/idempotency handling |
| Scope | Three sequential reads, one business handoff | Useful graph composition/interrupt machinery if later workflow complexity warrants it |
| Maintenance | Existing SQLAlchemy/Alembic and lockfile | Additional orchestration/checkpointer integration to maintain |

LangGraph's official documentation describes a durable checkpointer, a stable
thread ID, and restarting an interrupted node from its beginning. Any earlier
side effects therefore still need careful placement/idempotency. [Official
interrupt documentation](https://docs.langchain.com/oss/python/langgraph/interrupts).
Our inference is that adding it here would still require the BFF authorization
and claim fencing implemented below. We chose the smaller explicit controller
for this bounded flow. No LangGraph prototype or performance comparison was run;
this is an architectural/maintenance decision, not a speed or reliability ranking.

## Checkpoints and authority

`agent_runs` binds server-owned run/conversation/initial request UUIDs, the P09
username HMAC pseudonym, fixed document scopes and a 600-second expiry. Each
transition updates the expected revision and appends transition metadata in the
same transaction. Active actor slots are bounded to eight by a partial unique
index. The app can update state columns, but cannot change owner/identity/expiry,
delete runs or edit the event journal. Owner maintenance handles retention.

Planning is leased before calling the model. A validated closed intent is saved
before the BFF can claim it. A claim is saved before any Java GET. Every BFF
request, tool dispatch, result checkpoint and public response rechecks current
OPERATOR/CSRF as appropriate; Java independently authorizes its GET. Resume uses
fresh signed contexts and current configured scopes. HMAC key rotation makes old
ownership references unavailable. Verified usernames inherit Java's identity
lifecycle limitations; recycling a username is not a new tenant boundary.

After a process death, an expired planning/read lease becomes
waiting_for_operator/OUTCOME_UNKNOWN. Inspection performs this metadata transition
but never dispatches a tool. Explicit recovery of an uncertain read records an
unavailable observation for the original call and allows only a bounded final
abstention; it does not replay the GET. An interrupted planning phase can be
planned again only after an explicit resume, because no tool was claimed there.
Late results, duplicate resume and cancellation races are rejected by revisions
and lease IDs. A run has at most three read attempts and a 24-revision work budget.

Public snapshots contain statuses/counts/timestamps, not raw questions, cached
Java data, document excerpts, execution leases or transport credentials. Stored
knowledge observations discard excerpts/citations and retain count/status only;
the planner gets no cached document evidence to treat as current authorization.
Other stored tool observations are the P09 bounded, identity-redacted projections.
Their timestamps denote historical observations, not current business truth.

Business handoff is informational: it enters terminal phase with
waiting_for_operator/BUSINESS_HANDOFF and cannot be resumed as consent. Profile,
preview, receipt, confirm and restart semantics stay in Java. Cancelling a run
fences future checkpoints/dispatch but cannot retract a GET already received by
Java. No background resumption or automatic tool/model/provider retry is added.

## Expiry and retention

All API access applies the fixed 600-second TTL; expiry erases question/history/
summaries/pending outcome and disables continuation. Unread rows are scrubbed by
owner `runs-maintain`, at most500 per invocation. The owner then purges runs and
cascading metadata after24hours beyond expiry. This is lazy access enforcement
plus explicit bounded maintenance, not a claim that a background retention daemon
is installed or backups are erased at the wall-clock expiry.
