# Integration Access Specification

## Problem Statement

Tenants must reach the platform through credentials that identify exactly one integration, and the platform must derive the tenant itself (D-05, D-47). Administrators need a separate surface to manage those integrations (D-12, D-52). Without this, no request can be attributed, isolated, or limited.

## Goals

- [ ] Every API request resolves to one integration and one tenant, from the registry only.
- [ ] A revoked key stops working within 60 seconds.
- [ ] An integration key never works on the administrative surface, and the reverse.

## Out of Scope

| Feature | Reason |
| ------- | ------ |
| OAuth 2.0 and OIDC | Deferred until an IdP exists (D-47) |
| Delegated access | Not needed for now (D-50) |
| Multiple administrator roles | One role for now (D-12) |
| Back-office UI | Future; endpoints only (D-06) |
| Browser cross-origin support | Every integration is a backend (D-14) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --------------------- | -------------- | --------- | ---------- |
| Admin separation mechanism (§5.5, Proposed) | Separate listener in the API / Gateway, on its own port | The HLD's proposed mechanism; D-12 confirms separation only | n |
| Registry management on the admin surface (§5.5, Proposed) | Yes | D-06 names routing only, but D-31 and D-58 need an admin path for integrations | n |
| First administrator key | A bootstrap command creates one key if none exists and prints it once | Nothing else can authenticate the first administrative call | n |
| Rotation overlap | 24 hours, configurable | HLD §8.1 example value | n |
| Scope set | `submit` and `read-status` for integrations; `admin` for administrators | HLD §8.1 proposed starting set | n |
| Rate limit algorithm and store | Fixed one-minute window per integration, counters in Redis | D-36 sets per-integration limits; HLD names Redis as an option | n |
| No limit configured for an integration | A platform default from configuration applies | An unlimited integration would defeat D-36 | n |
| Rate-limit store outage | Allow the request and count the event | Availability of acceptance outranks a temporary limit gap | n |
| HTTP status codes | 401 unauthenticated, 403 forbidden scope, 429 limited, 404 unknown resource | Standard meanings; final in the OpenAPI contract | n |

**Open questions:** none - all resolved or logged above.

---

## User Stories

### P1: Administrator authentication ⭐ MVP

**User Story**: As an administrator, I want an administrator API key valid only on the administrative surface so that platform control stays separate from integration traffic (D-12, D-52).

**Why P1**: Nothing else in this feature can be managed without it.

**Acceptance Criteria**:
1. WHEN the bootstrap command runs and no administrator key exists THEN the system SHALL create one and display it exactly once. [ACC-01]
2. IF the bootstrap command runs and an active administrator key exists THEN the system SHALL refuse and create no key. [ACC-02]
3. IF a request on the administrative surface has no valid administrator key THEN the system SHALL respond 401. [ACC-03]
4. IF an administrator key is presented on an integration endpoint THEN the system SHALL respond 401. [ACC-04]
5. The administrative listener SHALL be separate from the integration listener and SHALL enforce an explicit administrator permission check. [ACC-05]

**Independent Test**: Run bootstrap twice, then call both listeners with the resulting key.

---

### P1: Integration registry and key issuance ⭐ MVP

**User Story**: As an administrator, I want to create integrations bound to a tenant so that each independently managed integration has one credential (D-05, D-31).

**Why P1**: Integrations cannot call the platform otherwise.

**Acceptance Criteria**:
1. WHEN an administrator creates an integration with a tenant and scopes THEN the system SHALL store it with credential type API key and return its generated key exactly once. [ACC-06]
2. The system SHALL store API keys only as hashes computed with a secret pepper. [ACC-07]
3. The system SHALL keep a non-secret key prefix for identification in logs and administrative responses. [ACC-08]
4. WHEN an administrator reads an integration THEN the system SHALL return its prefix and never the key or its hash. [ACC-09]
5. The registry SHALL hold exactly one credential type per integration. [ACC-10]
6. WHEN an administrator changes an integration THEN the system SHALL write an audit entry with actor, time, and old and new values. [ACC-11]

**Independent Test**: Create an integration, inspect its stored row for a plain key, and read it back through the admin API.

---

### P1: Authenticate and resolve the tenant ⭐ MVP

**User Story**: As a platform owner, I want the tenant derived only from the verified key so that a caller can never act as another tenant (D-05, FC-10).

**Why P1**: It is the core isolation control.

**Acceptance Criteria**:
1. WHEN an integration request carries a valid key in the request header THEN the system SHALL resolve its integration and tenant from the registry. [ACC-12]
2. IF a request supplies a tenant identifier in its body, header, or query THEN the system SHALL ignore it. [ACC-13]
3. IF a key is missing, unknown, or revoked THEN the system SHALL respond 401 without revealing which. [ACC-14]
4. IF a key is presented in a URL query string THEN the system SHALL respond 401 and SHALL not log the key. [ACC-15]
5. IF an integration lacks the scope an endpoint requires THEN the system SHALL respond 403. [ACC-16]

**Independent Test**: Call a protected test endpoint with a valid key plus a forged tenant field, and assert the resolved tenant.

---

### P1: Revocation and rotation ⭐ MVP

**User Story**: As an administrator, I want to revoke and rotate keys so that a leaked key stops working quickly (D-32, D-64).

**Why P1**: API keys are long-lived static secrets, so these are the main mitigations.

