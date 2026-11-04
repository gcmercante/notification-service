# ADR-0004: Retry failed sends with capped exponential backoff and equal jitter, and replay dead letters manually

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-07, D-10, D-11, D-15, D-17, D-18, D-39, D-40, D-67 |
| Decision date | 2026-10-22; D-67 on 2026-11-02 |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | Decisions confirmed in the HLD reviews listed in HLD [§2.3](../high-level-design.md#23-decision-log): revision 2 (D-07), revision 3 (D-10, D-11), revision 4 (D-15), revision 5 (D-17), revision 6 (D-18), revision 13 (D-39, D-40); D-67 during the ADR review of 2026-11-02 (HLD revision 30). This record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-17, C-20, C-21, C-24, C-26, C-45, C-46 |
| HLD sections | §5.2, §7.4 (incl. P-05), §7.5, §7.6, §9, §10 |
| Supersedes | — |

## Context

Channel workers call external providers that can fail, throttle, or be briefly unavailable. Without a stated policy, each worker would retry differently, and retries could flood a recovering provider that all tenants routed to it share (C-14, QS-09). Several facts constrain the policy:

- **Confirmed:** there is no failover or fallback; routing selects one provider per tenant and channel (C-05, C-12, C-13), so retrying means retrying the **same** provider.
- **Confirmed:** every broker hop is at-least-once and duplicates are minimized, not eliminated (D-61, [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md)). A retry is an extra provider call and may itself produce a duplicate.
- **Confirmed:** workers classify each outcome as accepted, permanent, retryable, or unknown (D-58, [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md)); see [HLD §5.2](../high-level-design.md#52-dispatch-flow-per-channel-worker).
- **Confirmed:** there is no central orchestrator (D-57), so stuck work must be detected explicitly ([HLD §7.6](../high-level-design.md#76-stuck-work-and-reconciliation)).
- **Open question:** timeouts, and whether an *unknown* outcome is retried (risking a duplicate) or ends the notification (risking loss), were explicitly deferred by the owner ([OQ-16](../high-level-design.md#112-still-open)).

## Decision

The decision log ([context §8](../architecture-context.md#8-confirmed-decisions)) records, verbatim:

- **D-07:** "When a send fails, it is retried with exponential backoff up to 3 times before the notification fails for good."
- **D-10:** "At most 4 attempts in total (the original plus 3 retries). Exponential backoff with base 1 s and cap 30 s. Permanent rejections are not retried. Timeout handling is not yet defined."
- **D-11:** "A failure reported by a provider after it accepted a send is final. It does not trigger a resend."
- **D-15:** "Retry delay before retry *n* (*n* = 1 for the first retry) is d<sub>n</sub> = min(cap, base × 2<sup>n−1</sup>), with base = 1 s and cap = 30 s. Under D-10 the delays are 1 s, 2 s, and 4 s."
- **D-17:** "Jitter is applied to the D-15 retry delays. The form is set by D-18."
- **D-18:** "Equal jitter: actual retry delay = d<sub>n</sub>/2 + random in [0, d<sub>n</sub>/2]."
- **D-39:** "No maximum notification age for now. DLQ messages are replayed manually by administrators through an admin endpoint, keeping the original notification ID. Alert when the DLQ grows."
- **D-40:** "Alert when a notification stays in PROCESSING for more than 5 minutes."
- **D-67:** "FC-09 is redefined around D-40: a notification that stays in PROCESSING for more than 5 minutes must raise an alert. A notification at SENT with no further provider report is not stuck (D-25) and raises no alert."

**Net position (D-07 as refined by D-10, D-15, D-17, D-18):** at most 4 provider attempts to the same provider; retry delays d<sub>n</sub> of 1 s, 2 s, and 4 s before jitter (base 1 s, cap 30 s; the cap is not reached within 4 attempts); equal jitter, so actual delays are 0.5–1 s, 1–2 s, 2–4 s and the total wait is 3.5–7 s plus attempt durations; permanent rejections get one attempt; provider-reported failures after acceptance are final (D-11). D-40 is an operational stuck-work alert, grouped here because it is sized against this retry window (decisions README §7.1).

**Deferred:** timeouts and the treatment of unknown outcomes (D-10, OQ-16). A later ADR will refine this one (decisions README §3.3 rule 3).

**Not decided here (Proposed in [HLD §7.4](../high-level-design.md#74-retries-and-dead-letter-handling)):** counting provider attempts rather than broker deliveries; only unprocessable messages go to the DLQ, while permanent rejections and exhausted retries do not; the broker-specific retry mechanism. Replay reopening `FAILED` to `PROCESSING` is D-41, recorded in [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md).

## Alternatives considered

- **Full jitter** (random in [0, d<sub>n</sub>]) — Rejected: a retry can follow almost instantly, so the retry window can shrink to almost nothing. (Source: HLD §7.4, P-05; owner review rev 6.)
- **Jitter added on top** (d<sub>n</sub> + random in [0, *j*]) — Not selected: exceeds the D-15 values and needs another parameter. (Source: HLD §7.4, P-05.)
- **Retry on the tenant's default provider** — Rejected: retries go to the same provider; the default is never a fallback. (Source: OQ-24 resolved by D-07; HLD §4.3, §10.)
- **Resend after a provider-reported failure** — Rejected by D-11: the status app stays a pure recorder of facts with no feedback loop into dispatch. (Source: OQ-32; HLD §10.)
- For the backoff count and base/cap (D-10, D-15), the DLQ replay mode and maximum age (D-39), and the 5-minute threshold (D-40): not recorded when the decision was made.

## Consequences

- **Positive:** predictable, bounded load on providers; retries spread out so a recovering provider is not hit in lockstep; a quick final answer to tenants (HLD §10). Replay keeps the original notification ID, so deduplication still works.
- **Negative / accepted risks:**
  - A provider disruption longer than the window (about 7 s plus attempt durations) makes every in-flight send to that provider fail for good, for every tenant routed to it ([HLD §7.5](../high-level-design.md#75-dependency-outages)). Accepted by the owner (D-15).
  - A temporary provider-side problem reported later by callback is never recovered (D-11).
  - Delays are random, so tests must inject a fixed random source.
  - Misclassifying permanent vs. retryable wastes shared quota or loses recoverable sends; classification is per adapter.
  - Retrying an unknown outcome may duplicate a send (OQ-16).
  - Manual-only replay means DLQ recovery depends on administrator action; no maximum age means DLQ contents are bounded only by retention (D-38, [ADR-0011](0011-protect-personal-data-with-encryption-and-bounded-retention.md)).
- **Follow-up:**
  - OQ-16 (timeouts and unknown outcomes) — will refine this ADR.
  - OQ-11 (provider rate limits) affects throttling alongside retries (D-58).
  - DLQ-growth alert threshold awaits targets (D-34).
  - Ownership of DLQ inspection and replay tooling is open (HLD §9).
  - Revisit if the attempt count is raised (the 30 s cap then matters) or if failover is ever approved.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| 4 attempts max; delays follow D-15 with equal jitter within [d<sub>n</sub>/2, d<sub>n</sub>]; cap from *n* = 6; permanent rejection gives 1 attempt; no default-provider call; no resend after a provider-reported failure (D-07, D-10, D-11, D-15, D-17, D-18) | [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69) — FC-24 | Planned |
| Replay through the admin endpoint keeps the original notification ID; DLQ growth raises an alert (D-39) | §14 — FC-28 (approved by D-66) | Planned |
| No maximum notification age (D-39) | — | Gap — no check exists |
| Alert when a notification stays in `PROCESSING` more than 5 minutes (D-40) | §14 — FC-09, redefined by D-67 around the 5-minute `PROCESSING` threshold | Planned |
| Timeouts and unknown outcomes | — (deferred, OQ-16) | Gap — no check exists |

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-07, D-10, D-11, D-15, D-17, D-18, D-39, D-40); [context §8](../architecture-context.md#8-confirmed-decisions). Constraints: HLD [§2.1](../high-level-design.md#21-confirmed-constraints).
- Runtime behaviour: HLD [§5.2](../high-level-design.md#52-dispatch-flow-per-channel-worker), [§7.4](../high-level-design.md#74-retries-and-dead-letter-handling) (incl. P-05), [§7.5](../high-level-design.md#75-dependency-outages), [§7.6](../high-level-design.md#76-stuck-work-and-reconciliation), [§9](../high-level-design.md#9-observability-and-operations); trade-offs [§10](../high-level-design.md#10-trade-offs).
- Related ADRs:
  - Related to [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md) (D-58 outcome classes; D-57 stuck-work detection).
  - Related to [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md) (D-61 at-least-once, worker outbox).
  - Related to [ADR-0003](0003-route-tenant-notifications-to-configured-or-default-provider.md) (D-55 retries keep the first attempt's provider).
  - Related to [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md) (D-41 replay reopens `FAILED`; D-29 failure reasons).
  - Related to [ADR-0009](0009-isolate-tenants-and-integrations-and-separate-admin-traffic.md) (D-12 separated admin surface used for replay).
  - Refined by a future ADR on timeouts (OQ-16).
- Contracts and sequence diagrams (DLQ replay, worker crash after send): not yet produced (HLD [§13](../high-level-design.md#13-follow-up-artifacts) items 3–4).

## Amendments

None.
