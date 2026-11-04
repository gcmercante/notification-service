# Provider Routing Specification

## Problem Statement

A tenant's notification must go to the provider configured for that tenant and channel, otherwise to the channel's platform-wide default, and otherwise be rejected (D-03, D-42, D-43). Administrators need to manage this configuration (D-06), and the send path must read it without a database call per send (D-44).

## Goals

- [ ] The resolution rule is deterministic and table-tested (FC-26).
- [ ] Routing still resolves with Redis down or empty (FC-20).
- [ ] Every configuration change is audited.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| Failover, fallback, weighted, cost-based routing | Not approved (C-05) |
| Per-integration overrides | Configuration is per tenant (D-09) |
| Provider credentials in routing data | Routing holds references only (D-59) |
| Provider adapters | Features 6, 8 and 9 |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Platform-wide defaults | SES for email, textbee for SMS, OneSignal for push | Confirmed by the owner (D-71) | y |
| OQ-51 and OQ-56: definition of a valid provider | An adapter is registered for the channel, a platform-owned account reference exists, and the provider is not disabled (P-02a) | FC-19 depends on this wording | n |
| Provider catalog location | A table in the API / Gateway database, managed by administrators | Provider disablement and account references need an owner; §6.1 places routing data there | n |
| Which applications know that an adapter exists | The catalog lists provider identifiers supported by the deployed release, from configuration | The API has no adapters and must still pre-check (P-02a) | n |
| Cache entry lifetime | 5 minutes, configurable | D-44 says change timing does not matter; the HLD asks only for a safety-net TTL | n |
| Read-only database grant for fallback (P-02b, Proposed) | Workers get a read-only grant on routing tables | Simpler than an internal endpoint, and FC-21 allows this one exception | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Manage tenant configuration and defaults ⭐ MVP

**User Story**: As an administrator, I want to set a tenant's provider per channel and each channel's default so that routing changes need no code change (D-06, D-42).

**Why P1**: Routing has no data otherwise.

**Acceptance Criteria**:
1. WHEN an administrator sets a tenant's provider for a channel THEN the system SHALL store at most one provider for that tenant and channel, replacing any previous value. [RTE-01]
2. WHEN an administrator sets a channel default THEN the system SHALL store exactly one platform-wide default for that channel. [RTE-02]
3. IF an administrator points configuration at a provider that is not valid for that channel THEN the system SHALL respond 422 and store nothing. [RTE-03]
4. WHEN an administrator removes a tenant's configuration for a channel THEN later resolutions for that tenant and channel SHALL use the default. [RTE-04]
5. WHEN any routing configuration changes THEN the system SHALL write an audit entry with actor, time, and old and new values. [RTE-05]
6. The routing configuration SHALL hold provider account references and SHALL hold no credential. [RTE-06]
7. IF an integration key calls a routing endpoint THEN the system SHALL respond 401. [RTE-07]

**Independent Test**: Set, replace and remove a tenant's configuration through the admin API, and read the audit trail.

---

### P1: Resolve the provider ⭐ MVP

**User Story**: As a channel worker, I want one routing policy so that provider selection stays outside the send workflow (D-55).

**Why P1**: Both the submission pre-check and dispatch call it.

**Acceptance Criteria**:
1. WHEN a tenant has a valid provider configured for the channel THEN the policy SHALL return that provider, its account reference, and source `tenant`. [RTE-08]
2. WHEN a tenant has no configuration for the channel and the default is valid THEN the policy SHALL return the default, its account reference, and source `default`. [RTE-09]
3. IF neither the tenant configuration nor the default yields a valid provider THEN the policy SHALL return a no-eligible-provider result. [RTE-10]
4. IF a tenant's configured provider is invalid THEN the policy SHALL return no-eligible-provider and SHALL not use the default. [RTE-11]
5. WHEN two integrations of one tenant resolve the same channel THEN the policy SHALL return the same provider. [RTE-12]

