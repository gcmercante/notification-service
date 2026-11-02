# ADR-0013: Correlate provider status reports that arrive before the attempt outcome

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-68 (from the HLD [§5.3](../high-level-design.md#53-callback-flow) "Correlation race" recommendation). Left open: OQ-57 (hold period, retention), OQ-58 (provider-reference scope) |
| Decision date | 2026-11-02 |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | D-68, confirmed by the project owner on 2026-11-02 by accepting this record (with ADR-0001 to ADR-0013). The owner had asked for this ADR the same day, because HLD §5.3 said the correlation race "Needs an ADR". |
| Constraints | C-07, C-08, C-55, C-64, C-66, C-67 (also relies on C-39, C-51) |
| HLD sections | [§5.3](../high-level-design.md#53-callback-flow), [§5.4](../high-level-design.md#54-status-maintenance-flow), [§4.5](../high-level-design.md#45-persistence-boundary), [§6.1](../high-level-design.md#61-ownership-table-confirmed-d-58-d-59), [§6.3](../high-level-design.md#63-delivery-status-model), [§7.1](../high-level-design.md#71-delivery-semantics-confirmed-d-61)–[§7.3](../high-level-design.md#73-duplicates-and-idempotency), [§7.6](../high-level-design.md#76-stuck-work-and-reconciliation) |
| Supersedes | — |

## Context

A provider event identifies a notification only by the provider's message reference. The Delivery-status app learns which notification that reference belongs to from the worker's attempt outcome, which carries the reference ([§5.2](../high-level-design.md#52-dispatch-flow-per-channel-worker), [§6.1](../high-level-design.md#61-ownership-table-confirmed-d-58-d-59): "Populated from attempt outcomes").

The two facts travel on different topics: attempt outcomes go through the worker's outbox and relay, and provider events go through the callbacks app's outbox and relay. No order exists between those topics, even on Kafka ([§7.2](../high-level-design.md#72-ordering)). A provider can also call back before the worker has committed the outcome, or before the worker has even received the provider's response. So the provider event can reach the Delivery-status app before the outcome that makes it matchable.

Forces:

- **Confirmed:** facts may be duplicated or arrive out of order (C-08). Broker ordering is never a correctness requirement (D-49, C-55).
- **Confirmed:** every hop is at-least-once, and consumers ack only after their durable side effect (D-61, C-67, [§7.1](../high-level-design.md#71-delivery-semantics-confirmed-d-61)).
- **Confirmed:** the Delivery-status app is the single writer of status (D-33, C-07, [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md)). It consumes attempt outcomes and provider events, applies transition rules that tolerate events arriving out of order, and maintains the provider-reference correlation (D-58, C-64, §5.4, [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md)). Who owns correlation is therefore settled. **How** an early report is handled is not.
- **Confirmed:** status only moves forward, a provider report may skip `SENT`, and the first final status wins (D-60, D-30, [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md)).
- **Confirmed:** each application has its own database (D-45, C-51). The Delivery-status app cannot read a worker's attempt ledger.
- **Open question:** whether a provider reference is unique per provider or only per provider account. No provider is selected (C-04), so this is unknown.

## Decision

**Decided (D-68, 2026-11-02).** The decision log records: "The handling of provider status reports that arrive before the attempt outcome is approved as recorded in ADR-0013: the Delivery-status app parks unmatched provider events durably before acknowledging them, applies them through the normal transition rules when an attempt outcome establishes the correlation, and raises an alert, changing no status, for any event still unmatched after a bounded period. Parking and reconciling stay inside the Delivery-status app. The hold period, retention, and correlation-key scope remain open (OQ-57, OQ-58)."

In detail (taken from the HLD §5.3 recommendation):

1. When the Delivery-status app receives a provider event whose provider reference matches no known correlation, it **parks** the event durably in its own database and only then acks it. This follows D-61.
2. When an attempt outcome later establishes the correlation for that reference, the app **reconciles**: it applies the parked events through the normal transition rules and deduplication (§6.3, §7.3). The resulting status and history are the same as if the facts had arrived in the other order. This is what FC-02 already requires of the rules.
3. Parking lasts for a **bounded period**. A parked event that is still unmatched after that period **raises an alert** and changes no status. The unmatched-callback count is already a proposed metric ([§9](../high-level-design.md#9-observability-and-operations)).
4. Parking and reconciling stay inside the Delivery-status app. Workers and the callbacks app are not changed, no new cross-application call is added, and no orchestrator is introduced (D-57).

**Not decided here (Open questions, no numbers proposed):**

- **The length of the hold period**, and what happens to an event after it: keep it for a late match, or discard it, and how long it is retained under §6.4. Provider events carry only identifiers and statuses (§6.4), so a parked event holds no content or recipient data. How the period relates to the D-40 five-minute `PROCESSING` alert also needs to be settled.
- **Interaction with OQ-16 (timeouts and unknown outcomes, deferred).** The race itself starts only after the provider has accepted a send, so it does not depend on the provider-call timeout. However, an attempt whose outcome is *unknown* (a timeout or crash after the send, §7.3) may never produce a provider reference. Provider events for that send can then never match. They end as unmatched alerts, and the notification may become `FAILED` (retries exhausted) even though the provider delivered it (§6.3). That case must be settled together with OQ-16.
- **Correlation key scope**, which depends on provider-reference uniqueness (see Context).

## Alternatives considered

- **Worker records the provider reference durably before the provider can call back** — Not recommended by the HLD (§5.3 option 2). Retrospective analysis: the worker usually learns the reference only from the provider's response, after the provider may already have called back. Under D-45 the worker's ledger is not visible to the Delivery-status app, and the outcome still crosses a separate topic. The race at the status app would remain.
- **Status app parks unmatched events and reconciles them** — Recommended (HLD §5.3 option 1). This is the Decision above.
- **Drop unmatched provider events** — Not adopted (retrospective). Valid provider facts would be lost, and notifications would stay at `SENT` when they actually progressed. This would undo the at-least-once handling of D-61.
- **Refuse to ack unmatched events and rely on broker redelivery until the correlation appears** — Not adopted (retrospective). On Kafka this blocks the partition or forces offset juggling. Redelivery and dead-letter behaviour differ across Kafka, RabbitMQ, and SQS, so correctness would depend on broker semantics (C-02, §4.4).
- **Correlate on a platform identifier that the provider echoes back** — Not evaluated (retrospective). Whether any provider supports this is unknown until providers are selected. It could reduce the race but could not be the base design.

## Consequences

- **Positive:** order-independence for this race comes from the status app alone, so it works on any broker (C-02). The rank rules and first-final-wins stay unchanged. No new cross-application dependency is added.
- **Negative / accepted risks:**
  - The status store gains a new kind of data, parked provider events. It needs lookup by provider reference, which is capability 4 in §4.5, and it needs expiry. It is listed in the HLD ownership tables (§4.5, §6.1) and the §6.4 retention table, with retention still open (OQ-57).
  - An outcome that never arrives (for example an unknown outcome, OQ-16) turns valid provider facts into alerts.
  - The hold period trades alert noise against how late an alert fires.
- **Follow-up:** the hold-period (OQ-57), OQ-16, and key-scope (OQ-58) questions above. HLD §4.5, §6.1, and §6.4 list parked events since revision 31 (retention still OQ-57). Add the callback-before-outcome sequence diagram (HLD [§13](../high-level-design.md#13-follow-up-artifacts) item 3). Revisit this ADR if the selected providers echo a platform identifier.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| Final status and history do not depend on whether the provider event or the attempt outcome arrives first, including duplicates | [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69) — FC-02 (partial: it covers the transition rules on correlated facts, not parking) | Planned |
| An unmatched provider event is stored durably before ack, survives a restart, and is applied exactly once when its correlation appears | §14 — FC-32 (approved by D-69) | Planned |
| An event still unmatched after the hold period raises an alert and changes no status | §14 — FC-33 (approved by D-69); the hold period is OQ-57 | Planned |
| Parking adds no orchestrator and no cross-application coordination | §14 — FC-31 (approved by D-66) | Planned |

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log); [context §8](../architecture-context.md#8-confirmed-decisions) (D-30, D-33, D-45, D-49, D-57, D-58, D-60, D-61 cited as context).
- Open questions: HLD [§11](../high-level-design.md#11-open-questions) (OQ-16).
- Related ADRs: Related to [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md) (D-30, D-60); Related to [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md) (single writer, D-33); Related to [ADR-0007](0007-ingest-provider-status-by-push-through-callbacks-app.md) (push ingestion, D-25; it defers the race to this ADR); Related to [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md) (at-least-once, D-61, D-49); Related to [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md) (D-58 responsibilities, D-57).
- Sequence diagram for callback-before-outcome: pending (HLD §13 item 3).

## Amendments

None.
