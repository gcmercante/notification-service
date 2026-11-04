# Platform Foundation Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/platform-foundation/design.md`
**Status**: Approved (owner, 2026-11-04). Implementation has not started and waits for the owner's go-ahead.

**Before execution:** create an implementation branch from the current one (the current branch holds ADR work). Phase 3 onward needs Docker enabled in this WSL distro.

---

## Test Coverage Matrix

> Generated from codebase, project guidelines, and spec - confirm before Execute. Guidelines found: `CLAUDE.md` (Implementation and Verification), `jest.config.ts`. No coverage thresholds exist, so strong defaults apply. Existing samples: `src/app.controller.spec.ts`, `test/app.e2e-spec.ts` (Jest, ts-jest, supertest).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Core libraries (`core-*`: rules, use cases) | unit | All branches; 1:1 to spec ACs; every listed edge case | `libs/core-*/src/**/*.spec.ts` | `bun run test` |
| Architecture and privacy checks | unit | Passing and failing fixture for each check | `test/architecture/*.spec.ts` | `bun run test` |
| Application shell (bootstrap, liveness) | e2e | Each route: happy path plus start-up failure | `apps/*/test/*.e2e-spec.ts` | `bun run test:e2e` |
| Adapters (`adapter-*`) touching infrastructure | integration | Key paths plus failure paths, against real services | `libs/adapter-*/test/*.integration-spec.ts` | `bun run test:integration` |
| Adapters with no infrastructure (logger, metrics) | unit | Key paths and error paths | `libs/adapter-*/src/**/*.spec.ts` | `bun run test` |
| Local infrastructure | integration | Each service reachable; isolation enforced | `test/infra/*.integration-spec.ts` | `bun run test:integration` |
| Package scripts and config only | none | Build gate only | - | Build gate |

## Gate Check Commands

> Generated from codebase - confirm before Execute. `test:integration` is added by T11. `build` becomes `nest build --all` and `lint` widens in earlier tasks.

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | Tasks with unit tests only | `bun run test` |
| E2E | Tasks with e2e tests | `bun run test && bun run test:e2e` |
| Integration | Tasks with integration tests | `bun run test && bun run test:integration` |
| Build | Config-only tasks and every phase end | `bun run build && bun run lint && bun run test && bun run test:e2e` |

From T11 on, the phase-end Build gate also runs `bun run test:integration`.

---

## Execution Plan

Phases run in order, and tasks run in order within a phase. Each phase's first task follows the previous phase's last task.

### Phase 1: Monorepo baseline

```
T1 → T2 → T3 → T4 → T5
```

### Phase 2: Boundaries and observability

```
T5 → T6 → T7 → T8 → T9 → T10
```

### Phase 3: Local infrastructure

```
T10 → T11 → T12
```

### Phase 4: Broker

```
T12 → T13 → T14 → T15
```

### Phase 5: Outbox and checks

```
T15 → T16 → T17 → T18 → T19
```

---

## Task Breakdown

### T1: Commit the starter as baseline and fix its metadata

**What**: Commit the untracked starter scaffold, rename the package to `notification-service`, and widen `lint` to `apps/ libs/ test/ src/`.
**Where**: `package.json`
**Depends on**: None
**Reuses**: Existing scaffold
**Requirement**: FND-01

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Starter files are committed; `.agents`, `.claude`, `.cursor` and `.github` are not in the commit
- [ ] Gate check passes: Build
- [ ] Test count: 1 unit and 1 e2e pass

**Tests**: none
**Gate**: build

**Commit**: `chore: add starter scaffold as implementation baseline`

---

### T2: Remove starter telemetry and deploy script

**What**: Remove `@nestjs/observe`, `@nestjs/mau`, the placeholder credentials, and the `deploy` script.
**Where**: `src/app.module.ts`
**Depends on**: T1
**Reuses**: None
**Requirement**: FND-04

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A repository search finds no `@nestjs/observe`, `@nestjs/mau`, `YOUR_APP_KEY`, or `deploy` script
- [ ] `src/main.ts` boots with no `instrument` option
- [ ] Gate check passes: Build
- [ ] Test count: 1 unit and 1 e2e pass

**Tests**: none
**Gate**: build

**Commit**: `chore: remove starter telemetry and deploy script`

---

### T3: Convert to a monorepo with the API / Gateway app

**What**: Switch `nest-cli.json` to monorepo mode, move the starter to `apps/api-gateway`, replace the `Hello World` route with `GET /health/live`, and make `build` run `nest build --all`.
**Where**: `apps/api-gateway/`
**Depends on**: T2
**Reuses**: `src/main.ts`, `test/app.e2e-spec.ts` pattern
**Requirement**: FND-01, FND-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `bun run build` produces the app
- [ ] E2E test asserts liveness returns 200
- [ ] Gate check passes: E2E
- [ ] Test count: the 2 starter `Hello World` tests are replaced as the design states; no other removal

