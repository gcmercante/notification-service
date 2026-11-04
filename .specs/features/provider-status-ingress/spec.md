# Provider Status Ingress Specification

## Problem Statement

After a provider accepts a send, only the provider knows what happened next. Those reports arrive on public endpoints, can be forged or replayed (QS-07), and can arrive before the attempt outcome that makes them matchable (D-68). This feature builds the callbacks application and its first provider path, SES through SNS, and adds correlation and parking to the Delivery-status app.

## Goals

- [ ] An unauthenticated report never changes status (FC-05).
- [ ] A Kafka outage does not lose provider reports (FC-17).
- [ ] Status and history are the same whichever of report and outcome arrives first (FC-32).

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Polling providers | Deferred (D-23, D-24, FC-07) |
| Provider-queue consumers | No selected provider needs one |
| textbee and OneSignal handlers | Features 8 and 9 |
| Resending after a reported failure | Reported failures are final (D-11) |
| Retaining raw callback payloads | Not retained (§6.4, Proposed) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| OQ-57: hold period for unmatched events | 15 minutes, configurable; longer than the D-40 alert so stuck-work alerts come first | Retry window is about 7 s plus attempts; a shorter hold adds alert noise | n |
| OQ-57: after the hold period | Alert once, keep the event for a late match, purge at 30 days | Keeps valid facts for late outcomes, and 30 days matches D-38 | n |
| OQ-58: correlation key scope | Provider, provider account, and provider reference together | Safe under either answer to uniqueness | n |
| SES status mapping | `Delivery` to `DELIVERED`, `Bounce` to `BOUNCED`, `Reject` to `NOT_DELIVERED`; all other event types ignored and counted | D-26 and D-29 vocabulary; `Send`, `Open`, `Click`, `Complaint` and `DeliveryDelay` carry no status in it | n |
| SNS subscription confirmation | The endpoint confirms only for an expected topic, after signature verification | Needed to receive messages; this is not status polling | n |
| SNS signature version | Accept `SignatureVersion` 2 only | AWS recommends SHA256; the platform controls the subscription | n |
| Replay protection for SNS | SNS `Timestamp` within 1 hour, plus dedupe on SNS message ID | HLD §8.3 asks for timestamps and/or event IDs | n |
| Reason for a stored event | Normalized provider reason only, with no recipient | §6.4 says adapters drop recipient data | n |

**Open questions:** none - all resolved or logged above. OQ-14 is answered for SES by SNS signatures.

---

## User Stories

### P1: Receive and verify SES status ⭐ MVP

**User Story**: As a platform owner, I want only genuine SES reports accepted so that status cannot be forged (QS-07).

**Why P1**: The endpoint is public by necessity.

**Acceptance Criteria**:
1. WHEN an SNS message arrives THEN the adapter SHALL verify its signature against a certificate fetched over HTTPS from an Amazon SNS host before parsing the SES payload. [ING-01]
2. IF the signature is invalid or the certificate host is not an Amazon SNS host THEN the system SHALL respond 403 and count the rejection. [ING-02]
3. IF the `TopicArn` is not the one configured for that provider account THEN the system SHALL respond 403 and count the rejection. [ING-03]
4. IF the SNS `Timestamp` is more than 1 hour old THEN the system SHALL respond 403 and count it as a replay. [ING-04]
5. WHEN a verified subscription confirmation arrives for an expected topic THEN the system SHALL confirm the subscription. [ING-05]
6. The system SHALL apply a request rate limit and a body size limit to the public endpoint before verification. [ING-06]
7. The callbacks application SHALL authenticate each provider through that provider's own authenticator and SHALL hold no mechanism-specific logic outside provider adapters. [ING-30]

**Independent Test**: Send forged, replayed, wrong-topic, and valid messages signed by a test certificate chain.

---

### P1: Normalize without personal data ⭐ MVP

**User Story**: As a data protection owner, I want provider events to carry only identifiers and statuses so that recipients never enter the status path (§6.4).

**Why P1**: SES payloads contain recipient addresses.

**Acceptance Criteria**:
1. WHEN a verified SES `Delivery` event arrives THEN the adapter SHALL produce a provider-neutral event with status `DELIVERED`, the `mail.messageId` reference, and the provider timestamp. [ING-07]
2. WHEN a verified SES `Bounce` event arrives THEN the adapter SHALL produce status `BOUNCED` with a normalized reason. [ING-08]
3. WHEN a verified SES `Reject` event arrives THEN the adapter SHALL produce status `NOT_DELIVERED` with a normalized reason. [ING-09]
4. WHEN any other SES event type arrives THEN the adapter SHALL produce no event, respond 200, and count it. [ING-10]
5. The provider-neutral event SHALL contain no recipient and no content. [ING-11]
6. The system SHALL not retain the raw provider payload after processing. [ING-12]

**Independent Test**: Feed recorded SES payloads with seeded addresses and scan the output.

---

### P1: Durable ingestion ⭐ MVP

**User Story**: As a platform owner, I want reports stored before they are acknowledged so that a Kafka outage loses nothing (D-37, FC-17).

**Why P1**: A provider may not resend what it thinks was delivered.

**Acceptance Criteria**:
1. WHEN an event is verified and normalized THEN the system SHALL commit it with an outbox entry and respond 2xx after the commit. [ING-13]
2. IF the commit fails THEN the system SHALL respond 503 so that the provider retries. [ING-14]
3. WHILE Kafka is unavailable the system SHALL keep accepting reports and SHALL publish them when Kafka returns. [ING-15]
4. The callbacks application SHALL write no status and SHALL make no synchronous call to another application. [ING-16]
5. The callbacks application SHALL contain no code path that calls a provider's status API. [ING-17]

