# ADR-0007: Ingest provider status by push only, through the provider-callbacks application

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-20, D-22, D-23, D-24, D-25 |
| Decision date | 2026-10-22 |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | Decisions confirmed during the HLD reviews of revision 6 (D-20), revision 7 (D-22), and revision 8 (D-23 to D-25); decision log, HLD §2.3. This record itself is not yet reviewed. Record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-28, C-30, C-31 (also relies on C-08, C-14, C-43) |
| HLD sections | [§5.3](../high-level-design.md#53-callback-flow), [§7.6](../high-level-design.md#76-stuck-work-and-reconciliation), [§8.3](../high-level-design.md#83-callbacks-tenancy-and-personal-data); see also [§6.3](../high-level-design.md#63-delivery-status-model) |
| Supersedes | — |

## Context

After a provider accepts a send, the only source of later outcomes (delivered, bounced, not delivered) is the provider itself. No provider has been selected yet, and providers report status in different ways: some call a webhook, some publish to a queue they host, some only offer an API to poll. The delivery-status application is the single writer of status (ADR-0006), so provider facts need one way in that does not write status itself.

Forces:

- **Confirmed (C-28):** a dedicated application receives provider status updates and publishes them to a Kafka topic, which the delivery-status app consumes.
- **Confirmed (C-08):** callbacks may be duplicated or out of order.
- **Confirmed (C-14):** provider accounts and credentials are platform-owned, so authenticating provider input is a platform concern.
- **Open question (OQ-14):** which callback authentication each provider offers is unknown until providers are selected.
- Polling providers costs provider API quota shared across tenants and needs its own state (what to poll, and when) ([§5.3](../high-level-design.md#53-callback-flow), "Deferred: polling").

## Decision

Quoted from [context §8](../architecture-context.md) (canonical wording):

- **D-20:** "Providers report status updates in provider-specific ways. The provider-callbacks application receives them and publishes them to a Kafka topic, from which the status projector (delivery-status application) updates status."
- **D-22:** "Status is received from each provider by polling, webhook, or queue, depending on what that provider offers. Whatever a provider supports is implemented, even if it is only one of the three. Narrowed by D-23 and D-24."
- **D-23:** "Only push mechanisms (webhook or queue) are used to receive provider status. There is no reconciliation polling."
- **D-24:** "The platform does not poll providers for now; it only sends notifications. Polling is deferred to a future feature that will update states providers did not report."
- **D-25:** "For outcomes a provider never reports, "accepted by provider" is the final known status, for now."

**Net position (D-22 as narrowed by D-23 and D-24; C-30, C-31):** each provider's status is received by webhook or by queue, whichever that provider offers; one is enough. Nothing polls providers in the current scope. All provider status enters through the provider-callbacks application and reaches the delivery-status app only through Kafka. When a provider never reports a further outcome, `SENT` (the D-26 name for "accepted by provider") is the final known status.

**Deferred:** polling, as a future feature that updates states providers did not report (D-24). It will get its own design and decision; its placement in the provider-callbacks app is only a likely home, not decided ([§5.3](../high-level-design.md#53-callback-flow)).

**Recorded elsewhere:** the outbox in the provider-callbacks app is D-37 ([ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md)). The status semantics around `SENT`, `NOT DELIVERED`, and the rank order are D-26, D-29, D-30 ([ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md)).

The mechanism per provider being chosen at onboarding (not per tenant), the queue details, and the deployment shape inside the app are **Proposed** in [§5.3](../high-level-design.md#53-callback-flow) and are not part of this decision.

## Alternatives considered

- **Polling providers for status** — part of the original D-22 ("polling, webhook, or queue"), then removed from the current scope by D-23 and D-24. **Deferred, not rejected:** D-24 keeps it as a future feature. (Source: HLD §2.3, owner review of revision 8.)
- **Reconciliation polling alongside push** (poll to catch reports a push mechanism missed) — Rejected by D-23. (Source: HLD §2.3, OQ-43, owner review of revision 8.)
- No other alternatives were recorded for D-20 or D-25. HLD [§10](../high-level-design.md#10-trade-offs) has no row for this decision.
- **(retrospective)** Having the delivery-status app or the channel workers receive provider input directly would mix provider-specific authentication and normalization into components that should stay provider-neutral or focused on sending. Not discussed when the decision was made.

## Consequences

- **Positive:**
  - One entry point and one topic for every inbound provider fact; the status projector cannot tell, and need not know, whether a fact came by webhook or queue ([§5.3](../high-level-design.md#53-callback-flow)).
  - Provider-specific authentication and normalization stay in that provider's adapter (QS-04, QS-07); the delivery-status app remains the single status writer.
  - No polling load on shared provider quotas and no polling state to operate.
- **Negative / accepted risks:**
  - A provider whose status can only be polled supplies no status updates for now; its notifications stop at `SENT`. This must be weighed when selecting providers ([§5.3](../high-level-design.md#53-callback-flow)).
  - A lost or never-sent push leaves a notification at `SENT` with no recovery path. `SENT` without a further report is a valid final known state and is not treated as stuck ([§7.6](../high-level-design.md#76-stuck-work-and-reconciliation)); integrations cannot distinguish "delivered but unreported" from "lost".
  - Webhook endpoints are public by necessity and need rate limiting and minimal parsing before verification ([§8.3](../high-level-design.md#83-callbacks-tenancy-and-personal-data)).
  - A callback can arrive before the worker's attempt outcome that carries the provider reference; the correlation race is handled by the delivery-status app ([§5.3](../high-level-design.md#53-callback-flow), "Correlation race"), not by this decision.
- **Follow-up:**
  - **OQ-14** (open): callback authentication per provider; depends on provider selection.
  - The future polling feature (D-24): its own design, placement, and quota handling. Revisit trigger: a selected provider offers polling only, or the per-provider share of notifications that never get past `SENT` ([§9](../high-level-design.md#9-observability-and-operations)) becomes material.
  - HLD [§5.3](../high-level-design.md#53-callback-flow) says the correlation-race recommendation "Needs an ADR"; it is not covered by this record.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| Unauthenticated or replayed provider input (forged webhook, invalid queue message) never changes status (D-20, D-22; QS-07) | §14 — FC-05 QS-07 inbound status trust | Planned |
| Webhook and queue produce the same provider-neutral event, so the mechanism is invisible downstream (D-22 net position) | §14 — FC-06 D-22 mechanism equivalence | Planned |
| No code path polls a provider's status API in this scope (D-23, D-24) | §14 — FC-07 D-24 no polling | Planned |
| Provider input is accepted and published even while Kafka is unavailable (D-20 path; outbox clause owned by D-37, ADR-0002) | §14 — FC-17 D-37 callbacks outbox | Planned |
| Provider status reaches the delivery-status app only through the Kafka topic; the callbacks app writes no status (D-20) | Gap — no check exists | — |
| A notification at `SENT` with no further report stays `SENT` and is not flagged as stuck (D-25) | §14 — FC-09 as redefined by D-67 (a notification at `SENT` with no further report raises no alert) | Planned |

None of the cited rows (FC-05, FC-06, FC-07, FC-17) is marked *(Proposed)*; all were approved by D-65.

**Note:** FC-09 originally read as contradicting D-25 and [§7.6](../high-level-design.md#76-stuck-work-and-reconciliation). D-67 (2026-11-02) redefined it around D-40, so it now supports D-25.

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-20, D-22, D-23, D-24, D-25); [context §8](../architecture-context.md). Constraints: HLD [§2.1](../high-level-design.md#21-confirmed-constraints) (C-28, C-30, C-31). Open questions: HLD [§11](../high-level-design.md#11-open-questions) (OQ-14). Fitness checks: HLD [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69).
- Related ADRs:
  - Related to [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md) — D-37, the callbacks-app outbox.
  - Related to [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md) — `SENT` and the other status semantics (D-25 also defines one).
  - Related to [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md) — single status writer; no push to integrations (D-21).
  - Related to [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md) — provider adapters and the choreographed pipeline.
- Diagram: [`notification-platform-hld.drawio`](../diagrams/notification-platform-hld.drawio), page "v1 - Current design" (provider status ingress, webhook and queue flows).
- Contracts: provider-event contract and the callback-before-outcome sequence diagram, once produced (HLD §13).

## Amendments

None.
