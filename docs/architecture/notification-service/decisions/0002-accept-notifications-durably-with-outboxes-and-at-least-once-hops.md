# ADR-0002: Accept notifications durably with outboxes and at-least-once hops

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-27, D-35, D-37, D-49, D-61 |
| Decision date | 2026-10-22 |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | Decisions confirmed in the owner's HLD reviews (HLD [§2.3](../high-level-design.md#23-decision-log)): D-27 in the revision 9 review; D-35 and D-37 in the revision 13 review; D-49 in the revision 15 review; D-61 in the item-by-item review of revision 18. This record itself has not been reviewed. Record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-08, C-33, C-41, C-43, C-55, C-67 |
| HLD sections | §5.1 (P-03), §7.1, §7.2, §7.3, §7.5 |
| Supersedes | — |

## Context

Submission, dispatch, callbacks, and status updates must be treated as potentially duplicated or out of order (C-08, **Confirmed**). In the original diagram the API published directly to the broker and never informed the status owner, so a notification was invisible until a worker reported an attempt, and a broker outage meant the API could not accept work at all (HLD [§5.1, P-03](../high-level-design.md#p-03-confirmed-by-d-27-durable-acceptance-via-transactional-outbox); I-04). The quality scenarios ask that an accepted request survive the crash of any single platform process (QS-01) and that duplicate sends be contained and documented, not hidden (QS-03).

The platform must also stay portable across brokers (C-02). Kafka, RabbitMQ, and SQS differ in ordering guarantees (HLD [§4.4](../high-level-design.md#44-broker-boundary)), and the provider call is an external side effect that cannot share a transaction with the broker or the database, so end-to-end exactly-once delivery is not achievable in general (HLD [§7.1](../high-level-design.md#71-delivery-semantics-confirmed-d-61)).

Unknown: no provider is selected yet, so which providers support idempotency keys is unknown. How to treat an *unknown* attempt outcome (timeout, or a crash between the provider's response and the commit) is an **Open question** (OQ-16).

## Decision

The owner confirmed (wording from [context §8](../architecture-context.md#8-confirmed-decisions)):

- **D-27:** "Durable acceptance through a transactional outbox (HLD P-03) is approved." (C-33)
- **D-35:** "Every submission must carry an idempotency key, scoped per integration and remembered for 24 hours. A retry with the same key returns the original notification." (C-41)
- **D-37:** "Each of the six applications has its own deployment. The outbox pattern runs in the API / Gateway and in the provider-callbacks application." (C-43)
- **D-49:** "There is no ordering requirement across notifications; delivery order may differ from submission order." (C-55)
- **D-61:** "Every hop between applications is at-least-once. Duplicate sends are minimized, not eliminated; exactly-once delivery to recipients is not promised. Provider idempotency keys are used where supported and are a provider-selection criterion. The channel workers also use an outbox, so every application that stores state and publishes events has one." (C-67)

**D-37 has two clauses.** Its first clause ("each of the six applications has its own deployment") is structural; it is recorded here because the grouping places it here (README §7.1), and [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md) relies on it. Its second clause limited the outbox to the API / Gateway and the provider-callbacks application; D-61 later extended it to the three channel workers.

**Net position:** every application that stores state and publishes events has an outbox: the API / Gateway (D-27, D-37), the provider-callbacks application (D-37), and the SMS, Email, and Push workers (D-61). The Delivery-status application consumes but never publishes, so it has none (HLD §7.1). Each application has its own deployment, and the API / Gateway's relay runs inside that deployment (HLD §5.1). Every hop is at-least-once and consumers deduplicate; correctness never depends on ordering across notifications.

The rule that the same idempotency key with a different body is rejected as a conflict is part of D-58 and is recorded in [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md), not here.

**Deferred:** the handling of unknown outcomes and timeouts remains open (OQ-16; deferred by the owner in D-10).

## Alternatives considered

- **Direct publish from the API to the broker (the v0 diagram)** — Rejected (D-27): broker unavailability stops acceptance, there is no durable record outside the broker, status is unknown between acceptance and the first attempt, and idempotency still needs a store. (Source: HLD §5.1, P-03 options table.)
- **Exactly-once delivery to recipients** — Not adopted (D-61): not achievable in general because the provider call is outside any transaction; recorded as an accepted trade-off. (Source: HLD §7.1, §10 "Duplicate containment, not elimination".)
- **Optional idempotency key, other scope or retention (D-35)** — Not recorded when the decision was made.
- **Ordering per recipient, per integration, or per tenant (D-49)** — These were the scopes the question covered; none was required. No ordered alternative was designed. (Source: HLD §7.2.)
- **Outbox only in the API / Gateway and provider-callbacks app (D-37 as first confirmed)** — Superseded in scope by D-61, which added the workers so that "attempt done" and "outcome published" are one atomic step (HLD §7.1). No other reason is recorded.

## Consequences

- **Positive:**
  - Acceptance is atomic with the stored request; the API keeps accepting while the broker is down, as long as PostgreSQL is available (HLD [§7.5](../high-level-design.md#75-dependency-outages)).
  - The status owner learns of every accepted notification, and every attempt outcome is published even if the broker fails after the provider call.
  - With no ordering dependency, the RabbitMQ and SQS ordering gaps do not affect the platform's semantics (HLD [§7.2](../high-level-design.md#72-ordering)).
  - The guarantee is stated honestly: duplicates are contained and documented, not denied.
- **Negative / accepted risks:**
  - A relay component and outbox table per stateful application, extra latency, and more database load (HLD [§10](../high-level-design.md#10-trade-offs)).
  - The API cannot accept work while PostgreSQL is unavailable.
  - Every consumer must deduplicate by stable message identity, because relays and broker hops redeliver.
  - A residual duplicate window remains between the provider's response and the worker's commit; provider idempotency keys close it only where supported (HLD [§7.3](../high-level-design.md#73-duplicates-and-idempotency)).
  - A submission retried more than 24 hours later creates a new notification.
- **Follow-up:**
  - OQ-16 (timeouts and unknown outcomes) is open; resolving it will refine this ADR and [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md).
  - Provider idempotency-key support must be assessed during provider selection (D-61).
  - The HLD §5.1 open point on whether the "accepted" fact uses its own topic stays open.
  - Event contracts must carry a stable message identity for deduplication once they are produced (HLD §13).

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| An accepted notification is never lost when the API, relay, or broker is killed (D-27) | §14 — FC-04 | Planned |
| Idempotency key mandatory, per integration, 24 hours, original returned (D-35) | §14 — FC-13 | Planned |
| Worker records attempt and outcome atomically and publishes after a broker outage; a "done" dispatch is not resent (D-61) | §14 — FC-16 | Planned |
| Callbacks app acknowledges providers after commit and publishes after a broker outage (D-37) | §14 — FC-17 | Planned |
| No consumer relies on ordering across notifications (D-49) | §14 — FC-31 (approved by D-66) | Planned |
| Each application has its own deployment (D-37, first clause) | Gap — no check exists | Gap — no check exists |
| Provider idempotency keys are used where the provider supports them (D-61) | Gap — no check exists | Gap — no check exists |
| Consumers deduplicate relay and broker redeliveries (D-61) | Partly FC-16 (workers) and FC-02 (status app, recorded in ADR-0005); no check for other consumers | Planned (partial) |

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-27, D-35, D-37, D-49, D-61); [context §8](../architecture-context.md#8-confirmed-decisions).
- Constraints: HLD [§2.1](../high-level-design.md#21-confirmed-constraints); open questions: HLD [§11.2](../high-level-design.md#112-still-open) (OQ-16); fitness checks: HLD [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69).
- Related to [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md) (D-58 idempotency-conflict rule; deployment structure; D-57 choreography).
- Related to [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md) (retries; OQ-16).
- Related to [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md) (order-independent status rules, D-60).
- Related to [ADR-0010](0010-use-a-database-per-application-on-shared-postgresql.md) (databases holding the outboxes, D-45).
- Diagram: [`notification-platform-hld.drawio`](../diagrams/notification-platform-hld.drawio), page "v1 - Current design".

## Amendments

None.
