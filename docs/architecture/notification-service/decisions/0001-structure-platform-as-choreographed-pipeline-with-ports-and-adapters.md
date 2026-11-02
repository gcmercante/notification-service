# ADR-0001: Structure the platform as a choreographed pipeline of six applications behind ports and adapters

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-48, D-54, D-57, D-58 |
| Decision date | 2026-10-22 |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | Decisions: HLD review of revision 14 (D-48), revision 17 (D-54), and the item-by-item review of revision 18 (D-57, D-58), as recorded in the HLD [§2.3](../high-level-design.md#23-decision-log) intro. This record: pending owner review (README Q-1). Record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-54, C-60, C-63, C-64; drivers C-01, C-02, C-03, C-04, C-06 |
| HLD sections | [§1.4](../high-level-design.md#14-out-of-scope-until-requirements-say-otherwise), [§4.1](../high-level-design.md#41-shape), [§4.2](../high-level-design.md#42-logical-layering-inside-each-application-confirmed--p-01-d-54) (P-01), [§5.1](../high-level-design.md#51-submission-flow), [§5.2](../high-level-design.md#52-dispatch-flow-per-channel-worker), [§5.4](../high-level-design.md#54-status-maintenance-flow) |
| Supersedes | — |

## Context

**Confirmed:** the platform is a NestJS monorepo with six planned applications (C-01): API / Gateway, three channel workers (SMS, email, push), the provider-callbacks application, and the delivery-status application. Kafka and PostgreSQL are the initial broker and database, but RabbitMQ/SQS adapters and alternative stores must stay feasible without rewriting business rules, and zero-cost substitution is not promised (C-02, C-03). No provider is selected, and providers must be addable and replaceable without scattering vendor logic (C-04). Abstractions must be built around needed capabilities, not hypothetical ones (C-06).

Before revision 18, the six responsibilities were a topology, not a component design. Three questions were still open: how stages coordinate (orchestration or choreography), how technology is kept out of business rules, and what each application owns and does not own. Product scope also had to be bounded (OQ-19). Otherwise templates, scheduling, preferences, or bulk sends would be designed in by default.

## Decision

The owner confirmed (context [§8](../architecture-context.md#8-confirmed-decisions), canonical wording):

- **D-48:** "Only single notifications for now. Templates, scheduled sends, recipient preferences, and bulk sends are future scope." This is a scope boundary. The design should not rule these features out, but nothing is built for them now (HLD §1.4, C-54).
- **D-54:** "Business rules and use cases depend only on narrow interfaces (ports) built around the capabilities they need. Kafka, PostgreSQL, Redis, and provider client libraries live only in replaceable adapters. No generic framework." This approves P-01 (HLD §4.2, C-60).
- **D-57:** "The platform is a choreographed, event-driven pipeline: each application reacts to facts published by the previous one, with no central orchestrator." (HLD §4.1, C-63.)
- **D-58:** "Application responsibilities as described in the HLD (§5.1, §5.2, §5.4) are approved. This includes: the same idempotency key with a different body is rejected; worker outcomes are classified as accepted, permanent, retryable, or unknown; the three workers share one send workflow but deploy separately; workers throttle to each provider account's rate limit." (C-64.)

D-58 approves the HLD §5.1, §5.2, and §5.4 responsibility lists wholesale. This ADR records it. Several of its rules belong by theme to other ADRs, which link back here and do not record D-58 again:

- the idempotency-conflict rule: [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md) (with D-35);
- the four outcome classes: [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md), with "unknown" still open under OQ-16;
- per-provider-account throttling: [ADR-0003](0003-route-tenant-notifications-to-configured-or-default-provider.md), with the values still open under OQ-11.

D-58 does **not** cover the provider-callbacks responsibilities in HLD §5.3. Those remain **Proposed**, except where D-20, D-22 to D-24, and D-37 confirm them. The "each application has its own deployment" clause of D-37 is recorded in [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md).

## Alternatives considered

- **Central orchestrator** (D-57): not selected. It would add a stateful coordinator without making compensation clearer, because the platform cannot compensate a sent notification and can only record what happened. The pipeline is also linear, with one owner per stage and stages that scale differently. (Source: HLD §4.1, §10.)
- **Generic "message bus" or "generic repository" abstraction** (D-54): Rejected. It hides semantics the domain depends on (C-06). (Source: HLD §4.2, P-01.)
- **One generic worker instead of three channel workers** (D-58): not adopted as a deployment. The three workers keep separate deployments for per-channel scaling and isolation (QS-06), and they share one dispatch use case so the workflow is not written three times. (Source: HLD §5.2.)
- **D-48 (scope):** Not recorded when the decision was made.

## Consequences

- **Positive:**
  - Stages scale and fail independently (QS-06).
  - The domain can be tested without infrastructure.
  - Broker, store, cache, and provider replaceability (QS-04, QS-05) becomes checkable through a dependency rule.
  - Each application has a bounded responsibility. Only the delivery-status application writes status (§5.4), and the API never calls providers (§5.1).
- **Negative / accepted risks:**
  - With no coordinator, completion and stuck-work detection must be built explicitly (HLD §4.1, §7.6; the D-40 alert is in [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md)).
  - Every boundary adds one indirection.
  - Ports can drift toward lowest-common-denominator semantics. Mitigation: each port states its guarantees and each adapter documents its gaps (HLD §4.2, §10).
  - Single notifications only: bulk sends and templates will need their own design when planned.
- **Follow-up:**
  - OQ-11: per-provider-account rate values, which depend on provider selection.
  - OQ-16: classifying unknown outcomes.
  - I-08: monorepo layout and tooling, to be decided during implementation planning.
  - HLD §5.3 responsibilities still awaiting approval.
  - Revisit trigger: any D-48 future-scope feature being planned, or any change that adds cross-application coordination.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| Domain and use-case code never imports broker clients, DB drivers, or provider SDKs (D-54) | §14 — FC-01 | Planned. FC-01 does not name Redis/cache clients explicitly. |
| No generic messaging, repository, or provider framework (D-54) | — | Gap — no check exists |
| No central orchestrator is introduced (D-57) | §14 — FC-31 (approved by D-66) | Planned |
| Stuck work becomes visible without a coordinator (D-57 cost) | §14 — FC-09 (as redefined by D-67) | Planned |
| Idempotency key with a different body is rejected (D-58) | §14 — FC-13 | Planned |
| Outcomes classified into four classes; permanent rejections produce exactly one attempt (D-58) | §14 — FC-24 (permanent and retryable paths only) | Planned. Gap for "unknown", pending OQ-16. |
| Workers share one send workflow but deploy separately (D-58) | — | Gap — no check exists |
| Workers throttle to each provider account's rate limit (D-58) | §14 — FC-30 (approved by D-66) | Planned; values depend on OQ-11 |
| Only single notifications are built (D-48) | — | Gap — no check exists (scope boundary; owner review) |

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-48, D-54, D-57, D-58); context [§8](../architecture-context.md#8-confirmed-decisions). Constraints: HLD [§2.1](../high-level-design.md#21-confirmed-constraints). Trade-offs: HLD [§10](../high-level-design.md#10-trade-offs). Fitness checks: HLD [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69).
- Related ADRs:
  - Related to [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md): D-37 deployment clause, idempotency conflict.
  - Related to [ADR-0003](0003-route-tenant-notifications-to-configured-or-default-provider.md): throttling, routing port.
  - Related to [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md): outcome classes, stuck-work alert.
  - Related to [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md): single status writer.
  - Related to [ADR-0010](0010-use-a-database-per-application-on-shared-postgresql.md): persistence boundary.
  - Related to [ADR-0012](0012-govern-architecture-through-owner-approval-and-fitness-checks.md): fitness checks.
- Diagram: [`../diagrams/notification-platform-hld.drawio`](../diagrams/notification-platform-hld.drawio), page "v1 - Current design".

## Amendments

None.
