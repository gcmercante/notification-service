# DLQ and Data Lifecycle Specification

## Problem Statement

Dead-lettered messages must be replayable by an administrator, or they stay `FAILED` forever (D-39, D-41). Personal data must also leave the platform on schedule and on request (D-38, D-62). Both are confirmed obligations, and both span several applications' stores.

## Goals

- [ ] An administrator replay keeps the notification ID and reopens `FAILED` (FC-28).
- [ ] No content or recipient older than 30 days remains in any store (FC-18).
- [ ] A recipient's data can be deleted per tenant through the blind index (FC-15).

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Automatic DLQ replay | Replay is manual (D-39) |
| Maximum notification age | None for now (D-39) |
| Legal or DPO review | Needed before production (D-62), and not a code task |
| Deleting data held by providers | Covered by provider terms and the D-62 assessment |
| Automated incident response | D-62 requires a path, which is a process document |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Delete or anonymize at 30 days | Delete content and recipient columns, keep the row's identifiers | D-38 allows either; idempotency and audit references stay intact | n |
| Purge schedule | Daily, configurable | D-38 sets the period, not the schedule | n |
| Topic and DLQ retention | Configured at 30 days or less, checked at start-up by an administrative check | FC-18 checks configuration | n |
| Worker ledger retention | 30 days, purged by the same job | §6.1 calls it operational, and it may hold encrypted data | n |
| DLQ growth threshold | Any new entry raises an alert until a threshold is set | D-39 requires an alert with no number; D-34 defers numbers | n |
| Replay of a notification whose content has expired | Refused with 422 and left in the DLQ until its retention ends | The worker could not send without content | n |
| Deletion across topics | Topics expire by retention; only stores and the DLQ are changed | HLD §6.4 says topics expire by retention | n |
| Deleted recipient with work in flight | A send already queued may still complete; the deletion response reports how many matches are still `PROCESSING` | Dispatch messages carry their own encrypted copy and topics expire by retention (§6.4), so workers cannot detect the deletion | n |
| Attempt budget on replay | A replay starts a new budget of 4 attempts | A dead-lettered message made no provider attempt, and D-39 and D-41 set no budget | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Replay dead letters ⭐ MVP

**User Story**: As an administrator, I want to replay a dead-lettered message so that a fixed problem does not leave notifications failed (D-39, D-41).

**Why P1**: The DLQ has no exit otherwise.

**Acceptance Criteria**:
1. WHEN an administrator lists a channel's DLQ THEN the system SHALL return notification IDs, tenant IDs, reasons, and timestamps, with no content or recipient. [OPS-01]
2. WHEN an administrator replays a dead-lettered message THEN the system SHALL republish it with its original notification ID. [OPS-02]
3. WHEN a replay runs THEN the status SHALL move from `FAILED` to `PROCESSING` with the administrator's identity in history. [OPS-03]
4. IF the notification's status is not `FAILED` THEN the system SHALL respond 409 and republish nothing. [OPS-04]
5. IF an integration key calls a DLQ endpoint THEN the system SHALL respond 401. [OPS-05]
6. WHEN a new message enters a DLQ THEN the system SHALL raise a DLQ growth alert. [OPS-06]
7. WHEN a replayed message is processed THEN the worker SHALL treat it as a fresh attempt budget under the retry policy. [OPS-07]

**Independent Test**: Force a poison message, fix its cause, replay it, and assert the same ID, the reopened status, and a final status.

---

### P1: Scheduled retention ⭐ MVP

**User Story**: As a data protection owner, I want data removed on schedule so that the platform keeps personal data no longer than D-38 allows.

**Why P1**: It is a confirmed obligation with a fitness check.

**Acceptance Criteria**:
1. WHEN content and recipient data are older than 30 days THEN the purge SHALL remove them from the request store, worker stores, and DLQ. [OPS-08]
2. WHEN status history is older than 1 year THEN the purge SHALL delete it. [OPS-09]
3. WHEN an idempotency record is older than 24 hours THEN the purge SHALL delete it. [OPS-10]
4. IF a topic or DLQ retention is configured above 30 days THEN the retention check SHALL fail and name it. [OPS-11]
5. WHEN the retention check runs THEN it SHALL fail on any content or recipient older than 30 days in a store. [OPS-12]
6. IF a purge run fails THEN the next run SHALL remove what remains, and the failure SHALL raise an alert. [OPS-13]

