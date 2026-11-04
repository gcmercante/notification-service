# Delivery Status Specification

## Problem Statement

Integrations need a trustworthy status for what they submitted, and facts about a notification arrive duplicated and out of order (C-08). The platform allows exactly one writer and one source of truth (C-07, D-33). Without this feature, nothing stops status from moving backward or leaking across integrations.

## Goals

- [ ] Shuffled, duplicated fact sequences always end in the same status and history (FC-02).
- [ ] Another integration's notification is indistinguishable from an unknown one (FC-11).
- [ ] A notification stuck in `PROCESSING` over 5 minutes raises an alert (FC-09).

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Provider events, correlation, parking | Feature 7 feeds them in through these same rules |
| DLQ replay transition's trigger | Feature 10; the rule that allows it is here |
| Push of status to integrations | Non-goal (D-21) |
| Marking stuck work with a new status | OQ-54 is open; alert only |
| Numeric latency targets | Deferred (D-34); measures are collected |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Wire form of statuses | `PROCESSING`, `SENT`, `DELIVERED`, `BOUNCED`, `NOT_DELIVERED`, `FAILED` | HLD §6.3 leaves the written form to contracts | n |
| Administrator status queries (§5.6, Proposed) | Administrative surface reaches the same query without the integration filter | Needed for support; HLD proposal | n |
| Internal query transport | HTTP on an internal listener, guarded by the service key | D-53 and D-56 describe an internal HTTP interface | n |
| Status fields shown to integrations | ID, channel, status, reason, attempt number, timestamps | OQ-23 leaves provider identity undecided, so it is not exposed | n |
| Stuck-work check interval | Every 60 seconds, configurable | D-40 fixes the threshold, not the interval | n |
| OQ-16 interaction | An unknown attempt outcome moves no status, so the D-40 alert covers it | Status vocabulary has no value for it (OQ-54); see the email-dispatch spec | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Single writer with forward-only rules ⭐ MVP

**User Story**: As a platform owner, I want every fact applied through one rule set so that status is deterministic whatever the arrival order (D-30, D-60).

**Why P1**: It is the platform's central invariant.

**Acceptance Criteria**:
1. WHEN an accepted fact arrives for an unknown notification THEN the system SHALL create its status as `PROCESSING` with tenant and integration IDs. [STA-01]
2. WHEN a fact has a rank higher than the current status THEN the system SHALL move status to that fact's status and append history. [STA-02]
3. IF a fact has a rank equal to or lower than the current status THEN the system SHALL append it to history and leave status unchanged. [STA-03]
4. WHILE status is final the system SHALL keep the first final status when a conflicting final fact arrives. [STA-04]
5. WHEN a fact repeats an already applied event identity THEN the system SHALL change neither status nor history. [STA-05]
6. WHEN attempt outcomes report a pending retry THEN the system SHALL keep `PROCESSING` and update the attempt number attribute. [STA-06]
7. IF a `FAILED` fact has no reason THEN the system SHALL treat it as unprocessable and leave status unchanged. [STA-07]
8. The system SHALL accept `NOT_DELIVERED` only from a provider event and never from an attempt outcome. [STA-08]
9. WHEN `FAILED` is reopened by a replay fact carrying an administrator's identity THEN the system SHALL move status to `PROCESSING` and record that identity in history. [STA-09]
10. IF a status other than `FAILED` receives a replay fact THEN the system SHALL leave status unchanged. [STA-10]
11. WHEN a fact arrives for a notification with no accepted fact yet THEN the system SHALL create the status record from the fact's identifiers and apply the rules, and a later accepted fact SHALL not lower it. [STA-11]
12. WHEN two consumers apply facts to one notification at once THEN the system SHALL serialize them through a conditional atomic update. [STA-12]

**Independent Test**: Property test: generate fact sets, shuffle and duplicate them, and assert identical final status and the same set of history entries (FC-02).

---

### P1: Read own notification status ⭐ MVP

**User Story**: As an integration, I want to read the status of my notification so that I know what happened (D-16, D-21).

**Why P1**: It is the only way integrations learn outcomes.

**Acceptance Criteria**:
1. WHEN an integration with `read-status` requests its own notification THEN the API SHALL return its current status through the internal query interface. [STA-13]
2. IF the notification belongs to another integration or tenant THEN the API SHALL respond 404 with a body identical to the unknown-ID response. [STA-14]
3. WHEN a notification was accepted but its accepted fact is not yet applied THEN the API SHALL respond 404. [STA-15]
4. IF the internal query interface is called without the API's service key THEN it SHALL respond 401. [STA-16]
5. The status query SHALL touch only the status store and SHALL call no worker or provider. [STA-17]
6. IF the Delivery-status app is unavailable THEN the API SHALL respond 503. [STA-18]

