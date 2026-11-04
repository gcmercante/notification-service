# Email Dispatch Specification

## Problem Statement

Accepted email notifications must reach a provider under the confirmed retry policy, without knowingly sending twice, and every attempt must produce a fact for the status owner (D-07, D-10, D-58, D-61). The three workers share one dispatch workflow (D-58), so this feature builds that workflow and proves it on email through Amazon SES (AD-001).

## Goals

- [ ] A provider that always fails gets exactly 4 attempts, with delays inside the equal-jitter bounds (FC-24).
- [ ] An email reaches SES, and its status becomes `SENT`.
- [ ] A redelivered dispatch whose ledger says done is not sent again (FC-16).

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| SES status events | Feature 7 |
| Failover or fallback | Not approved (C-05) |
| SMS and push adapters | Features 8 and 9 |
| DLQ replay | Feature 10; this feature only hands off to the DLQ |
| Tenant-specific sender identities | OQ-23 is open |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| OQ-16: provider-call timeout | 10 seconds, configured per provider account | The owner deferred this, and a call needs some bound; it stays configuration | n |
| OQ-16: unknown outcome (timeout after send, or crash with ledger in flight) | Never resend. The attempt is recorded unknown, status stays `PROCESSING`, and the D-40 alert fires | Avoids duplicates, adds no status (OQ-54), and uses only confirmed mechanisms. Cost: a possibly lost notification needs an operator | n |
| What counts as retryable from SES | Throttling and 5xx-class errors, plus connection failures before the request was sent | §7.4 examples; exact error names are fixed by the adapter's tests against SES documentation | n |
| Dead-lettering scope (§7.4, Proposed) | Only unprocessable messages go to the DLQ; exhausted retries do not | HLD proposal; D-39 does not change it | n |
| Retry mechanism on Kafka | Ledger holds attempt count and next-attempt time; a delay topic carries the retry | §7.4 says Kafka has no native delay and in-place retry blocks a partition | n |
| Sender address | One verified sender per provider account, in configuration | OQ-23 is open and C-14 makes accounts platform-owned | n |
| SES status mechanism | SNS to an HTTPS endpoint (feature 7) | One push mechanism per provider is enough (§5.3) | n |
| SES idempotency | None available in the pages read, so no key is sent | Residual duplicate window stays documented (QS-03) | n |
| Throttle values (OQ-11) | Configured per account, starting from the account's SES sending quota | D-58 requires per-account throttling; values depend on the account | n |
| Bulkhead per provider (§7.5, Proposed) | Concurrency limit per provider account within a worker | Protects QS-06 without new infrastructure | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Send through the routed provider ⭐ MVP

**User Story**: As a tenant, I want my email sent through the provider selected for me so that routing configuration takes effect at send time (D-55).

**Why P1**: It is the worker's core function.

**Acceptance Criteria**:
1. WHEN the email worker consumes a dispatch request THEN it SHALL resolve the provider through the routing policy for the first attempt. [DSP-01]
2. WHEN the provider accepts the send THEN the worker SHALL commit the attempt as done with the provider reference and an accepted outcome in one transaction. [DSP-02]
3. The attempt record SHALL hold the provider used, the account reference, and whether the source was `tenant` or `default`. [DSP-03]
4. WHEN a retry runs after routing configuration changed THEN the worker SHALL use the first attempt's provider. [DSP-04]
5. IF the policy returns no eligible provider at dispatch THEN the worker SHALL publish a `FAILED` outcome with reason `NO_ELIGIBLE_PROVIDER` and make no attempt. [DSP-05]
6. WHEN the worker calls SES THEN it SHALL decrypt content and recipient immediately before the call and SHALL not store or log the plain values. [DSP-06]
7. The worker SHALL commit or ack the dispatch request only after its ledger transaction commits. [DSP-07]

**Independent Test**: Submit an email against the SES sandbox, and read status `SENT` and the attempt record.

---

### P1: Retry policy ⭐ MVP