**Independent Test**: Seed records either side of each boundary with a test clock, run the purge, and assert what remains.

---

### P1: Delete a recipient per tenant ⭐ MVP

**User Story**: As an administrator acting for a tenant, I want to delete a recipient's data so that a data subject's request can be met before 30 days (D-62).

**Why P1**: D-62 confirms this capability.

**Acceptance Criteria**:
1. WHEN an administrator requests deletion for a tenant and recipient THEN the system SHALL find matches through the blind index and remove their content and recipient from the request store and DLQ. [OPS-14]
2. The deletion SHALL affect only the named tenant's records. [OPS-15]
3. WHEN a deletion runs THEN the system SHALL write an audit entry holding the actor, tenant, time, and match count, with no recipient value. [OPS-16]
4. WHEN a notification's content is deleted THEN its status and history SHALL remain. [OPS-17]
5. WHEN a deletion completes THEN the response SHALL state how many matched notifications are still `PROCESSING` and may still be sent. [OPS-18]

**Independent Test**: Seed one recipient in two tenants, delete for one, and scan both.

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | OPS-04, OPS-19 |
| Failure / partial-failure states | OPS-13, OPS-20 |
| Idempotency / retry / duplicates | OPS-02, OPS-20 |
| Auth boundaries & rate limits | OPS-05, OPS-15 |
| Concurrency / ordering | OPS-21 |
| Data lifecycle / expiry | OPS-08 to OPS-12, OPS-14 |
| Observability | OPS-06, OPS-13, OPS-16 |
| External-dependency failure | OPS-20 |
| State-transition integrity | OPS-03, OPS-04 |

## Edge Cases

- IF a replay targets a notification whose content has expired THEN the system SHALL respond 422 and leave the message in the DLQ. [OPS-19]
- IF a replay fails to publish THEN the message SHALL stay in the DLQ and the status SHALL not change. [OPS-20]
- WHEN two administrators replay the same message at once THEN the system SHALL republish it exactly once. [OPS-21]

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| OPS-01 | P1: Replay dead letters | Specify | Pending |
| OPS-02 | P1: Replay dead letters | Specify | Pending |
| OPS-03 | P1: Replay dead letters | Specify | Pending |
| OPS-04 | P1: Replay dead letters | Specify | Pending |
| OPS-05 | P1: Replay dead letters | Specify | Pending |
| OPS-06 | P1: Replay dead letters | Specify | Pending |
| OPS-07 | P1: Replay dead letters | Specify | Pending |
| OPS-08 | P1: Scheduled retention | Specify | Pending |
| OPS-09 | P1: Scheduled retention | Specify | Pending |
| OPS-10 | P1: Scheduled retention | Specify | Pending |
| OPS-11 | P1: Scheduled retention | Specify | Pending |
| OPS-12 | P1: Scheduled retention | Specify | Pending |
| OPS-13 | P1: Scheduled retention | Specify | Pending |
| OPS-14 | P1: Delete a recipient per tenant | Specify | Pending |
| OPS-15 | P1: Delete a recipient per tenant | Specify | Pending |
| OPS-16 | P1: Delete a recipient per tenant | Specify | Pending |
| OPS-17 | P1: Delete a recipient per tenant | Specify | Pending |
| OPS-18 | P1: Delete a recipient per tenant | Specify | Pending |
| OPS-19 | Edge cases | Specify | Pending |
| OPS-20 | Edge cases | Specify | Pending |
| OPS-21 | Edge cases | Specify | Pending |

**Coverage:** 21 total, 0 mapped to tasks, 21 unmapped until the Tasks phase.

---

## Success Criteria

- [ ] FC-18 and FC-28 pass; FC-15 passes for deletion.
- [ ] The DLQ-replay sequence diagram exists (HLD §13 item 3).
