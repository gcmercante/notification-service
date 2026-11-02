# ADR-0010: Give each application its own database on a shared PostgreSQL instance, with secrets kept in a secrets store

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-45, D-46, D-59 |
| Decision date | 2026-10-22 |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | Decisions confirmed in the HLD revision 14 review (D-45, D-46) and the item-by-item review of revision 18 (D-59); HLD [§2.3](../high-level-design.md#23-decision-log) intro paragraph. This record itself is not yet reviewed. Record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-03, C-51, C-52, C-65 |
| HLD sections | [§4.5](../high-level-design.md#45-persistence-boundary), [§6.1](../high-level-design.md#61-ownership-table-confirmed-d-58-d-59), [§8.2](../high-level-design.md#82-credentials-and-secrets) |
| Supersedes | — |

## Context

The platform has six applications ([ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md)), and several of them keep state: the API / Gateway (accepted requests, idempotency keys, outbox, integration registry, routing configuration), each channel worker (attempt ledger and outbox), the provider-callbacks app (inbound outbox), and the Delivery-status app (delivery status, the single source of truth). PostgreSQL is the initial database, but alternative SQL or NoSQL stores must stay evaluable, and zero-cost substitution is **not** promised (C-03). CLAUDE.md warns against inferring a database per application unless the architecture supports it, and against multiple sources of truth for delivery status.

Two questions were open before the revision 14 review: the database topology (OQ-12) and how infrastructure credentials reach applications (OQ-26). The applications also handle sensitive values (provider credentials, which the platform alone owns per D-04; broker, database and Redis credentials; service keys; key material for API-key hashing), and there was no rule on where those live versus ordinary configuration. **Open question:** which secrets-store / key-management product to use; no product is chosen.

## Decision

Quoting the canonical wording in [context §8](../architecture-context.md#8-confirmed-decisions):

- **D-45:** "One shared PostgreSQL instance, with a separate database per application." (C-51)
- **D-46:** "Kafka, PostgreSQL (and other infrastructure) credentials are secrets made available through environment variables, to be set up later." (C-52)
- **D-59:** "Data ownership as described in the HLD (§4.5, §6.1) is approved, including the worker attempt ledger and immutable accepted requests. Sensitive values (all credentials and keys) are kept in a secrets store; non-sensitive configuration is kept in environment variables. Secrets may be delivered to applications as environment variables (D-46)." (C-65)

Net position: each application writes only its own database on one shared instance. What each database holds is the table in HLD [§4.5](../high-level-design.md#45-persistence-boundary) and the ownership table in [§6.1](../high-level-design.md#61-ownership-table-confirmed-d-58-d-59). The worker attempt ledger is operational data, not a second source of delivery status. Accepted requests are immutable. D-59 clarifies D-46: the secrets store is where sensitive values are kept, and environment variables are how they may be delivered. Non-sensitive configuration goes in plain environment variables. The product choice is deferred (open, raised by D-59 in HLD §2.3).

Not decided here: the Redis routing cache (D-44) and provider-credential ownership (D-04), both in [ADR-0003](0003-route-tenant-notifications-to-configured-or-default-provider.md). Also not decided here: the **Proposed** items in HLD §8.1 and §8.2, namely per-application credentials with no sharing, broker ACLs, and database users limited to their own database.

## Alternatives considered

Not recorded when the decision was made. HLD [§10](../high-level-design.md#10-trade-offs) lists only the chosen option and its trade-offs. No alternative topology or secrets mechanism is labelled Rejected.

(retrospective) Two options a future reader might ask about, which were not evaluated in the HLD:
- **One database with a schema per application** would allow cross-schema transactions, but it also allows the cross-application table coupling that D-45 rules out.
- **A separate PostgreSQL instance per application** would remove the shared failure domain, at the cost of operating several instances.

## Consequences

- **Positive:** clear write ownership, and no coupling between applications through tables (§10). Each application's store can be replaced on its own, which supports C-03, though a replacement must still provide the guarantees listed in §4.5 through its own mechanisms. There is one instance to operate. Secrets stay out of code, configuration files, the routing database, messages and logs (§8.2).
- **Negative / accepted risks:**
  - The shared instance is a **shared failure and capacity domain**: an outage or a heavy query affects every application (§4.5, §10).
  - There are no cross-database joins or transactions. Data moves through messages or explicit interfaces. This is why P-04 option B (the API reading status tables directly) is **Rejected** ([§5.6](../high-level-design.md#p-04-confirmed-by-d-56-the-api-serves-status-reads-by-querying-the-delivery-status-app)).
  - The one proposed cross-database read is the routing read-only fallback used when Redis misses or is down. HLD [P-02b](../high-level-design.md#p-02b-confirmed-by-d-44-routing-configuration-is-served-from-a-redis-cache) proposes a read-only grant on the API / Gateway's routing tables over an internal read endpoint. That choice is still Proposed and belongs to ADR-0003.
  - Secrets delivered as environment variables usually need a restart or redeploy to rotate, so rotation is planned rather than instant (§8.2).
- **Follow-up:**
  - Choose the secrets-store product. It also covers key management for D-63 encryption keys ([ADR-0011](0011-protect-personal-data-with-encryption-and-bounded-retention.md)). It has no OQ-nn in HLD §11.2.
  - Owner review of the §8.1/§8.2 Proposed items listed above.
  - Revisit the topology if shared-instance contention or blast radius becomes a problem.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| Each application's database user cannot read or write another application's database, except the routing read-only fallback (P-02b) | §14 — FC-21 (D-45 database isolation) | Planned |
| Only workers and the callbacks app can read provider secrets; no secrets in logs or messages | §14 — FC-25 (QS-11 credential confinement) | Planned |
| Secrets are absent from code and configuration files; non-sensitive configuration is kept in environment variables | Gap — no check exists (FC-25 scans only logs and messages) | Gap — no check exists |
| Accepted requests are immutable after acceptance | Gap — no check exists | Gap — no check exists |
| The worker attempt ledger never decides or exposes delivery status | Gap — no check exists (FC-16 covers only the ledger's atomicity with the outbox) | Gap — no check exists |

FC-21 and FC-25 are approved rows (D-65), not *(Proposed)* ones.

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-45, D-46, D-59); [context §8](../architecture-context.md#8-confirmed-decisions). Constraints: HLD [§2.1](../high-level-design.md#21-confirmed-constraints). Resolved questions: OQ-12, OQ-26 ([§11.1](../high-level-design.md#11-open-questions)).
- Related to [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md) (persistence ports, D-54), [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md) (outboxes held in each database, D-37, D-61), [ADR-0003](0003-route-tenant-notifications-to-configured-or-default-provider.md) (D-04, D-44 Redis cache, read-only fallback), [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md) (status store and reads, D-33, D-56), [ADR-0008](0008-authenticate-callers-with-api-keys-and-defer-oidc-oauth.md) (service keys and API-key pepper held as secrets, D-53, D-64), [ADR-0011](0011-protect-personal-data-with-encryption-and-bounded-retention.md) (key-encryption key in the secrets store, D-63; retention, D-38).
- Logical data model and per-store guarantees: not yet produced (HLD [§13](../high-level-design.md#13-follow-up-artifacts)).

## Amendments

None.
