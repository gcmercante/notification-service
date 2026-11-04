# Implementation Roadmap

Ten features, built in this order. Each has its own spec, design, tasks and Verifier run. Architecture stays canonical in `docs/architecture/notification-service/`; these specs link to it and do not replace it.

| # | Feature | Delivers | Needs | Fitness checks built here |
|---|---|---|---|---|
| 1 | [platform-foundation](features/platform-foundation/spec.md) | Monorepo with six applications, dependency rule, safe logging, broker port, outbox, local infrastructure | none | FC-01, FC-08, FC-21 |
| 2 | [integration-access](features/integration-access/spec.md) | Administrator and integration API keys, tenant resolution, separated admin surface, rate limits | 1 | FC-03, FC-10, FC-14, FC-22, FC-23, FC-27 |
| 3 | [provider-routing](features/provider-routing/spec.md) | Provider catalog, tenant and default configuration, resolution rule, Redis cache | 2 | FC-20, FC-26 |
| 4 | [notification-submission](features/notification-submission/spec.md) | Durable, idempotent, encrypted acceptance and publication | 2, 3 | FC-04, FC-13, FC-15 (submission part), FC-19 (submission part) |
| 5 | [delivery-status](features/delivery-status/spec.md) | Status state machine, history, status reads, stuck-work alert | 4 | FC-02, FC-09, FC-11, FC-12 (measures) |
| 6 | [email-dispatch](features/email-dispatch/spec.md) | Shared dispatch workflow, retries, ledger, DLQ hand-off, SES send | 3, 4, 5 | FC-16, FC-19 (dispatch part), FC-24, FC-25, FC-29, FC-30 |
| 7 | [provider-status-ingress](features/provider-status-ingress/spec.md) | Callbacks application, SES status by SNS, correlation and parking | 5, 6 | FC-05, FC-07, FC-17, FC-32, FC-33 |
| 8 | [sms-textbee](features/sms-textbee/spec.md) | SMS worker, textbee send and signed status webhook | 6, 7 | FC-05, FC-30 (textbee) |
| 9 | [push-onesignal](features/push-onesignal/spec.md) | Push worker, OneSignal send and Event Stream ingestion | 6, 7 | FC-05, FC-30 (OneSignal) |
| 10 | [dlq-and-data-lifecycle](features/dlq-and-data-lifecycle/spec.md) | DLQ replay, retention, tenant-scoped deletion | 5, 6 | FC-15 (deletion part), FC-18, FC-28 |

**First demonstrable end-to-end path:** after feature 6, an integration submits an email, SES sends it, and the status reads `SENT`. Feature 7 takes it to `DELIVERED`.

**Not assigned to a feature:**

- FC-06 (same status by webhook and queue) has no subject: each selected provider uses one mechanism. It applies when a provider uses both.
- FC-31 is a design-review step, applied to every design here.
- Deployment, production infrastructure, and the legal/DPO review (D-62) need their own decisions before production.

## Cross-cutting items for the owner

| Item | Why it matters |
|---|---|
| OQ-16 timeouts and unknown outcomes | Specs use an unconfirmed default: never resend, stay `PROCESSING`, let the D-40 alert fire. A refining ADR is needed if you confirm it. |
| Enable Docker in WSL | Integration gates and FC-04, FC-16, FC-17, FC-20, FC-21 and FC-32 need PostgreSQL, Kafka and Redis. `docker` is not available in this distro today. |
| International transfer (D-62) | SES region, textbee storage region (not stated by the vendor) and OneSignal all need an assessment before production. |
