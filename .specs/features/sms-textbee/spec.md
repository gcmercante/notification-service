# SMS through textbee Specification

## Problem Statement

The platform must send SMS, and the owner selected hosted textbee.dev (AD-001). textbee sends through Android phones with their own SIMs, so it behaves unlike a carrier API: capacity is bound to phones and plan limits, and carriers do not always report delivery. This feature adds the SMS worker on the shared dispatch workflow, plus textbee's send and status paths.

## Goals

- [ ] An SMS is sent through textbee and reaches `SENT`.
- [ ] A signed `MESSAGE_DELIVERED` webhook moves it to `DELIVERED`.
- [ ] Only the textbee adapter, its configuration, and routing data change (QS-04).

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Inbound SMS (`MESSAGE_RECEIVED`) | The platform only sends notifications (D-14) |
| Self-hosted textbee | Owner chose hosted |
| Bulk send endpoint | Single notifications only (D-48) |
| Scheduled sends | Future scope (D-48) |
| Provisioning phones and SIMs | Operational task, outside the code |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Provider reference | `smsBatchId`, because each notification is a batch of one recipient | The send response returns `smsBatchId`, and every status webhook carries it | n |
| Status mapping | `MESSAGE_DELIVERED` to `DELIVERED`; `MESSAGE_FAILED` to `NOT_DELIVERED` with normalized `errorCode`; `MESSAGE_SENT` and `UNKNOWN_STATE` move no status and are counted | D-29: after provider acceptance a failure is `NOT_DELIVERED`. `SENT` already comes from the attempt outcome | n |
| Provider acceptance | A successful send response with a `smsBatchId` means accepted, so `SENT` | Vendor: "Use smsBatchId to follow delivery. Acceptance is not delivery" | n |
| Replay protection | Dedupe on `idempotencyKey` at the callbacks app, and rely on status rules for a repeated status | The signature covers the body only, with no timestamp. A repeated status gets a new key, which is why the status rules must absorb it | n |
| Device selection | The provider account reference holds one `deviceId` | The send path is per device; multiple-device balancing is not requested | n |
| Throttle value (OQ-11) | Configured per account, starting at 1 message per second | Vendor states no per-device rate; carrier rules still apply. Tune by observation | n |
| Plan limit reached (429) | Retryable under the normal policy, so `RETRIES_EXHAUSTED` once attempts are used | Vendor returns 429 for bursts and plan limits and they are not distinguishable in the pages read | n |
| Webhook subscription paused by textbee | Detect through alerting on missing events only; re-enable is manual | Vendor pauses repeatedly failing subscriptions and sends email | n |
| Idempotency | None available, so no key is sent | Vendor spec has no idempotency header; the duplicate window stays documented (QS-03) | n |
| International transfer (D-62) | Assessed before production; textbee storage region is not stated by the vendor | D-62 makes it a selection criterion and needs legal review | n |
| Timeout and unknown outcomes (OQ-16) | Same default as email-dispatch | Shared workflow | n |

**Open questions:** none - all resolved or logged above. OQ-11 stays partly open at provider level, as logged above.

---

## User Stories

### P1: Send SMS through textbee ⭐ MVP

**User Story**: As a tenant, I want SMS notifications sent through the platform's textbee account so that my users receive texts without me handling a provider (C-14).

**Why P1**: SMS is a confirmed channel.

**Acceptance Criteria**:
1. The SMS worker SHALL run the same dispatch workflow as the email worker and differ only in channel validation, adapters, and outcome mapping. [SMS-01]
2. WHEN the worker sends a notification THEN the adapter SHALL send one message to one recipient through the configured device, with the API key in the `x-api-key` header. [SMS-02]
3. WHEN textbee responds with success and a `smsBatchId` THEN the adapter SHALL return an accepted outcome with that value as the provider reference. [SMS-03]
4. IF textbee responds with 429 or a 5xx status THEN the adapter SHALL return a retryable failure. [SMS-04]
5. IF textbee responds with a 4xx status other than 429 THEN the adapter SHALL return a permanent failure. [SMS-05]
6. IF the request times out after being sent THEN the adapter SHALL return an unknown outcome. [SMS-06]
7. IF a success response has no `smsBatchId` THEN the adapter SHALL return an unknown outcome and count it. [SMS-07]
8. The worker SHALL never call the textbee account faster than its configured rate. [SMS-08]

**Independent Test**: Run adapter tests against a recorded HTTP stub for each response, then send one real SMS to a test phone.

---

### P1: Verify textbee webhooks ⭐ MVP

**User Story**: As a platform owner, I want only signed textbee webhooks accepted so that SMS status cannot be forged (QS-07, FC-05).

**Why P1**: The endpoint is public.

