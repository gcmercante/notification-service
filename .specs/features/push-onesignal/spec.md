# Push through OneSignal Specification

## Problem Statement

The platform must send push notifications, and the owner selected the OneSignal Free tier (AD-001). OneSignal offers a real idempotency key, which helps QS-03. It also has hard Free-plan limits, unsigned events, and an API that reports some failures with HTTP 200. This feature adds the push worker on the shared dispatch workflow and handles those traits explicitly.

## Goals

- [ ] A push is sent through OneSignal and reaches `SENT`.
- [ ] A broker-level resend of one attempt cannot produce a second push, through the idempotency key.
- [ ] Reaching the Event Stream cap leaves notifications at `SENT`, with no wrong status.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Device registration and SDK integration | Happens in tenants' mobile apps |
| OneSignal email and SMS | Channels use SES and textbee (AD-001) |
| Segments and filters | Single notifications only (D-48) |
| Web push callbacks | Configured separately by OneSignal and not selected |
| Paid OneSignal plan | Owner chose Free; revisit when limits are reached |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Recipient for push | OneSignal subscription ID (UUID), sent with `include_subscription_ids` | OneSignal holds device tokens, and a malformed ID returns 400 | n |
| OneSignal apps per tenant | A provider account reference names one OneSignal app; each tenant's mobile app needs its own account entry | Subscriptions belong to an app, and accounts are platform-owned (C-14). Free-tier limits apply per app and are to be checked for several apps | n |
| Events subscribed | Only received and failed push events, not sent, clicked, or unsubscribed | Each event counts against 1,000 per month. Subscribing to one more type could halve the status capacity | n |
| Status mapping | Received to `DELIVERED`; failed to `NOT_DELIVERED` with normalized `failure_reason` | D-26 and D-29. Exact event kind values are not stated in the page read and must be confirmed in design | n |
| Event authentication | A static secret in a custom header, compared in constant time, replaceable at any time | Confirmed by the owner for now (D-72). OneSignal offers no signing, so QS-07 is weaker here | y |
| Reading of "ready to change at any time" | Changes stay inside OneSignal's authenticator and configuration, and the secret rotates with no code change | Accepted by the owner with ADR-0015 | y |
| Replay protection | Dedupe on `event.id` | Docs state each event has a unique `event.id`. A captured request can be replayed only as a duplicate | n |
| Provider reference | `message.id`, the send response's `id` | Both identify the OneSignal notification | n |
| Idempotency key | A UUID derived stably from the notification ID and attempt number | D-61 calls for a stable attempt identity; OneSignal requires a UUID valid for 30 days | n |
| Unknown outcome for OneSignal (OQ-16) | Same default as email-dispatch: never resend | Keeps one policy for now; the key makes a safe retry possible later (see context) | n |
| Empty `id` with HTTP 200 | Permanent failure, so `FAILED` with `REJECTED_BY_PROVIDER` | Docs: an empty `id` means the message was not sent, usually with no subscribed target | n |
| Throttle value (OQ-11) | 150 requests per second per app, configured below that | Documented Free-plan create limit | n |
| 429 handling | Retryable under the D-15 policy, ignoring `Retry-After` | D-15 fixes the delays. The vendor suggests waiting longer, so sustained 429s end in `RETRIES_EXHAUSTED` | n |
| International transfer (D-62) | Assessed before production | D-62 makes it a selection criterion | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Send push through OneSignal ⭐ MVP

**User Story**: As a tenant, I want push notifications sent through the platform's OneSignal account so that my app's users receive them.

**Why P1**: Push is a confirmed channel.

**Acceptance Criteria**:
1. The push worker SHALL run the same dispatch workflow as the email worker and differ only in channel validation, adapters, and outcome mapping. [PSH-01]
2. WHEN the worker sends a notification THEN the adapter SHALL target exactly one subscription ID with `include_subscription_ids`. [PSH-02]
3. WHEN the adapter calls OneSignal THEN it SHALL send an `idempotency_key` that is the same for every call of one attempt. [PSH-03]
4. WHEN OneSignal responds 200 with a non-empty `id` THEN the adapter SHALL return an accepted outcome with that `id` as the provider reference. [PSH-04]
5. IF OneSignal responds 200 with an empty `id` THEN the adapter SHALL return a permanent failure with a normalized reason. [PSH-05]
6. IF OneSignal responds 400 THEN the adapter SHALL return a permanent failure. [PSH-06]
7. IF OneSignal responds 429 or a 5xx status THEN the adapter SHALL return a retryable failure. [PSH-07]
8. IF the request times out after being sent THEN the adapter SHALL return an unknown outcome. [PSH-08]
9. The worker SHALL never call a OneSignal app faster than its configured rate. [PSH-09]

**Independent Test**: Run adapter tests against a recorded stub for each response, including 200 with an empty `id`, then send one push to a test device.

---

### P1: Authenticate Event Stream deliveries ⭐ MVP

**User Story**: As a platform owner, I want Event Stream calls authenticated by their secret header so that outsiders cannot set push status (QS-07, FC-05).

**Why P1**: The endpoint is public.

**Acceptance Criteria**:
1. WHEN an Event Stream call arrives THEN the adapter SHALL compare its secret header to the configured value in constant time before parsing the body. [PSH-10]
2. IF the header is missing or wrong THEN the system SHALL respond 403 and count the rejection. [PSH-11]
3. WHEN a call repeats an already stored `event.id` THEN the system SHALL respond 2xx and store nothing new. [PSH-12]
4. The configured secret SHALL differ per provider account and SHALL never appear in logs. [PSH-13]
5. The OneSignal event authentication SHALL sit behind that provider's authenticator, so that changing the mechanism changes only that authenticator and its configuration. [PSH-24]
6. WHEN the header secret is rotated through configuration THEN the system SHALL accept the current and previous values until the previous value is removed, with no code change. [PSH-25]

