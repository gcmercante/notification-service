# Platform Foundation Specification

## Problem Statement

The repository is one starter NestJS app named `notification-consumer`, with a third-party telemetry module wired with placeholder credentials (HLD I-08, I-09). Every later feature needs the six confirmed applications, an enforced boundary between business rules and technology (D-54), safe logging (C-09), and a reusable at-least-once publishing path (D-27, D-61). None of these exist.

## Goals

- [ ] Six applications build and start separately from one monorepo.
- [ ] A domain or use-case import of a technology client fails the check suite.
- [ ] A broker outage loses no outbox entry in the integration test.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Business endpoints and notification logic | Later features |
| Deployment and production infrastructure | Needs its own decision; architecture approval does not authorize it |
| Remote CI service | No CI provider is confirmed; a local check command covers FC triggers for now |
| RabbitMQ and SQS adapters | Kafka is the initial broker (C-02); the port keeps them feasible |
| Observability backend selection | Not decided (I-09) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Starter telemetry (I-09) | Remove `@nestjs/observe`, `@nestjs/mau` and the `deploy` script | HLD treats them as starter residue; placeholder secrets in source conflict with §8 | n |
| OQ-55: does the dependency rule cover Redis clients | Yes | D-54 confines Redis to adapters explicitly | n |
| Alert delivery | An alert is a structured log event plus a counter; routing to on-call is out of scope | No observability backend is confirmed, and D-34 requires measures from day one | n |
| OQ-56: per-application database users (FC-21) | Adopt as written | The check cannot be built otherwise | n |
| Local Docker availability | Owner enables Docker in WSL before integration gates run | `docker` is unavailable in this distro today | n |
| Monorepo tooling | NestJS CLI monorepo mode with `bun` scripts | Matches `nest-cli.json`, `jest.config.ts` comments and `bun.lock` | n |

**Open questions:** none - all resolved or logged above. Project-level OQ-16 does not affect this feature.

---

## User Stories

### P1: Six deployable applications ⭐ MVP

**User Story**: As a platform engineer, I want each confirmed application to build and start on its own so that each can deploy and scale separately (D-37).

**Why P1**: Every later feature lands in one of these applications.

**Acceptance Criteria**:
1. The repository SHALL build six separately startable applications, one per responsibility in `CLAUDE.md`. [FND-01]
2. WHEN an application starts with valid configuration THEN it SHALL answer its liveness check with HTTP 200. [FND-02]
3. IF a required configuration value is missing THEN the application SHALL exit with a non-zero code and name the missing variable without printing any value. [FND-03]
4. The repository SHALL contain no `@nestjs/observe` dependency, no placeholder credential, and no `deploy` script. [FND-04]

**Independent Test**: Build all six, start each with valid and with missing configuration, and read the liveness result and exit code.

---

### P1: Enforced dependency rule ⭐ MVP

**User Story**: As an architect, I want technology confined to adapters by an automated check so that broker, database and provider replaceability cannot erode silently (FC-01).

**Why P1**: The rule is cheapest to enforce before any business code exists.

**Acceptance Criteria**:
1. IF a domain or use-case library imports a broker client, database driver, cache client, or provider SDK THEN the check suite SHALL fail and name the offending file. [FND-05]
2. WHEN domain and use-case libraries import only ports and domain types THEN the check suite SHALL pass. [FND-06]

**Independent Test**: Add a forbidden import to a scratch copy of a domain file and watch the check fail with that file named.

---

### P1: Logging without personal data ⭐ MVP

**User Story**: As a data protection owner, I want redaction in the shared logging layer so that no call site can leak content, recipients, or secrets (C-09, FC-08).

**Why P1**: Logging is used from the first line of business code.

**Acceptance Criteria**:
1. WHEN a log entry contains a field classified as recipient, content, API key, or credential THEN the logging layer SHALL replace its value with a fixed redaction marker. [FND-07]
2. WHEN a log entry is written inside a request or message context THEN it SHALL include the available notification, tenant, and integration identifiers. [FND-08]
3. WHEN the privacy scan runs over captured test logs containing seeded email, phone, and key patterns THEN it SHALL fail on any unredacted match. [FND-09]

**Independent Test**: Log a seeded object through the layer, then run the scanner over the output with and without redaction.

---

### P1: Broker port with at-least-once consumption ⭐ MVP

**User Story**: As a use-case author, I want a narrow broker port so that consumers receive domain messages and never see Kafka types (C-02, D-61).

**Why P1**: Submission, dispatch, status and ingress all depend on it.

**Acceptance Criteria**:
1. WHEN a message handler completes successfully THEN the Kafka adapter SHALL commit that message. [FND-10]
2. IF a message handler throws THEN the Kafka adapter SHALL not commit that message and SHALL redeliver it. [FND-11]
3. The broker port SHALL expose no Kafka record, offset, or partition type. [FND-12]
4. The publisher SHALL give each message a stable message identity, a contract version, and trace context as broker-neutral metadata. [FND-13]
5. IF a consumed message has an unsupported contract version or fails schema validation THEN the adapter SHALL report it to the handler as unprocessable and SHALL not retry it through redelivery. [FND-14]

**Independent Test**: Against local Kafka, run a handler that fails once, and assert redelivery and a single commit.

---

### P1: Reusable transactional outbox ⭐ MVP

**User Story**: As an application author, I want one outbox implementation so that a state change and its event commit together (D-27, D-61).