**User Story**: As a platform owner, I want the confirmed retry policy enforced exactly so that provider load is bounded and predictable (D-07, D-10, D-15, D-18, FC-24).

**Why P1**: It is a confirmed guarantee with an approved fitness check.

**Acceptance Criteria**:
1. IF every attempt fails as retryable THEN the worker SHALL make exactly 4 attempts and then publish `FAILED` with reason `RETRIES_EXHAUSTED`. [DSP-08]
2. The delay before retry n SHALL be d/2 plus a random value in [0, d/2], where d = min(30 s, 1 s × 2^(n−1)). [DSP-09]
3. IF the provider permanently rejects the send THEN the worker SHALL make exactly 1 attempt and publish `FAILED` with reason `REJECTED_BY_PROVIDER`. [DSP-10]
4. WHILE retries are pending the worker SHALL publish an outcome per attempt that keeps the notification in `PROCESSING` with its attempt number. [DSP-11]
5. WHEN a broker redelivery arrives for a request that never reached the provider THEN the worker SHALL not count an attempt. [DSP-12]
6. The worker SHALL keep attempt count and next-attempt time durable across restarts. [DSP-13]
7. The worker SHALL never call a tenant's default provider as a fallback for a failing configured provider. [DSP-14]
8. The backoff calculation SHALL take its random source as an injected dependency. [DSP-15]

**Independent Test**: A scripted fake behind the provider port fails every time; assert attempt count, delays under a fixed random source, and terminal outcome.

---

### P1: Duplicate containment ⭐ MVP

**User Story**: As a recipient, I want not to receive the same email twice from a redelivery so that retries inside the platform are invisible to me (QS-03, D-61).

**Why P1**: At-least-once hops make redelivery routine.

**Acceptance Criteria**:
1. WHEN a dispatch request arrives THEN the worker SHALL mark the attempt in flight in its ledger before calling the provider. [DSP-16]
2. WHEN a redelivered request finds its ledger marked done THEN the worker SHALL make no provider call and SHALL republish nothing beyond the existing outbox entry. [DSP-17]
3. IF the provider call times out after the request may have been sent THEN the worker SHALL record the attempt as unknown, make no further attempt, and change no status. [DSP-18]
4. IF a redelivered request finds its ledger marked in flight THEN the worker SHALL record the attempt as unknown, make no provider call, and change no status. [DSP-19]
5. WHEN the broker is unavailable after a provider call THEN the worker SHALL still commit the attempt and outcome, and SHALL publish the outcome after the broker returns. [DSP-20]
6. The worker SHALL count unknown attempts by provider. [DSP-21]

**Independent Test**: Kill the worker between the provider call and the commit, restart it, and assert no second call and an unknown record.

---

### P1: Unprocessable messages ⭐ MVP

**User Story**: As an operator, I want poison messages set aside and reflected in status so that they neither block a channel nor vanish (D-29, D-39).

**Why P1**: A blocked partition would stall the channel.

**Acceptance Criteria**:
1. IF a dispatch request fails schema validation or decryption THEN the worker SHALL move it to the channel's DLQ and publish `FAILED` with reason `UNPROCESSABLE`. [DSP-22]
2. WHEN a message goes to the DLQ THEN the worker SHALL continue with the next message. [DSP-23]
3. The DLQ SHALL hold content and recipients only in encrypted form. [DSP-24]

**Independent Test**: Publish a malformed request and assert the DLQ entry, the outcome, and that the next message is processed.

---

### P1: Provider isolation and throttling ⭐ MVP

**User Story**: As a tenant on a healthy provider, I want another provider's outage to leave my sends unaffected so that failures stay contained (QS-06, D-58).

**Why P1**: All tenants share platform-owned accounts (C-14).

**Acceptance Criteria**:
1. The worker SHALL never call a provider account faster than the rate configured for that account. [DSP-25]
2. WHILE one provider account is slow or failing the worker SHALL keep processing work for other provider accounts within their concurrency limits. [DSP-26]
3. The email worker SHALL read provider secrets only for its own channel's accounts. [DSP-27]

