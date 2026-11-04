# Notification Submission Specification

## Problem Statement

Integrations need to hand over one notification and know it will not be lost or duplicated by their own retries. Success must mean the request survives a crash (QS-01), with content and recipients encrypted from the moment of acceptance (D-63). This is the platform's main external entry point.

## Goals

- [ ] Zero accepted-but-lost notifications in fault injection (FC-04).
- [ ] A retried submission returns the original notification (FC-13).
- [ ] No plain content or recipient in the request store, outbox, or topics (FC-15).

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Templates, scheduling, preferences, bulk sends | Future scope (D-48) |
| Provider selection for the send | The worker decides; the API only pre-checks (D-55) |
| Writing delivery status | Single writer is feature 5 (C-07) |
| Outbound status webhooks to integrations | Non-goal (D-21) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| OQ-51: does the API pre-check routing | Yes, the full resolution rule runs at submission (P-02a) | FC-19 tests this reading | n |
| Content fields | Email: subject and text or HTML body. SMS: text. Push: title and body | D-48 excludes templates, so callers supply content; these match the three selected providers | n |
| Recipient format | Email address; E.164 phone number; OneSignal subscription ID (UUID) | Provider targeting facts in the channel features; final in the OpenAPI contract | n |
| Size limits | Email 256 KB, SMS 1,600 characters, push 4 KB, all configurable | HLD requires limits but sets no values | n |
| Key handling until OQ-53 is answered | Envelope encryption with the key-encryption key delivered as an environment secret | D-59 allows delivery as environment variables; no store product is chosen | n |
| Blind index (OQ-56, Proposed) | Keyed hash of the normalized recipient stored beside the ciphertext | FC-15 requires deletion by recipient to work through it | n |
| Accepted fact path (§5.1 open) | A status-facts stream, separate from channel topics | The HLD's recommendation; the status app need not subscribe to channel topics | n |
| Idempotency key format | Caller-supplied string, 1 to 255 characters | Bound needed; final in the contract | n |
| HTTP status codes | 202 accepted, 200 idempotent replay, 400 missing key, 409 key conflict, 422 validation or no eligible provider | Standard meanings; final in the OpenAPI contract | n |
| Canonical body hash | SHA-256 over a canonical serialization of the request body | D-58 and §6.4 require comparing a hash, not plain content | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Submit one notification ⭐ MVP

**User Story**: As an integration, I want to submit one notification and receive its ID so that I can track it later.

**Why P1**: It is the platform's purpose.

**Acceptance Criteria**:
1. WHEN an authenticated integration with the `submit` scope sends a valid notification THEN the system SHALL respond 202 with a notification ID after the database commit. [SUB-01]
2. IF the channel is not email, SMS, or push THEN the system SHALL respond 422. [SUB-02]
3. IF the recipient format is invalid for the channel THEN the system SHALL respond 422 naming the field and not echoing its value. [SUB-03]
4. IF the content exceeds the channel's size limit or is missing a required field THEN the system SHALL respond 422. [SUB-04]
5. IF the policy finds no eligible provider for the tenant and channel THEN the system SHALL respond 422 with a non-retryable error code and store nothing. [SUB-05]
6. The system SHALL store the tenant and integration IDs from the authenticated context and from no other source. [SUB-06]
7. The system SHALL not change an accepted request after acceptance. [SUB-07]

**Independent Test**: Submit valid and invalid requests per channel, and inspect responses and stored rows.

---

### P1: Idempotent submission ⭐ MVP

**User Story**: As an integration, I want to retry safely so that a network failure cannot create a second notification (D-35).

**Why P1**: Every submission must carry a key.

**Acceptance Criteria**:
1. IF a submission has no idempotency key THEN the system SHALL respond 400. [SUB-08]
2. WHEN an integration repeats a key with the same body within 24 hours THEN the system SHALL respond 200 with the original notification ID and create nothing. [SUB-09]
3. IF an integration repeats a key with a different body within 24 hours THEN the system SHALL respond 409. [SUB-10]
4. WHEN two integrations use the same key THEN the system SHALL treat them as separate submissions. [SUB-11]
5. WHEN a key is older than 24 hours THEN the system SHALL treat its reuse as a new submission. [SUB-12]
6. WHEN concurrent requests use the same key THEN the system SHALL create exactly one notification. [SUB-13]

**Independent Test**: Replay a key with the same and a different body, from one and from two integrations, and race two requests.

---

### P1: Encrypt at acceptance ⭐ MVP

**User Story**: As a data protection owner, I want content and recipients encrypted before storage so that stores and topics never hold them in plain form (D-63).

