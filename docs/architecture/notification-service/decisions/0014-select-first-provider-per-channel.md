# ADR-0014: Select the first provider per channel

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-70 |
| Decision date | 2026-11-04 |
| Record approved | 2026-11-04, by the project owner |
| Approval evidence | The owner selected the providers during TLC planning on 2026-11-04 and asked for the selection to be recorded as a new decision. The owner accepted this record on 2026-11-04, in reply to the implementation-planning summary. |
| Constraints | C-04, C-05, C-14, C-30, C-31, C-48, C-67, C-68 |
| HLD sections | [§4.3](../high-level-design.md#43-provider-routing-boundary), [§5.2](../high-level-design.md#52-dispatch-flow-per-channel-worker), [§5.3](../high-level-design.md#53-callback-flow), [§7.3](../high-level-design.md#73-duplicates-and-idempotency), [§8.3](../high-level-design.md#83-callbacks-tenancy-and-personal-data) |
| Supersedes | — |

## Context

The architecture was written with no provider selected (C-04). Implementation needs one, because workers send through real APIs, and several open questions wait on provider facts (OQ-11, OQ-14, OQ-58). The decisions set the criteria:

- **Confirmed:** status arrives by push only, webhook or queue (D-23, D-24). A provider that reports nothing leaves notifications at `SENT` (D-25).
- **Confirmed:** provider idempotency keys are used where supported, and support is a selection criterion (D-61).
- **Confirmed:** international transfer is a selection criterion (D-62).
- **Confirmed:** at most one provider per tenant per channel (D-42).

Vendor facts below were read from vendor documentation on 2026-11-04. Some OneSignal details came from a truncated page, and the feature designs must re-check them.

| Criterion | Amazon SES | Hosted textbee.dev | OneSignal Free |
|---|---|---|---|
| Status by push | Yes: events through SNS | Yes: webhook | Yes: Event Streams, up to 1,000 events per month |
| Status authenticity | SNS message signature | HMAC-SHA256 over the raw body, no timestamp signed | Static custom header only, no signing |
| Idempotency key on send | None found | None | Yes: `idempotency_key`, valid for 30 days |
| Capacity limits | Account sending quota | Plan and phones: at most 25,000 per month on Scale | Fewer than 1,000 MAU for mobile push; 150 create requests per second |
| Data location | Not yet assessed | Stored on textbee's servers, region not stated | Not yet assessed |

## Decision

**Decided (D-70, 2026-11-04).** The decision log records: "The first provider per channel is Amazon SES for email, hosted textbee.dev for SMS, and the OneSignal Free tier for push."

**Not decided here:**

- Whether these providers are also the platform-wide defaults per channel that D-03 and D-42 require (OQ-59).
- Whether a static shared secret is acceptable proof of authenticity for OneSignal events under QS-07 (OQ-60).
- International transfer, which D-62 requires to be assessed before production. D-70 does not record that assessment.

## Alternatives considered

- **Simulated, non-production adapter, with real providers later** — Not chosen by the owner. It was the recommendation, because it let the pipeline be built before accounts existed. (Source: TLC planning, 2026-11-04.)
- **Stop at the provider port, using only test doubles** — Not chosen by the owner. The deployed pipeline could not send anything. (Source: TLC planning, 2026-11-04.)
- **SMS: Twilio, Zenvia, or Amazon SNS** — Offered and not chosen; the owner named textbee.dev instead. Zenvia and SNS SMS were not researched. (Source: TLC planning, 2026-11-04.)
- **Email: SendGrid or Zenvia** — Offered and not chosen, and not researched. (Source: TLC planning, 2026-11-04.)
- **Push: FCM alone** — Offered and not chosen. FCM's documentation lists no per-message status by push, so push would have stopped at `SENT`. (Source: TLC planning, 2026-11-04.)
- **Push: FCM and APNs separately** — Offered and not chosen. It conflicts with D-42. (Source: TLC planning, 2026-11-04.)
- **Self-hosted textbee** — Offered and not chosen. It keeps message data on controlled infrastructure, at the cost of running its server, MongoDB, Redis, and a Firebase project. (Source: TLC planning, 2026-11-04.)

## Consequences

- **Positive:** work can target real APIs. Every channel has a push status path. OneSignal's idempotency key closes the crash-after-send duplicate window for attempts it covers (§7.3). Replaceability is unchanged, because vendor names stay in adapters (D-54).
- **Negative / accepted risks:**
  - SES and textbee offer no idempotency key, so a crash after the provider call can still cause a duplicate (QS-03).
  - textbee capacity depends on plan limits and phones. One phone is a single point of failure for its account, and carriers do not always report delivery, which leaves `SENT` (D-25).
  - Past 1,000 OneSignal events in a month, push status probably stays at `SENT`. The vendor does not state what happens over the cap.
  - Past the MAU limit, mobile push stops until the plan is upgraded.
  - OneSignal subscriptions belong to an app, so each tenant's mobile app probably needs its own OneSignal app. Free-tier limits across several apps are unverified.
- **Follow-up:** OQ-59, OQ-60, the D-62 assessment, OQ-11 and OQ-14 per provider, OQ-58, I-24 (diagram). Revisit when a Free-tier or plan limit is reached, or if the transfer assessment fails for a provider.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| Vendor logic stays in adapters | [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69) — FC-01 | Planned |
| Status from each provider is authenticated | §14 — FC-05 (the OneSignal part depends on OQ-60) | Planned |
| Each account is throttled to its configured rate | §14 — FC-30 | Planned |
| Provider idempotency keys are used where supported | Gap — no check exists; ADR-0002 records the same gap | Gap — planned as an adapter test in `.specs/features/push-onesignal/` |
| International transfer is assessed before production | Gap — no check exists; ADR-0011 records the same gap | Gap — no check exists |

## Links

- Refined by [ADR-0015](0015-use-selected-providers-as-defaults-and-replaceable-onesignal-authentication.md) (D-71, D-72), which settles OQ-59 and OQ-60.
- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log); [context §8](../architecture-context.md#8-confirmed-decisions) (D-70).
- Related ADRs: Related to [ADR-0003](0003-route-tenant-notifications-to-configured-or-default-provider.md) (routing, D-42); Related to [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md) (D-61); Related to [ADR-0007](0007-ingest-provider-status-by-push-through-callbacks-app.md) (D-23 to D-25); Related to [ADR-0011](0011-protect-personal-data-with-encryption-and-bounded-retention.md) (D-62).
- Feature notes and vendor sources: `.specs/features/email-dispatch/context.md`, `.specs/features/sms-textbee/context.md`, `.specs/features/push-onesignal/context.md`.

## Amendments

None.