**Independent Test**: Stop Kafka, post verified reports, restart Kafka, and assert publication (FC-17).

---

### P1: Correlate and park ⭐ MVP

**User Story**: As an integration, I want the correct final status even when a report beats the attempt outcome so that races do not lose facts (D-68, FC-32).

**Why P1**: Topics have no order between them.

**Acceptance Criteria**:
1. WHEN an accepted attempt outcome arrives with a provider reference THEN the Delivery-status app SHALL store the correlation under provider, account, and reference. [ING-18]
2. WHEN a provider event matches a known correlation THEN the Delivery-status app SHALL apply it through the normal transition rules. [ING-19]
3. WHEN a provider event matches no correlation THEN the Delivery-status app SHALL park it durably and only then acknowledge it. [ING-20]
4. WHEN an attempt outcome establishes a correlation with parked events THEN the Delivery-status app SHALL apply each parked event once through the normal rules. [ING-21]
5. WHEN a report and an outcome arrive in either order, including across a restart THEN the resulting status and history SHALL be identical. [ING-22]
6. IF a parked event remains unmatched past the hold period THEN the Delivery-status app SHALL raise one alert and change no status. [ING-23]
7. WHEN a late correlation matches an event already alerted on THEN the Delivery-status app SHALL still apply it through the normal rules. [ING-24]
8. The parked event store SHALL hold no content or recipient. [ING-25]

**Independent Test**: Publish the event before the outcome with a restart between them, then the reverse, and compare results (FC-32).

---

### P1: Reported failures stay final ⭐ MVP

**User Story**: As a platform owner, I want provider-reported failures recorded and never retried so that status stays a recorder of facts (D-11).

**Why P1**: A feedback loop would break the choreography (D-57).

**Acceptance Criteria**:
1. WHEN a provider event reports `BOUNCED` or `NOT_DELIVERED` THEN the system SHALL make no new provider attempt. [ING-26]

**Independent Test**: Report a bounce and assert no dispatch message and no attempt.

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | ING-01 to ING-04, ING-06 |
| Failure / partial-failure states | ING-14, ING-15 |
| Idempotency / retry / duplicates | ING-21, ING-27 |
| Auth boundaries & rate limits | ING-01 to ING-03, ING-06, ING-30 |
| Concurrency / ordering | ING-22 |
| Data lifecycle / expiry | ING-12, ING-28 |
| Observability | ING-02, ING-10, ING-29 |
| External-dependency failure | ING-15 |
| State-transition integrity | ING-19, ING-26 |

## Edge Cases

- WHEN SNS redelivers a message with an already stored SNS message ID THEN the system SHALL respond 2xx and store nothing new. [ING-27]
- WHEN a parked event reaches 30 days THEN the system SHALL purge it. [ING-28]
- The system SHALL expose counts of rejected reports by reason, unmatched events, and parked-event age. [ING-29]

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| ING-01 | P1: Receive and verify SES status | Specify | Pending |
| ING-02 | P1: Receive and verify SES status | Specify | Pending |
| ING-03 | P1: Receive and verify SES status | Specify | Pending |
| ING-04 | P1: Receive and verify SES status | Specify | Pending |
| ING-05 | P1: Receive and verify SES status | Specify | Pending |
| ING-06 | P1: Receive and verify SES status | Specify | Pending |
| ING-07 | P1: Normalize without personal data | Specify | Pending |
| ING-08 | P1: Normalize without personal data | Specify | Pending |
| ING-09 | P1: Normalize without personal data | Specify | Pending |
| ING-10 | P1: Normalize without personal data | Specify | Pending |
| ING-11 | P1: Normalize without personal data | Specify | Pending |
| ING-12 | P1: Normalize without personal data | Specify | Pending |
| ING-13 | P1: Durable ingestion | Specify | Pending |
| ING-14 | P1: Durable ingestion | Specify | Pending |
| ING-15 | P1: Durable ingestion | Specify | Pending |
| ING-16 | P1: Durable ingestion | Specify | Pending |
| ING-17 | P1: Durable ingestion | Specify | Pending |
| ING-18 | P1: Correlate and park | Specify | Pending |
| ING-19 | P1: Correlate and park | Specify | Pending |
| ING-20 | P1: Correlate and park | Specify | Pending |
| ING-21 | P1: Correlate and park | Specify | Pending |
| ING-22 | P1: Correlate and park | Specify | Pending |
| ING-23 | P1: Correlate and park | Specify | Pending |
| ING-24 | P1: Correlate and park | Specify | Pending |
| ING-25 | P1: Correlate and park | Specify | Pending |
| ING-26 | P1: Reported failures stay final | Specify | Pending |
| ING-27 | Edge cases | Specify | Pending |
| ING-28 | Edge cases | Specify | Pending |
| ING-29 | Edge cases | Specify | Pending |
| ING-30 | P1: Receive and verify SES status | Specify | Pending |

**Coverage:** 30 total, 0 mapped to tasks, 30 unmapped until the Tasks phase.

---

## Success Criteria

- [ ] FC-05 (SES), FC-07, FC-17, FC-32 and FC-33 pass.
- [ ] Email reaches `DELIVERED` end to end through the SES sandbox.
- [ ] Callback-before-outcome sequence diagram exists (HLD §13 item 3).