**Why P1**: Plain data must never reach the store, even once.

**Acceptance Criteria**:
1. WHEN a notification is accepted THEN the system SHALL encrypt content and recipient before any write using an envelope scheme. [SUB-14]
2. The system SHALL store a keyed blind index of the normalized recipient beside the encrypted value. [SUB-15]
3. The system SHALL compute idempotency conflict checks from a body hash and SHALL not store the plain body for them. [SUB-16]
4. WHEN the store, outbox, and topic contents are scanned after submission THEN no seeded content or recipient SHALL appear in plain form. [SUB-17]

**Independent Test**: Submit seeded values and run the scanner over the database and consumed messages.

---

### P1: Durable hand-off ⭐ MVP

**User Story**: As an integration, I want acceptance to survive crashes and broker outages so that success always means the work will happen (D-27).

**Why P1**: QS-01 is the top reliability scenario.

**Acceptance Criteria**:
1. WHEN a notification is accepted THEN the system SHALL commit the request and its outbox entries in one transaction. [SUB-18]
2. WHEN the relay runs THEN it SHALL publish a dispatch request on the channel's topic and an accepted fact on the status-facts stream. [SUB-19]
3. WHILE the broker is unavailable and PostgreSQL is available the system SHALL keep accepting submissions. [SUB-20]
4. IF PostgreSQL is unavailable THEN the system SHALL respond 503 and accept nothing. [SUB-21]
5. The accepted fact SHALL carry only identifiers, channel, and timestamps, with no content or recipient. [SUB-22]
6. The system SHALL place no API key on any message. [SUB-23]

**Independent Test**: Kill the API, relay, or broker during submissions, then assert each 202 has both messages eventually (FC-04).

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | SUB-02 to SUB-04, SUB-08 |
| Failure / partial-failure states | SUB-18, SUB-20, SUB-21 |
| Idempotency / retry / duplicates | SUB-09 to SUB-13 |
| Auth boundaries & rate limits | SUB-06; authentication and limits from integration-access apply to this endpoint |
| Concurrency / ordering | SUB-13; no ordering across notifications (D-49) |
| Data lifecycle / expiry | SUB-12; content purge in dlq-and-data-lifecycle |
| Observability | SUB-24 |
| External-dependency failure | SUB-20, SUB-21 |
| State-transition integrity | SUB-07 |

## Edge Cases

- WHEN a submission is accepted or rejected THEN the system SHALL count it by channel and rejection reason with no recipient or content label. [SUB-24]
- IF the encryption key material is unavailable THEN the system SHALL respond 503 and store nothing. [SUB-25]

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| SUB-01 | P1: Submit one notification | Specify | Pending |
| SUB-02 | P1: Submit one notification | Specify | Pending |
| SUB-03 | P1: Submit one notification | Specify | Pending |
| SUB-04 | P1: Submit one notification | Specify | Pending |
| SUB-05 | P1: Submit one notification | Specify | Pending |
| SUB-06 | P1: Submit one notification | Specify | Pending |
| SUB-07 | P1: Submit one notification | Specify | Pending |
| SUB-08 | P1: Idempotent submission | Specify | Pending |
| SUB-09 | P1: Idempotent submission | Specify | Pending |
| SUB-10 | P1: Idempotent submission | Specify | Pending |
| SUB-11 | P1: Idempotent submission | Specify | Pending |
| SUB-12 | P1: Idempotent submission | Specify | Pending |
| SUB-13 | P1: Idempotent submission | Specify | Pending |
| SUB-14 | P1: Encrypt at acceptance | Specify | Pending |
| SUB-15 | P1: Encrypt at acceptance | Specify | Pending |
| SUB-16 | P1: Encrypt at acceptance | Specify | Pending |
| SUB-17 | P1: Encrypt at acceptance | Specify | Pending |
| SUB-18 | P1: Durable hand-off | Specify | Pending |
| SUB-19 | P1: Durable hand-off | Specify | Pending |
| SUB-20 | P1: Durable hand-off | Specify | Pending |
| SUB-21 | P1: Durable hand-off | Specify | Pending |
| SUB-22 | P1: Durable hand-off | Specify | Pending |
| SUB-23 | P1: Durable hand-off | Specify | Pending |
| SUB-24 | Edge cases | Specify | Pending |
| SUB-25 | Edge cases | Specify | Pending |

**Coverage:** 25 total, 0 mapped to tasks, 25 unmapped until the Tasks phase.

---

## Success Criteria

- [ ] FC-04 and FC-13 pass; FC-15 and FC-19 pass for the submission path.
- [ ] OpenAPI contract for the integration API exists under `docs/architecture/notification-service/`.