**Tests**: e2e
**Gate**: e2e

**Commit**: `refactor: convert to monorepo with api-gateway application`

---

### T4: Add the other five applications

**What**: Generate `email-worker`, `sms-worker`, `push-worker`, `provider-callbacks`, and `delivery-status`, each with `GET /health/live` and an e2e test.
**Where**: `apps/`
**Depends on**: T3
**Reuses**: The api-gateway shell from T3
**Requirement**: FND-01, FND-02

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Each of the six builds and answers liveness
- [ ] Gate check passes: E2E
- [ ] Test count: 6 liveness e2e tests pass

**Tests**: e2e
**Gate**: e2e

**Commit**: `feat: add worker, callbacks and delivery-status applications`

---

### T5: Fail clearly on missing configuration

**What**: Add `core-config` and call it from all six bootstraps, exiting non-zero and naming missing variables without values.
**Where**: `libs/core-config/`
**Depends on**: T4
**Reuses**: None
**Requirement**: FND-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Unit tests cover present, missing, and several-missing cases, and assert no value appears in the error
- [ ] E2E test starts one built app with a missing variable and asserts the exit code and message
- [ ] Gate check passes: E2E, then Build at phase end
- [ ] Test count: no reduction from T4

**Tests**: e2e
**Gate**: e2e

**Commit**: `feat(config): exit with named variables on missing configuration`

---

### T6: Enforce the dependency rule

**What**: Add the path-scoped `no-restricted-imports` override for `libs/core-*` and for use-case and domain folders in apps, with a test running oxlint over passing and failing fixtures.
**Where**: `.oxlintrc.json`
**Depends on**: T5
**Reuses**: Existing oxlint setup
**Requirement**: FND-05, FND-06

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A forbidden broker, database, cache, or provider import fails and names the file
- [ ] A port-only fixture passes
- [ ] Gate check passes: Quick
- [ ] Test count: no reduction, plus the fixture tests

**Tests**: unit
**Gate**: quick

**Commit**: `feat(architecture): enforce dependency rule for core libraries`

---

### T7: Add the log sanitizer and context

**What**: Add `core-logging` with `sanitize` and the log context.
**Where**: `libs/core-logging/`
**Depends on**: T6
**Reuses**: None
**Requirement**: FND-07, FND-08, FND-26

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Tests cover each classified field, nested objects, arrays, and context isolation across concurrent async work
- [ ] Gate check passes: Quick
- [ ] Test count: no reduction, plus the new tests

**Tests**: unit
**Gate**: quick

**Commit**: `feat(logging): add field sanitizer and log context`

---

### T8: Add the platform logger

**What**: Add `adapter-logging` on pino and use it in all six applications.
**Where**: `libs/adapter-logging/`
**Depends on**: T7
**Reuses**: `core-logging`
**Requirement**: FND-07, FND-08

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Captured output shows redaction and context identifiers through the Nest logger interface
- [ ] Gate check passes: Quick
- [ ] Test count: no reduction, plus the new tests

**Tests**: unit
**Gate**: quick

**Commit**: `feat(logging): add pino adapter as the platform logger`

---

### T9: Add the privacy scan

**What**: Add a scanner that fails on seeded email, phone, and key patterns in captured logs.
**Where**: `test/architecture/privacy-scan.spec.ts`
**Depends on**: T8
**Reuses**: `adapter-logging`
**Requirement**: FND-09

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] The scan fails on an unredacted fixture and passes on logger output
- [ ] Gate check passes: Quick
- [ ] Test count: no reduction, plus the new tests

**Tests**: unit
**Gate**: quick

**Commit**: `test(privacy): scan captured logs for personal data patterns`

---

### T10: Add metrics and the alert signal

**What**: Add `core-metrics` with `emitAlert`, plus `adapter-metrics` serving Prometheus text at `GET /metrics`.
**Where**: `libs/core-metrics/`
**Depends on**: T9
**Reuses**: `core-logging`
**Requirement**: FND-20

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `emitAlert` writes one structured event and one counter increment
- [ ] Gate check passes: Quick, then Build at phase end
- [ ] Test count: no reduction, plus the new tests

**Tests**: unit
**Gate**: quick

**Commit**: `feat(metrics): add metrics port, alert signal and prometheus adapter`

---

### T11: Start local infrastructure with one command

