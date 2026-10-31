# Scope and non-goals

This is a local portfolio implementation plan for a fictional retailer with synthetic suppliers A/B. No real customer acceptance, multi-tenant deployment, production security certification or ROI is implied.

## Included

- Authorized bilingual synthetic SOP retrieval and supported answers/citations with abstention.
- Original-byte CP932/UTF-8 mapping drafts limited to sku/name/on_hand; rule-only baseline and human review.
- Bounded read-only job/profile/stored-report investigation through an authenticated server-side BFF gateway.
- Explicit handoff into current protected V-Market profile, activation, preview/confirm and inspection workflows.
- Fake-default standalone demo and feature-OFF integrated local mode; opt-in real provider only with explicit budget.
- Dataset/version/config evidence, formal evals, negative security tests, failure behavior, English delivery docs and manual fallback.

## Excluded

No autonomous inventory, price, product, checkout, profile, activation, import confirm, restart, refund or reconciliation mutation. No AI connection to Java's DB. No browser-to-model API calls or Python-held session/CSRF/trust secrets. No real suppliers, payment details, private records or external live business integrations. No arbitrary web/URL/SQL/file execution tools. No automatic encoding guess, BOM/newline repair, invented vendor identity or quantity freshness. No fake tenant selector or supplier-level isolation claim over a shared-store OPERATOR role. No public production deployment, billable cloud provisioning, customer SLA or real participant benchmark without further evidence and authorization.

Support for scanned/OCR documents, LangGraph, reranking frameworks, streaming, object storage and additional languages is conditional on demonstrated need and installable, tested implementation. Do not claim these from a diagram alone.

## Change control and rollback

Requirements are proposed engineering scope. A new business write tool, broadened document access, real data use or external spend is a scope change requiring review before implementation. Maintain requirement/acceptance links and version thresholds before held-out evaluation. If AI adds no measurable value over rules, retain rules or reduce model scope.

Before integration: rollback means discard drafts/disable AI; Java is unchanged. After integration: switch AI feature OFF and use existing manual ops. Do not reverse legitimate business mutations, downgrade fenced import binaries or modify immutable profile history as an AI rollback. Inspect unknown import outcomes and use the existing operator recovery procedure.

The P00 dependency audit failure remains open. Documentation work can proceed; later security/release acceptance cannot claim it is resolved without separate remediation and regression proof.
