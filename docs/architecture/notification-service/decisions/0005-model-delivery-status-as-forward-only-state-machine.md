# ADR-0005: Model delivery status as a forward-only state machine

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-26, D-29, D-30, D-41, D-60 |
| Decision date | 2026-10-22 |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | HLD [§2.3](../high-level-design.md#23-decision-log) decision log: D-26 confirmed during review of revision 9, D-29 and D-30 during review of revision 10, D-41 during review of revision 14, D-60 during the item-by-item review of revision 18. This record itself has not been reviewed. Record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-07, C-08, C-32, C-35, C-36, C-47, C-66 |
| HLD sections | [§6.3](../high-level-design.md#63-delivery-status-model), [§7.2](../high-level-design.md#72-ordering), [§5.4](../high-level-design.md#54-status-maintenance-flow), [§7.4](../high-level-design.md#74-retries-and-dead-letter-handling) |
| Supersedes | — |

## Context

The Delivery-status application is the single writer of delivery status (C-07, [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md)). It receives facts from three independent sources: acceptance facts from the API, attempt outcomes from the channel workers, and provider status events from the provider callbacks application. These arrive on separate streams, so no order exists between them even on Kafka, and provider callbacks may arrive out of order relative to each other ([§7.2](../high-level-design.md#72-ordering)). **Confirmed:** submission, dispatch, callbacks, and status updates must be treated as potentially duplicated or out of order (C-08), and there is no ordering requirement across notifications (D-49, [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md)). The broker must stay replaceable (C-02), and RabbitMQ and SQS standard queues do not preserve order either.

The platform therefore needs a status vocabulary and transition rules whose result does not depend on message order: a callback can overtake the worker's attempt outcome, a late `SENT` can arrive after `DELIVERED`, and two providers' reports can conflict. It also needs to distinguish failures the platform caused or observed before the provider accepted the send from failures the provider reported afterwards, because the latter never trigger a resend (D-11, [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md)).

## Decision

The decision-log wording (context §8, canonical) is:

- **D-26:** "Status vocabulary: PROCESSING (still processing on the platform's side), SENT (sent to the provider), DELIVERED (provider reported delivery), BOUNCED (provider reported a bounce; probably email only, but usable by other channels), NOT DELIVERED (provider reported errors on delivery)." (C-32)
- **D-29:** "A FAILED status, with a status reason, covers failures before the provider accepted the notification: the provider rejecting the send, retries exhausted, no eligible provider, or an unprocessable message. NOT DELIVERED is set only when a provider reports a delivery failure." (C-35)
- **D-30:** "When final statuses conflict, the first final status wins, for now." (C-36)
- **D-41:** "A manual DLQ replay by an administrator may reopen a notification from FAILED to PROCESSING. This is the only exception to D-30." (C-47)
- **D-60:** "Status only moves forward (PROCESSING, then SENT, then a final status), except for a manual DLQ replay. A provider report may skip SENT. The attempt number is a field, not a status. FAILED reasons start as REJECTED_BY_PROVIDER, RETRIES_EXHAUSTED, NO_ELIGIBLE_PROVIDER, UNPROCESSABLE. BOUNCED and NOT DELIVERED may carry a normalized provider reason." (C-66)

Net position: status is a forward-only state machine ranked `PROCESSING` < `SENT` < {`DELIVERED`, `BOUNCED`, `NOT DELIVERED`, `FAILED`}. A fact that would lower the rank, or a second final fact, is kept in history and does not change current status. The single way back is an administrator's manual DLQ replay from `FAILED` to `PROCESSING`. The state diagram and the full rule text are in HLD [§6.3](../high-level-design.md#63-delivery-status-model).

Related decisions recorded elsewhere: `SENT` as the final known status when a provider never reports further (D-25) is in [ADR-0007](0007-ingest-provider-status-by-push-through-callbacks-app.md). The replay mechanism itself (admin endpoint, original notification ID, DLQ alert, D-39) is in [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md).

Deferred: the "for now" in D-30 leaves conflict precedence open to revision, and the interaction between `FAILED` and attempt timeouts depends on OQ-16, which the owner deferred (D-10).

## Alternatives considered

- **Event log as the authority, with status rebuilt by replay** — Rejected (D-33). It concerns the source of truth rather than the transition rules and is recorded in [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md); it is listed here only because forward-only rules are what make a non-replayed store safe. (Source: HLD §6.2.)
- **Relying on broker ordering for status correctness** — not adopted: no cross-stream order exists, providers reorder callbacks, and RabbitMQ/SQS do not guarantee order. (Source: HLD §7.2; §10 "Order-independent status rules".)
- **Channel-specific precedence between conflicting final statuses** — not rejected, deferred: HLD §6.3 notes it "can be introduced later, if needed, without changing the vocabulary". (Source: HLD §6.3.)
- For the vocabulary itself (D-26), the `FAILED` / `NOT DELIVERED` split (D-29), and the replay exception (D-41): not recorded when the decision was made.

## Consequences

- **Positive:** status is deterministic for any delivery order and any duplication, on any broker (QS-02, C-02). The Delivery-status application only records facts and has no path back to dispatch. `FAILED` with a reason tells tenants the notification never reached a provider, separately from provider-reported outcomes. The persistence port needs only a conditional atomic update per notification ([§4.5](../high-level-design.md#45-persistence-boundary)), which PostgreSQL and the evaluated alternatives can provide by different mechanisms.
- **Negative / accepted risks:**
  - First final wins can leave a status that is wrong from the recipient's point of view: if an attempt times out after the request reached the provider, the platform may record `FAILED` (retries exhausted) and later receive `DELIVERED`, which stays in history only ([§6.3](../high-level-design.md#63-delivery-status-model)). Retrying in that case can also send twice.
  - A genuine later correction from a provider (for example `DELIVERED`, then `BOUNCED`) does not change current status.
  - The replay exception makes `FAILED` the only non-terminal final status; it must be restricted to the administrative path and recorded in history with the administrator's identity ([§7.4](../high-level-design.md#74-retries-and-dead-letter-handling)).
  - Transition rules must be designed carefully per channel ([§10](../high-level-design.md#10-trade-offs)).
- **Follow-up:**
  - OQ-16 (timeouts and unknown outcomes) is still open; it may refine D-29/D-30 and ADR-0004.
  - The notification lifecycle state diagram is a pending artifact (HLD [§13](../high-level-design.md#13-follow-up-artifacts) item 2).
  - Exact contract names (for example `NOT_DELIVERED`) and the final list of reasons belong in the contracts (HLD §13).
  - Revisit D-30 if a channel needs precedence between final statuses.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| Shuffled and duplicated facts give monotonic, deterministic status under the rank order; a late `SENT` never changes a provider-reported final status | [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69) — FC-02 | Planned |
| A second final fact never replaces the first (D-30) | §14 — FC-02 | Planned |
| Every `FAILED` record has a reason (D-29) | §14 — FC-02 | Planned |
| Only a manual DLQ replay reopens a final status, and only from `FAILED` to `PROCESSING` (D-41) | §14 — FC-28 (approved by D-66) | Planned |
| `NOT DELIVERED` is set only from a provider report, never for a pre-provider failure (D-29) | Gap — no check exists | Gap — no check exists |
| The attempt number is a field, not a status; `BOUNCED` / `NOT DELIVERED` carry a normalized provider reason when the provider gives one (D-60) | Gap — no check exists | Gap — no check exists |

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-26, D-29, D-30, D-41, D-60); context §8; constraints HLD [§2.1](../high-level-design.md#21-confirmed-constraints).
- Open questions: HLD [§11](../high-level-design.md#11-open-questions) (OQ-16; resolved OQ-15, OQ-45, OQ-46, OQ-49).
- Related ADRs: Related to [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md) (retries, DLQ replay, D-39); Related to [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md) (single writer, source of truth); Related to [ADR-0007](0007-ingest-provider-status-by-push-through-callbacks-app.md) (D-25); Related to [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md) (duplicates, no ordering); Related to [ADR-0012](0012-govern-architecture-through-owner-approval-and-fitness-checks.md) (fitness checks).
- Lifecycle state diagram: pending (HLD §13 item 2).

## Amendments

None.