**What**: Add the compose file, `.env.example`, `infra:up` and `infra:down`, `test:integration`, and a connectivity test for PostgreSQL, Kafka, and Redis.
**Where**: `infra/local/compose.yaml`
**Depends on**: T10
**Reuses**: None
**Requirement**: FND-21, FND-23

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `bun run infra:up` starts all three, and a test connects to each
- [ ] Compose fails when a credential variable is unset; the repository holds no real secret
- [ ] Gate check passes: Integration
- [ ] Test count: no reduction, plus the new tests

**Tests**: integration
**Gate**: integration

**Commit**: `feat(infra): add local postgres, kafka and redis stack`

---

### T12: Create isolated application databases

**What**: Add the init script creating one database and user per application, with cross-database access revoked, and a test proving refusal (FC-21).
**Where**: `infra/local/postgres-init.sh`
**Depends on**: T11
**Reuses**: The T11 stack
**Requirement**: FND-21, FND-22

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Each user connects to its own database and is refused on every other one
- [ ] Gate check passes: Integration, then Build at phase end
- [ ] Test count: no reduction, plus the new tests

**Tests**: integration
**Gate**: integration

**Commit**: `feat(infra): isolate application databases and users`

---

### T13: Define the broker port

**What**: Add `core-messaging` with the envelope, its builder, and the publisher and consumer ports.
**Where**: `libs/core-messaging/`
**Depends on**: T12
**Reuses**: None
**Requirement**: FND-12, FND-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Builder tests assert identity, version, and trace metadata
- [ ] No Kafka type is exported, and the dependency rule passes
- [ ] Gate check passes: Quick
- [ ] Test count: no reduction, plus the new tests

**Tests**: unit
**Gate**: quick

**Commit**: `feat(messaging): define broker port and message envelope`

---

### T14: Implement the Kafka publisher

**What**: Add `adapter-kafka`'s publisher, resolving only on broker confirmation and mapping metadata to headers, and trust the client's install script.
**Where**: `libs/adapter-kafka/src/kafka-publisher.ts`
**Depends on**: T13
**Reuses**: `core-messaging`
**Requirement**: FND-13

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] A clean install loads the native client
- [ ] Test publishes and reads back identity, version, and trace metadata
- [ ] Test asserts rejection when the broker cannot confirm
- [ ] Gate check passes: Integration
- [ ] Test count: no reduction, plus the new tests

**Tests**: integration
**Gate**: integration

**Commit**: `feat(kafka): add publisher with broker confirmation`

---

### T15: Implement the Kafka consumer

**What**: Add the consumer, committing after handler completion, redelivering on a throw, and routing bad versions and shapes to `unprocessable`.
**Where**: `libs/adapter-kafka/src/kafka-consumer.ts`
**Depends on**: T14
**Reuses**: `core-messaging`
**Requirement**: FND-10, FND-11, FND-14

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Test: success commits, and a restart does not redeliver
- [ ] Test: a throw redelivers the same message, then commits once it succeeds
- [ ] Test: an unsupported version reaches `unprocessable`, commits, and is not redelivered
- [ ] Gate check passes: Integration, then Build at phase end
- [ ] Test count: no reduction, plus the new tests

**Tests**: integration
**Gate**: integration

**Commit**: `feat(kafka): add consumer with commit after handling`

---

### T16: Add the relay use case

**What**: Add `core-outbox` with its ports and a relay that claims, publishes, retries with a capped delay, and reports backlog measures.
**Where**: `libs/core-outbox/`
**Depends on**: T15
**Reuses**: `core-messaging`, `core-metrics`
**Requirement**: FND-18, FND-19, FND-20

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Tests with fakes cover success, publish failure keeping the entry, and backlog and oldest-age measures
- [ ] Gate check passes: Quick
- [ ] Test count: no reduction, plus the new tests

**Tests**: unit
**Gate**: quick

**Commit**: `feat(outbox): add relay use case and ports`

---

### T17: Add the PostgreSQL outbox store

**What**: Add `adapter-postgres` with the pool, transaction runner, outbox migration, store, and `pg_notify` on insert.
**Where**: `libs/adapter-postgres/`
**Depends on**: T16
**Reuses**: `core-outbox`
**Requirement**: FND-15, FND-16, FND-19

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Test: a committed transaction holds both the state row and the outbox entry
- [ ] Test: a rolled-back transaction holds neither
- [ ] Test: a claimed batch deletes on success and survives a publish failure
- [ ] Gate check passes: Integration
- [ ] Test count: no reduction, plus the new tests

**Tests**: integration
**Gate**: integration

**Commit**: `feat(outbox): add postgres store and transaction runner`

---

### T18: Prove the relay end to end