**Acceptance Criteria**:
1. WHEN an administrator revokes a key or disables an integration THEN the system SHALL refuse that key within 60 seconds. [ACC-17]
2. The registry cache lifetime SHALL be configured at 60 seconds or less, and the application SHALL refuse to start with a larger value. [ACC-18]
3. WHILE a rotation overlap is active the system SHALL accept both the old and the new key. [ACC-19]
4. WHEN a rotation overlap ends THEN the system SHALL accept only the new key. [ACC-20]

**Independent Test**: Revoke a key with a test clock and assert refusal at the cache boundary. Rotate and assert both windows.

---

### P1: Per-integration rate limits ⭐ MVP

**User Story**: As an administrator, I want a limit per integration so that one integration cannot exhaust shared provider accounts (D-36, FC-27).

**Why P1**: D-36 requires limits from the start.

**Acceptance Criteria**:
1. IF an integration exceeds its limit in the current window THEN the system SHALL respond 429 with a `Retry-After` header. [ACC-21]
2. WHILE one integration is limited the system SHALL keep serving other integrations of the same tenant. [ACC-22]
3. WHEN an administrator changes a limit THEN the system SHALL apply the new value within 60 seconds. [ACC-23]

**Independent Test**: Exhaust one integration's limit, then call with a second integration of the same tenant.

---

### P1: Internal service authentication ⭐ MVP

**User Story**: As a platform owner, I want internal interfaces to require a per-caller service key so that they are not reachable by other callers (D-53, FC-22).

**Why P1**: The status query interface in feature 5 depends on this guard.

**Acceptance Criteria**:
1. IF an internal interface receives a call without a valid service key for an allowed caller THEN the system SHALL respond 401. [ACC-24]
2. The system SHALL read service keys from environment variables and SHALL never log them. [ACC-25]

**Independent Test**: Call a guarded test interface with no key, a wrong key, and the right key.

---

## Implicit-Requirement Sweep

| Dimension | Resolution |
| --------- | ---------- |
| Input validation & bounds | ACC-13, ACC-15 |
| Failure / partial-failure states | ACC-14, ACC-26 |
| Idempotency / retry / duplicates | N/A because administrative creation is not retried automatically; a duplicate creates a separate integration the administrator can disable |
| Auth boundaries & rate limits | ACC-03 to ACC-05, ACC-12 to ACC-16, ACC-21 to ACC-25 |
| Concurrency / ordering | ACC-27 |
| Data lifecycle / expiry | ACC-17 to ACC-20 |
| Observability | ACC-28 |
| External-dependency failure | ACC-26 |
| State-transition integrity | ACC-19, ACC-20 |

## Edge Cases

- IF the rate-limit store is unavailable THEN the system SHALL allow the request and increment a limiter-outage counter. [ACC-26]
- WHEN concurrent requests from one integration cross its limit THEN the system SHALL admit no more than the limit plus the number of API instances in that window. [ACC-27]
- WHEN authentication fails or a limit is hit THEN the system SHALL increment a counter by reason, labelled with the key prefix when known and never with the key. [ACC-28]

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| -------------- | ----- | ----- | ------ |
| ACC-01 | P1: Administrator authentication | Specify | Pending |
| ACC-02 | P1: Administrator authentication | Specify | Pending |
| ACC-03 | P1: Administrator authentication | Specify | Pending |
| ACC-04 | P1: Administrator authentication | Specify | Pending |
| ACC-05 | P1: Administrator authentication | Specify | Pending |
| ACC-06 | P1: Integration registry and key issuance | Specify | Pending |
| ACC-07 | P1: Integration registry and key issuance | Specify | Pending |
| ACC-08 | P1: Integration registry and key issuance | Specify | Pending |
| ACC-09 | P1: Integration registry and key issuance | Specify | Pending |
| ACC-10 | P1: Integration registry and key issuance | Specify | Pending |
| ACC-11 | P1: Integration registry and key issuance | Specify | Pending |
| ACC-12 | P1: Authenticate and resolve the tenant | Specify | Pending |
| ACC-13 | P1: Authenticate and resolve the tenant | Specify | Pending |
| ACC-14 | P1: Authenticate and resolve the tenant | Specify | Pending |
| ACC-15 | P1: Authenticate and resolve the tenant | Specify | Pending |
| ACC-16 | P1: Authenticate and resolve the tenant | Specify | Pending |
| ACC-17 | P1: Revocation and rotation | Specify | Pending |
| ACC-18 | P1: Revocation and rotation | Specify | Pending |
| ACC-19 | P1: Revocation and rotation | Specify | Pending |
| ACC-20 | P1: Revocation and rotation | Specify | Pending |
| ACC-21 | P1: Per-integration rate limits | Specify | Pending |
| ACC-22 | P1: Per-integration rate limits | Specify | Pending |
| ACC-23 | P1: Per-integration rate limits | Specify | Pending |
| ACC-24 | P1: Internal service authentication | Specify | Pending |
| ACC-25 | P1: Internal service authentication | Specify | Pending |
| ACC-26 | Edge cases | Specify | Pending |
| ACC-27 | Edge cases | Specify | Pending |
| ACC-28 | Edge cases | Specify | Pending |

**Coverage:** 28 total, 0 mapped to tasks, 28 unmapped until the Tasks phase.

---

## Success Criteria

- [ ] FC-03 (API-key part), FC-10, FC-14, FC-22, FC-23 and FC-27 pass.
- [ ] No plain key appears in the database or captured logs.