**Acceptance Criteria**:
1. WHEN a webhook arrives THEN the adapter SHALL compute HMAC-SHA256 of the raw body with the subscription's secret and compare it in constant time to `X-Signature`. [SMS-09]
2. IF the signature is missing or does not match THEN the system SHALL respond 403 and count the rejection. [SMS-10]
3. WHEN a webhook repeats an already stored `idempotencyKey` THEN the system SHALL respond 2xx and store nothing new. [SMS-11]
4. The adapter SHALL verify the signature before parsing the body. [SMS-12]

**Independent Test**: Post forged, replayed, and valid bodies signed with a test secret.

---

### P1: Normalize textbee status ⭐ MVP

**User Story**: As an integration, I want accurate SMS status so that I can tell delivered messages from failed ones.

**Why P1**: This is what makes SMS status useful.

**Acceptance Criteria**:
1. WHEN `MESSAGE_DELIVERED` arrives THEN the adapter SHALL produce status `DELIVERED` with the `smsBatchId` reference and `deliveredAt`. [SMS-13]
2. WHEN `MESSAGE_FAILED` arrives THEN the adapter SHALL produce status `NOT_DELIVERED` with a reason normalized from `errorCode` and `failedAt`. [SMS-14]
3. WHEN `MESSAGE_SENT`, `UNKNOWN_STATE`, or any other event type arrives THEN the adapter SHALL produce no event, respond 200, and count it by type. [SMS-15]
4. The provider-neutral event SHALL exclude `recipient`, `message`, and `errorMessage`. [SMS-16]
5. WHEN `MESSAGE_DELIVERED` arrives before `MESSAGE_SENT` or before the attempt outcome THEN the final status SHALL still be `DELIVERED`. [SMS-17]
6. WHILE the carrier sends no delivery report the notification SHALL stay `SENT` with no alert. [SMS-18]

**Independent Test**: Replay vendor example payloads in shuffled order and assert status and the scanned event body.

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | SMS-19 |
| Failure / partial-failure states | SMS-04 to SMS-07 |
| Idempotency / retry / duplicates | SMS-11; retries by the shared workflow |
| Auth boundaries & rate limits | SMS-08 to SMS-10 |
| Concurrency / ordering | SMS-17 |
| Data lifecycle / expiry | SMS-16; hosted message retention at textbee is covered by the D-62 assessment |
| Observability | SMS-10, SMS-15, SMS-20 |
| External-dependency failure | SMS-04, SMS-06, SMS-20 |
| State-transition integrity | SMS-14, SMS-17, SMS-18 |

## Edge Cases

- IF a recipient is not a valid E.164 number at send time THEN the worker SHALL treat the request as unprocessable, although the API validates it first. [SMS-19]
- WHEN the share of notifications at `SENT` with no report rises for textbee THEN the per-provider measure SHALL show it, so that a paused subscription or offline phone is visible. [SMS-20]

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| SMS-01 | P1: Send SMS through textbee | Specify | Pending |
| SMS-02 | P1: Send SMS through textbee | Specify | Pending |
| SMS-03 | P1: Send SMS through textbee | Specify | Pending |
| SMS-04 | P1: Send SMS through textbee | Specify | Pending |
| SMS-05 | P1: Send SMS through textbee | Specify | Pending |
| SMS-06 | P1: Send SMS through textbee | Specify | Pending |
| SMS-07 | P1: Send SMS through textbee | Specify | Pending |
| SMS-08 | P1: Send SMS through textbee | Specify | Pending |
| SMS-09 | P1: Verify textbee webhooks | Specify | Pending |
| SMS-10 | P1: Verify textbee webhooks | Specify | Pending |
| SMS-11 | P1: Verify textbee webhooks | Specify | Pending |
| SMS-12 | P1: Verify textbee webhooks | Specify | Pending |
| SMS-13 | P1: Normalize textbee status | Specify | Pending |
| SMS-14 | P1: Normalize textbee status | Specify | Pending |
| SMS-15 | P1: Normalize textbee status | Specify | Pending |
| SMS-16 | P1: Normalize textbee status | Specify | Pending |
| SMS-17 | P1: Normalize textbee status | Specify | Pending |
| SMS-18 | P1: Normalize textbee status | Specify | Pending |
| SMS-19 | Edge cases | Specify | Pending |
| SMS-20 | Edge cases | Specify | Pending |

**Coverage:** 20 total, 0 mapped to tasks, 20 unmapped until the Tasks phase.

---

## Success Criteria

- [ ] FC-05 and FC-30 pass for textbee.
- [ ] One real SMS reaches `DELIVERED` on a test phone.
- [ ] Non-adapter code changes are limited to the SMS worker's wiring.