**What**: Add a relay runner listening for notifications with a 1 s sweep, with fault tests against real Kafka and PostgreSQL.
**Where**: `libs/adapter-postgres/test/outbox-relay.integration-spec.ts`
**Depends on**: T17
**Reuses**: `adapter-kafka`, `core-outbox`
**Requirement**: FND-17, FND-18, FND-25

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Test: a commit publishes through the notification path, with the sweep interval set too long to explain it
- [ ] Test: with Kafka stopped, entries stay, and they publish with the same message identity after restart
- [ ] Test: two relays publish every entry at least once
- [ ] Gate check passes: Integration
- [ ] Test count: no reduction, plus the new tests

**Tests**: integration
**Gate**: integration

**Commit**: `test(outbox): prove relay under broker outage and concurrency`

---

### T19: Add the check command

**What**: Add `check`, running format check, lint, type check, build, unit tests, and architecture checks, and exiting on the first failure.
**Where**: `package.json`
**Depends on**: T18
**Reuses**: Existing scripts
**Requirement**: FND-24

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `bun run check` exits 0 on the clean tree
- [ ] It exits non-zero on a temporary lint violation, which is then reverted
- [ ] Gate check passes: Build, including integration
- [ ] Test count: no reduction

**Tests**: none
**Gate**: build

**Commit**: `chore: add single check command for local gates`

---

## Phase Execution Map

```
Phase 1:  T1 → T2 → T3 → T4 → T5
Phase 2:  T6 → T7 → T8 → T9 → T10
Phase 3:  T11 → T12
Phase 4:  T13 → T14 → T15
Phase 5:  T16 → T17 → T18 → T19
```

Execution is strictly sequential. The 19 tasks pack into 3 batches of whole phases: Phase 1 (5 tasks), Phases 2 and 3 (7 tasks), and Phases 4 and 5 (7 tasks). Execute offers batch sub-agents before starting.

---

## Task Granularity Check

| Task | Scope | Status |
| ---- | ----- | ------ |
| T1, T2, T19 | One config concern each | ✅ Granular |
| T3, T4 | One structural change; T4 repeats one shell five times | ⚠️ OK, cohesive and generated |
| T5, T7, T10, T13, T16, T17 | One library each | ✅ Granular |
| T6, T9, T11, T12 | One check or one infrastructure concern | ✅ Granular |
| T8, T14, T15, T18 | One adapter class or one test suite | ✅ Granular |

---

## Diagram-Definition Cross-Check

Every task depends only on the task before it, and the diagrams show the same chain.

| Task | Depends On (task body) | Diagram Shows | Status |
| ---- | ---------------------- | ------------- | ------ |
| T1 | None | None | ✅ Match |
| T2 to T5 | Previous task | Phase 1 chain | ✅ Match |
| T6 | T5 | Phase 2 start | ✅ Match |
| T7 to T10 | Previous task | Phase 2 chain | ✅ Match |
| T11 | T10 | Phase 3 start | ✅ Match |
| T12 | T11 | Phase 3 chain | ✅ Match |
| T13 | T12 | Phase 4 start | ✅ Match |
| T14, T15 | Previous task | Phase 4 chain | ✅ Match |
| T16 | T15 | Phase 5 start | ✅ Match |
| T17 to T19 | Previous task | Phase 5 chain | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| ---- | --------------------------- | --------------- | --------- | ------ |
| T1, T2, T19 | Package scripts and config | none | none | ✅ OK |
| T3, T4, T5 | Application shell | e2e | e2e | ✅ OK |
| T6, T9 | Architecture and privacy checks | unit | unit | ✅ OK |
| T7, T10, T13, T16 | Core libraries | unit | unit | ✅ OK |
| T8 | Adapter with no infrastructure | unit | unit | ✅ OK |
| T11, T12 | Local infrastructure | integration | integration | ✅ OK |
| T14, T15, T17, T18 | Adapters touching infrastructure | integration | integration | ✅ OK |

## Requirement Coverage

| Requirement | Task | Requirement | Task |
| ----------- | ---- | ----------- | ---- |
| FND-01 | T1, T3, T4 | FND-14 | T15 |
| FND-02 | T3, T4 | FND-15 | T17 |
| FND-03 | T5 | FND-16 | T17 |
| FND-04 | T2 | FND-17 | T18 |
| FND-05 | T6 | FND-18 | T16, T18 |
| FND-06 | T6 | FND-19 | T16, T17 |
| FND-07 | T7, T8 | FND-20 | T10, T16 |
| FND-08 | T7, T8 | FND-21 | T11, T12 |
| FND-09 | T9 | FND-22 | T12 |
| FND-10 | T15 | FND-23 | T11 |
| FND-11 | T15 | FND-24 | T19 |
| FND-12 | T13 | FND-25 | T18 |
| FND-13 | T13, T14 | FND-26 | T7 |