**Independent Test**: Read one notification as its owner, as a sibling integration, and as another tenant, and compare response bodies byte for byte.

---

### P1: Stuck-work alert ⭐ MVP

**User Story**: As an operator, I want an alert for notifications stuck in `PROCESSING` so that silent failures in a choreographed pipeline become visible (D-40, D-67).

**Why P1**: No orchestrator holds the overall picture (D-57).

**Acceptance Criteria**:
1. WHEN a notification stays in `PROCESSING` for more than 5 minutes THEN the system SHALL raise an alert containing its notification, tenant, and integration IDs. [STA-19]
2. WHILE a notification is at `SENT` with no further provider report the system SHALL raise no alert. [STA-20]
3. The system SHALL raise one alert per stuck notification per stuck period, not one per check. [STA-21]

**Independent Test**: Hold a synthetic notification with a test clock across 5 minutes, and repeat for one at `SENT`.

---

### P1: No personal data in status ⭐ MVP

**User Story**: As a data protection owner, I want status history free of personal data so that its 1-year retention does not extend personal data's life (D-62).

**Why P1**: The design of the store depends on it.

**Acceptance Criteria**:
1. The status store SHALL hold only identifiers, statuses, reasons, and timestamps, with no content or recipient. [STA-22]
2. IF a consumed fact contains a recipient or content field THEN the system SHALL reject the fact as a contract violation and count it. [STA-23]

**Independent Test**: Scan the status database after a seeded run.

---

### P2: Freshness measures

**User Story**: As an operator, I want freshness measured from day one so that targets can be set once load is known (D-19, D-34, FC-12).

**Why P2**: Status works without it, but D-34 requires collection.

**Acceptance Criteria**:
1. WHEN a fact is applied THEN the system SHALL record the time from the fact's occurrence to its application. [STA-24]
2. The system SHALL expose consumer lag per topic. [STA-25]

**Independent Test**: Apply facts with known timestamps and read the measure.

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | STA-07, STA-23 |
| Failure / partial-failure states | STA-18, STA-26 |
| Idempotency / retry / duplicates | STA-05 |
| Auth boundaries & rate limits | STA-14, STA-16 |
| Concurrency / ordering | STA-11, STA-12 |
| Data lifecycle / expiry | Status history purge in dlq-and-data-lifecycle |
| Observability | STA-19, STA-24, STA-25 |
| External-dependency failure | STA-26 |
| State-transition integrity | STA-02 to STA-04, STA-08 to STA-10 |

## Edge Cases

- IF PostgreSQL is unavailable THEN the consumer SHALL stop acknowledging facts and resume without loss when it returns. [STA-26]
- WHEN a `SENT` fact arrives after `DELIVERED` THEN the system SHALL keep `DELIVERED` and append the `SENT` fact to history. [STA-27]

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| STA-01 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-02 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-03 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-04 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-05 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-06 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-07 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-08 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-09 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-10 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-11 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-12 | P1: Single writer with forward-only rules | Specify | Pending |
| STA-13 | P1: Read own notification status | Specify | Pending |
| STA-14 | P1: Read own notification status | Specify | Pending |
| STA-15 | P1: Read own notification status | Specify | Pending |
| STA-16 | P1: Read own notification status | Specify | Pending |
| STA-17 | P1: Read own notification status | Specify | Pending |
| STA-18 | P1: Read own notification status | Specify | Pending |
| STA-19 | P1: Stuck-work alert | Specify | Pending |
| STA-20 | P1: Stuck-work alert | Specify | Pending |
| STA-21 | P1: Stuck-work alert | Specify | Pending |
| STA-22 | P1: No personal data in status | Specify | Pending |
| STA-23 | P1: No personal data in status | Specify | Pending |
| STA-24 | P2: Freshness measures | Specify | Pending |
| STA-25 | P2: Freshness measures | Specify | Pending |
| STA-26 | Edge cases | Specify | Pending |
| STA-27 | Edge cases | Specify | Pending |

**Coverage:** 27 total, 0 mapped to tasks, 27 unmapped until the Tasks phase.

---

## Success Criteria

- [ ] FC-02, FC-09 and FC-11 pass.
- [ ] Event contracts for the accepted fact and attempt outcome exist under `docs/architecture/notification-service/`.