**Independent Test**: Table-driven unit tests over the policy with an in-memory configuration port.

---

### P1: Cached configuration with fallback ⭐ MVP

**User Story**: As a platform owner, I want routing served from Redis with the database as source of truth so that sends need no database read and survive a cache outage (D-44, FC-20).

**Why P1**: D-44 places the send path on the cache.

**Acceptance Criteria**:
1. WHEN an administrator changes routing configuration THEN the system SHALL write the new value through to the cache after the database commit. [RTE-13]
2. IF the cache has no entry THEN the reader SHALL read from the source database and populate the cache. [RTE-14]
3. IF Redis is unavailable THEN the reader SHALL read from the source database and return the correct resolution. [RTE-15]
4. IF a cache write fails after the database commit THEN the administrative change SHALL still succeed and the failure SHALL be counted. [RTE-16]
5. The cache SHALL hold no value that is absent from the database. [RTE-17]

**Independent Test**: Stop Redis, resolve a provider, restart Redis, and resolve again.

---

### P2: Routing visibility

**User Story**: As an operator, I want to see how much traffic depends on defaults so that the default's importance stays visible (HLD §9).

**Why P2**: Useful for operations, not needed to route.

**Acceptance Criteria**:
1. WHEN the policy returns a provider THEN the system SHALL count it by channel, provider, and source. [RTE-18]

**Independent Test**: Resolve tenant-configured and default cases and read the counters.

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | RTE-03 |
| Failure / partial-failure states | RTE-16 |
| Idempotency / retry / duplicates | RTE-01 and RTE-02 are replace operations, so repeats are safe |
| Auth boundaries & rate limits | RTE-07 |
| Concurrency / ordering | RTE-19 |
| Data lifecycle / expiry | RTE-20 |
| Observability | RTE-18 |
| External-dependency failure | RTE-14, RTE-15 |
| State-transition integrity | N/A because configuration has no lifecycle states beyond present or absent |

## Edge Cases

- WHEN two administrators change the same tenant and channel at once THEN the last database commit SHALL win and both SHALL appear in the audit trail. [RTE-19]
- WHEN a cache entry passes its lifetime THEN the reader SHALL treat it as a miss. [RTE-20]

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| RTE-01 | P1: Manage tenant configuration and defaults | Specify | Pending |
| RTE-02 | P1: Manage tenant configuration and defaults | Specify | Pending |
| RTE-03 | P1: Manage tenant configuration and defaults | Specify | Pending |
| RTE-04 | P1: Manage tenant configuration and defaults | Specify | Pending |
| RTE-05 | P1: Manage tenant configuration and defaults | Specify | Pending |
| RTE-06 | P1: Manage tenant configuration and defaults | Specify | Pending |
| RTE-07 | P1: Manage tenant configuration and defaults | Specify | Pending |
| RTE-08 | P1: Resolve the provider | Specify | Pending |
| RTE-09 | P1: Resolve the provider | Specify | Pending |
| RTE-10 | P1: Resolve the provider | Specify | Pending |
| RTE-11 | P1: Resolve the provider | Specify | Pending |
| RTE-12 | P1: Resolve the provider | Specify | Pending |
| RTE-13 | P1: Cached configuration with fallback | Specify | Pending |
| RTE-14 | P1: Cached configuration with fallback | Specify | Pending |
| RTE-15 | P1: Cached configuration with fallback | Specify | Pending |
| RTE-16 | P1: Cached configuration with fallback | Specify | Pending |
| RTE-17 | P1: Cached configuration with fallback | Specify | Pending |
| RTE-18 | P2: Routing visibility | Specify | Pending |
| RTE-19 | Edge cases | Specify | Pending |
| RTE-20 | Edge cases | Specify | Pending |

**Coverage:** 20 total, 0 mapped to tasks, 20 unmapped until the Tasks phase.

---

## Success Criteria

- [ ] FC-20 and FC-26 pass.
- [ ] Audit entries exist for every change path.