**Independent Test**: Post calls with no header, a wrong header, a right header, and a repeated `event.id`. Rotate the secret through configuration. Swap in a test authenticator using another mechanism, and assert nothing outside the adapter changes.

---

### P1: Normalize push status ⭐ MVP

**User Story**: As an integration, I want push status when OneSignal reports it so that I can see delivery within the plan's limits.

**Why P1**: Push is the channel with the fewest events available, so each must count.

**Acceptance Criteria**:
1. WHEN a push received event arrives THEN the adapter SHALL produce status `DELIVERED` with the `message.id` reference. [PSH-14]
2. WHEN a push failed event arrives THEN the adapter SHALL produce status `NOT_DELIVERED` with a reason normalized from `failure_reason`. [PSH-15]
3. WHEN any other event kind arrives THEN the adapter SHALL produce no event, respond 200, and count it by kind. [PSH-16]
4. The provider-neutral event SHALL exclude subscription, external, and OneSignal user identifiers. [PSH-17]
5. WHILE no event arrives for a notification it SHALL stay `SENT` with no alert. [PSH-18]

**Independent Test**: Replay recorded Event Stream bodies and assert status and the scanned event body.

---

### P2: Free-plan limit visibility

**User Story**: As an operator, I want to see the plan limits approaching so that lost status or stopped sends do not surprise me.

**Why P2**: Limits do not block the first release, but crossing them changes behaviour.

**Acceptance Criteria**:
1. The system SHALL count Event Stream events received per calendar month per provider account. [PSH-19]
2. WHEN the monthly count reaches 80% of the configured event limit THEN the system SHALL raise an alert. [PSH-20]
3. WHEN OneSignal stops sending because the app reached its MAU limit THEN the resulting send failures SHALL be classified and counted under a distinct normalized reason. [PSH-21]

**Independent Test**: Feed counts across the threshold with a test clock, and stub the limit error.

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | PSH-06, PSH-22 |
| Failure / partial-failure states | PSH-05 to PSH-08 |
| Idempotency / retry / duplicates | PSH-03, PSH-12 |
| Auth boundaries & rate limits | PSH-09 to PSH-11, PSH-24, PSH-25 |
| Concurrency / ordering | Status rules from delivery-status absorb order; no extra requirement |
| Data lifecycle / expiry | PSH-17; OneSignal's own retention is covered by the D-62 assessment |
| Observability | PSH-11, PSH-16, PSH-19 to PSH-21 |
| External-dependency failure | PSH-07, PSH-08, PSH-18 |
| State-transition integrity | PSH-14, PSH-15, PSH-18 |

## Edge Cases

- IF a recipient is not a valid UUID at send time THEN the worker SHALL treat the request as unprocessable, although the API validates it first. [PSH-22]
- WHEN OneSignal auto-disables the stream after sustained failures THEN notifications SHALL stay `SENT`, and the per-provider measure of notifications with no report SHALL show the rise. [PSH-23]

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| PSH-01 | P1: Send push through OneSignal | Specify | Pending |
| PSH-02 | P1: Send push through OneSignal | Specify | Pending |
| PSH-03 | P1: Send push through OneSignal | Specify | Pending |
| PSH-04 | P1: Send push through OneSignal | Specify | Pending |
| PSH-05 | P1: Send push through OneSignal | Specify | Pending |
| PSH-06 | P1: Send push through OneSignal | Specify | Pending |
| PSH-07 | P1: Send push through OneSignal | Specify | Pending |
| PSH-08 | P1: Send push through OneSignal | Specify | Pending |
| PSH-09 | P1: Send push through OneSignal | Specify | Pending |
| PSH-10 | P1: Authenticate Event Stream deliveries | Specify | Pending |
| PSH-11 | P1: Authenticate Event Stream deliveries | Specify | Pending |
| PSH-12 | P1: Authenticate Event Stream deliveries | Specify | Pending |
| PSH-13 | P1: Authenticate Event Stream deliveries | Specify | Pending |
| PSH-14 | P1: Normalize push status | Specify | Pending |
| PSH-15 | P1: Normalize push status | Specify | Pending |
| PSH-16 | P1: Normalize push status | Specify | Pending |
| PSH-17 | P1: Normalize push status | Specify | Pending |
| PSH-18 | P1: Normalize push status | Specify | Pending |
| PSH-19 | P2: Free-plan limit visibility | Specify | Pending |
| PSH-20 | P2: Free-plan limit visibility | Specify | Pending |
| PSH-21 | P2: Free-plan limit visibility | Specify | Pending |
| PSH-22 | Edge cases | Specify | Pending |
| PSH-23 | Edge cases | Specify | Pending |
| PSH-24 | P1: Authenticate Event Stream deliveries | Specify | Pending |
| PSH-25 | P1: Authenticate Event Stream deliveries | Specify | Pending |

**Coverage:** 25 total, 0 mapped to tasks, 25 unmapped until the Tasks phase.

---

## Success Criteria

- [ ] FC-05 and FC-30 pass for OneSignal.
- [ ] One real push reaches `DELIVERED` on a test device.
- [ ] Non-adapter code changes are limited to the push worker's wiring.