**Why P1**: Four kinds of application use it (API, workers, callbacks), and it is the basis of QS-01.

**Acceptance Criteria**:
1. WHEN a use case commits a state change with an outbox entry THEN both SHALL be stored in one database transaction. [FND-15]
2. IF the transaction rolls back THEN neither the state change nor the outbox entry SHALL exist. [FND-16]
3. WHEN an outbox entry commits THEN the relay SHALL publish it without a deliberate delay (D-19). [FND-17]
4. IF the broker is unavailable THEN the relay SHALL keep the entry and retry until the broker confirms it. [FND-18]
5. WHEN the broker confirms a publish THEN the relay SHALL purge that entry. [FND-19]
6. The relay SHALL expose the current backlog size and oldest entry age as measures (D-34). [FND-20]

**Independent Test**: Stop Kafka, commit entries, restart Kafka, and assert each entry publishes at least once with the same message identity.

---

### P1: Local infrastructure and database isolation ⭐ MVP

**User Story**: As a developer, I want one command to start the dependencies so that integration gates are repeatable (D-45, FC-21).

**Why P1**: Integration gates cannot run without it.

**Acceptance Criteria**:
1. WHEN the local infrastructure command runs THEN PostgreSQL, Kafka, and Redis SHALL start with one database and one database user per application. [FND-21]
2. IF an application's database user attempts to read or write another application's database THEN PostgreSQL SHALL refuse the connection or statement. [FND-22]
3. The repository SHALL hold no real secret; infrastructure credentials SHALL come from environment variables (D-46). [FND-23]

**Independent Test**: Start the stack and connect with one application's user to another application's database.

---

### P2: One local check command

**User Story**: As a contributor, I want one command for all gates so that the FC triggers marked CI have a home until CI exists.

**Why P2**: The separate scripts work without it.

**Acceptance Criteria**:
1. WHEN the check command runs THEN it SHALL run format check, lint, type check, build, unit tests, and architecture checks, and exit non-zero on the first failure. [FND-24]

**Independent Test**: Break one lint rule and confirm a non-zero exit.

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | FND-03, FND-14 |
| Failure / partial-failure states | FND-11, FND-16, FND-18 |
| Idempotency / retry / duplicates | FND-13, FND-18; consumers dedupe in later features |
| Auth boundaries & rate limits | N/A because no business endpoint exists here; FND-22 covers database access |
| Concurrency / ordering | N/A because broker ordering is never a correctness requirement (D-49) |
| Data lifecycle / expiry | FND-19 |
| Observability | FND-07, FND-08, FND-20 |
| External-dependency failure | FND-11, FND-18 |
| State-transition integrity | N/A because no domain state exists here |

## Edge Cases

- IF two relay instances run at once THEN each outbox entry SHALL still publish at least once, and duplicates SHALL keep the same message identity. [FND-25]
- IF a log field is unclassified THEN the logging layer SHALL drop nested message-body objects rather than serialize them. [FND-26]

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| FND-01 | P1: Six deployable applications | Tasks | In Tasks |
| FND-02 | P1: Six deployable applications | Tasks | In Tasks |
| FND-03 | P1: Six deployable applications | Tasks | In Tasks |
| FND-04 | P1: Six deployable applications | Tasks | In Tasks |
| FND-05 | P1: Enforced dependency rule | Tasks | In Tasks |
| FND-06 | P1: Enforced dependency rule | Tasks | In Tasks |
| FND-07 | P1: Logging without personal data | Tasks | In Tasks |
| FND-08 | P1: Logging without personal data | Tasks | In Tasks |
| FND-09 | P1: Logging without personal data | Tasks | In Tasks |
| FND-10 | P1: Broker port with at-least-once consumption | Tasks | In Tasks |
| FND-11 | P1: Broker port with at-least-once consumption | Tasks | In Tasks |
| FND-12 | P1: Broker port with at-least-once consumption | Tasks | In Tasks |
| FND-13 | P1: Broker port with at-least-once consumption | Tasks | In Tasks |
| FND-14 | P1: Broker port with at-least-once consumption | Tasks | In Tasks |
| FND-15 | P1: Reusable transactional outbox | Tasks | In Tasks |
| FND-16 | P1: Reusable transactional outbox | Tasks | In Tasks |
| FND-17 | P1: Reusable transactional outbox | Tasks | In Tasks |
| FND-18 | P1: Reusable transactional outbox | Tasks | In Tasks |
| FND-19 | P1: Reusable transactional outbox | Tasks | In Tasks |
| FND-20 | P1: Reusable transactional outbox | Tasks | In Tasks |
| FND-21 | P1: Local infrastructure and database isolation | Tasks | In Tasks |
| FND-22 | P1: Local infrastructure and database isolation | Tasks | In Tasks |
| FND-23 | P1: Local infrastructure and database isolation | Tasks | In Tasks |
| FND-24 | P2: One local check command | Tasks | In Tasks |
| FND-25 | Edge cases | Tasks | In Tasks |
| FND-26 | Edge cases | Tasks | In Tasks |

**Coverage:** 26 total, 26 mapped to tasks, 0 unmapped.

---

## Success Criteria

- [ ] `bun run` check command passes with six applications present.
- [ ] Zero unredacted seeded values in the privacy scan.
- [ ] FC-01, FC-08 and FC-21 run as part of this feature.