**Independent Test**: With two fake accounts, stall one and assert the other's throughput holds. Assert the call rate under load.

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | DSP-22 |
| Failure / partial-failure states | DSP-08, DSP-10, DSP-18, DSP-19, DSP-20 |
| Idempotency / retry / duplicates | DSP-08 to DSP-13, DSP-16 to DSP-19 |
| Auth boundaries & rate limits | DSP-25, DSP-27; no inbound HTTP besides liveness |
| Concurrency / ordering | DSP-26, DSP-28 |
| Data lifecycle / expiry | DSP-29 |
| Observability | DSP-21, DSP-30 |
| External-dependency failure | DSP-18, DSP-20, DSP-26 |
| State-transition integrity | DSP-02, DSP-11 |

## Edge Cases

- WHEN two worker instances receive the same request at once THEN the ledger SHALL allow exactly one to mark it in flight. [DSP-28]
- WHEN an attempt ledger entry passes the retention period set for worker data THEN it SHALL be purged with no effect on delivery status. [DSP-29]
- WHEN an attempt ends THEN the worker SHALL record attempt latency and outcome class by channel and provider. [DSP-30]
- IF SES returns an account-level error such as a suspended account THEN the adapter SHALL classify it as retryable only when its documentation marks it transient, and otherwise as permanent. [DSP-31]

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| DSP-01 | P1: Send through the routed provider | Specify | Pending |
| DSP-02 | P1: Send through the routed provider | Specify | Pending |
| DSP-03 | P1: Send through the routed provider | Specify | Pending |
| DSP-04 | P1: Send through the routed provider | Specify | Pending |
| DSP-05 | P1: Send through the routed provider | Specify | Pending |
| DSP-06 | P1: Send through the routed provider | Specify | Pending |
| DSP-07 | P1: Send through the routed provider | Specify | Pending |
| DSP-08 | P1: Retry policy | Specify | Pending |
| DSP-09 | P1: Retry policy | Specify | Pending |
| DSP-10 | P1: Retry policy | Specify | Pending |
| DSP-11 | P1: Retry policy | Specify | Pending |
| DSP-12 | P1: Retry policy | Specify | Pending |
| DSP-13 | P1: Retry policy | Specify | Pending |
| DSP-14 | P1: Retry policy | Specify | Pending |
| DSP-15 | P1: Retry policy | Specify | Pending |
| DSP-16 | P1: Duplicate containment | Specify | Pending |
| DSP-17 | P1: Duplicate containment | Specify | Pending |
| DSP-18 | P1: Duplicate containment | Specify | Pending |
| DSP-19 | P1: Duplicate containment | Specify | Pending |
| DSP-20 | P1: Duplicate containment | Specify | Pending |
| DSP-21 | P1: Duplicate containment | Specify | Pending |
| DSP-22 | P1: Unprocessable messages | Specify | Pending |
| DSP-23 | P1: Unprocessable messages | Specify | Pending |
| DSP-24 | P1: Unprocessable messages | Specify | Pending |
| DSP-25 | P1: Provider isolation and throttling | Specify | Pending |
| DSP-26 | P1: Provider isolation and throttling | Specify | Pending |
| DSP-27 | P1: Provider isolation and throttling | Specify | Pending |
| DSP-28 | Edge cases | Specify | Pending |
| DSP-29 | Edge cases | Specify | Pending |
| DSP-30 | Edge cases | Specify | Pending |
| DSP-31 | Edge cases | Specify | Pending |

**Coverage:** 31 total, 0 mapped to tasks, 31 unmapped until the Tasks phase.

---

## Success Criteria

- [ ] FC-16, FC-24, FC-25 (email), FC-29 and FC-30 pass; FC-19 passes for the dispatch path.
- [ ] A refining ADR for OQ-16 is written if the owner confirms the default.
