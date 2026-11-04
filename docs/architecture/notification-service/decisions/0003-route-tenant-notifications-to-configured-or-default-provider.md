# ADR-0003: Route each tenant's notifications per channel to its configured provider, else the channel default

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-03, D-04, D-06, D-09, D-42, D-43, D-44, D-55 |
| Decision date | 2026-10-22 — the date the owner confirmed the D-nn entries |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | Decisions confirmed in the HLD reviews of revision 1 (D-03, D-04), revision 2 (D-06), revision 3 (D-09), revision 14 (D-42, D-43, D-44) and revision 17 (D-55), per the HLD [§2.3](../high-level-design.md#23-decision-log) intro. This record itself has not been reviewed. Record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-04, C-05, C-12, C-13, C-14, C-16, C-19, C-48, C-49, C-50, C-61 |
| HLD sections | [§4.3](../high-level-design.md#43-provider-routing-boundary) (P-02, P-02a, P-02b), [§5.2](../high-level-design.md#52-dispatch-flow-per-channel-worker), [§5.5](../high-level-design.md#55-administration-flow), [§8.2](../high-level-design.md#82-credentials-and-secrets) |
| Supersedes | — |

## Context

No notification provider has been selected yet (C-04). Providers must be addable and replaceable without vendor logic spreading through the platform, and routing must be able to choose a provider based on the customer (C-05). C-05 also says failover, fallback, weighted, cost-based, and availability-based routing are **not** assumed.

The owner had to settle several questions (HLD [§11.1](../high-level-design.md#11-open-questions)): where routing configuration lives and who owns provider credentials (OQ-06), whether a default applies (OQ-07), who administers the configuration (OQ-22), whether routing is per tenant or per integration (OQ-30), what "a configured provider" means across channels (OQ-28, assumptions A-01 to A-03), when a submission with no provider is rejected (OQ-08), how fast configuration changes must take effect (OQ-27), and where routing is resolved (P-02).

Two facts still shape the design. **Open:** the default provider for each channel is not yet defined (C-13). **Open question:** whether tenants need their own sender identities under the platform's accounts, and whether they may learn which provider handled a notification ([OQ-23](../high-level-design.md#11-open-questions)).

## Decision

Quoted from [context §8](../architecture-context.md#8-confirmed-decisions), which is canonical:

- **D-03:** "Once the client is identified, the platform routes to the provider configured for that client in the database. If the client has no configured provider, a default provider is used. The default provider is not yet defined."
- **D-09:** "Provider configuration is per tenant. In D-03, "client" means tenant."
- **D-42:** "Provider configuration is per channel, with at most one configured provider per tenant per channel, and one platform-wide default provider per channel."
- **D-04:** "Provider credentials are owned by the platform only. Clients have credentials to access the platform and nothing else."
- **D-06:** "Routing configuration is managed through administrative endpoints, so that a back-office can be built on them later."
- **D-43:** "A submission is rejected only after the platform has tried to find a valid provider for it (tenant configuration, then default) and found none."
- **D-44:** "How fast routing changes take effect does not matter. Routing configuration can be served from a Redis cache; the database remains its source of truth."
- **D-55:** "The channel worker selects the provider at send time through a separate routing policy. Retries keep the provider chosen for the first attempt. Each attempt records the provider used and whether it came from tenant configuration or the default."

Net position: for tenant *T* and channel *K*, use *T*'s configured provider for *K*. If there is none, use *K*'s platform-wide default. If neither gives a valid provider, reject the submission (resolution rule, HLD §4.3). The default replaces **missing configuration only**. It is never a fallback for a configured provider that is failing. That provider is retried and then fails for good (D-07, recorded in ADR-0004).

Still deferred or only proposed:

- **Not defined:** which provider is the default for each channel (D-03).
- **Proposed:** what makes a provider "valid" (an adapter exists, a platform-owned account exists for the channel, the provider is not disabled; P-02a).
- **Proposed (HLD interpretation):** the API runs the resolution as a pre-check while the worker still resolves at dispatch (P-02a).
- **Proposed:** how Redis is populated and how reads fall back when it misses or is unavailable (P-02b).
- **Proposed:** a routing record holds only a reference to a provider account (P-02).

## Alternatives considered

- **API resolves the provider at acceptance and pins it in the dispatch message (option A)** — Rejected: it ignores configuration changes made between acceptance and dispatch, couples the API to provider configuration, and puts the provider identity on every message. (Source: HLD §4.3 options table; D-55, revision 17 review.)
- **Use the default provider as a fallback when the configured provider fails** — Rejected: a failing provider is retried and then fails for good; the default is never used in its place. (Source: HLD §4.3; OQ-24 resolved by D-07.)
- **Failover, fallback, weighted, cost-based, or availability-based routing** — Not assumed (C-05). The routing port leaves room for them as a different policy implementation later (P-02). They were set aside as out of scope, not evaluated and rejected.
- **Routing per integration instead of per tenant** — Not selected: OQ-30 asked the question and D-09 answered "per tenant". (Source: HLD §11.1.)
- **An ordered list of providers per tenant and channel; a default per group of tenants** — Not selected: A-02 ("no ordered list") and A-03 ("not a per-tenant-group default") were confirmed by D-42. (Source: HLD §4.3.)
- **Read the routing database on every send instead of caching** — Implied by the §10 trade-off ("no database read on each send"). No reason for rejecting it was recorded beyond D-44's statement that change latency does not matter.
- **Tenant-supplied provider credentials (D-04); other places to manage configuration (D-06)** — Not recorded when the decision was made.

## Consequences

- **Positive:**
  - Routing is simple, deterministic, and easy to audit (HLD [§10](../high-level-design.md#10-trade-offs)).
  - Provider logic stays next to the provider call and its account. The worker always uses the current configuration.
  - Clients never handle provider secrets.
  - Retrying with the same provider keeps provider-side deduplication and callback attribution coherent.
  - Recording the provider and its source on each attempt keeps attempts attributable after configuration changes.
- **Negative / accepted risks:**
  - The design gives no resilience against a provider failure (§10).
  - Configuration changes also apply to work already queued, within the cache lifetime.
  - Shared platform accounts mean a shared blast radius and shared quotas across tenants (§8.2, QS-09). Per-provider-account throttling is in D-58 (ADR-0001); its values wait on OQ-11.
  - Redis is a **new technology** to operate, and reads need a fallback for when it is unavailable (§10, P-02b).
  - The proposed fallback needs either a read-only grant on the API / Gateway's routing tables or an internal read endpoint, which crosses the database-per-application boundary of D-45 (ADR-0010).
  - A provider that becomes invalid between submission and dispatch ends `FAILED` with reason `NO_ELIGIBLE_PROVIDER` (D-29, ADR-0005).
  - Until the defaults are defined, a tenant with no configuration for a channel cannot send on that channel.
- **Follow-up:**
  - Define the per-channel defaults (D-03).
  - Answer OQ-23 (sender identities and provider visibility) and OQ-11 (provider-account limits).
  - Get the owner's review of the Proposed parts of P-02, P-02a, and P-02b.
  - Write the administrative OpenAPI contract and the logical data model for routing configuration and defaults (HLD [§13](../high-level-design.md#13-follow-up-artifacts) items 5 and 7).
  - Revisit this ADR if failover or fallback routing is ever approved.

## Confirmation

All checks below are from HLD [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69). None is implemented yet.

| Claim | Check | Evidence state |
|---|---|---|
| Resolution rule: tenant configuration, else the default, else no provider (D-03, D-09) | FC-26 (C-12 / C-13 routing) | Planned |
| At most one provider per tenant per channel; the default is per channel (D-42) | FC-26 does not explicitly cover the per-channel dimension | Gap — no check exists |
| Two integrations of the same tenant resolve to the same provider (D-09, per tenant rather than per integration) | — | Gap — no check exists |
| Rejection only when no valid provider exists; a provider invalidated before dispatch ends `FAILED` / `NO_ELIGIBLE_PROVIDER` (D-43) | FC-19 (D-43 routing pre-check) | Planned |
| Routing still resolves correctly when Redis is unavailable or empty (D-44) | FC-20 (D-44 Redis fallback); FC-21 (only the routing read-only exception crosses databases) | Planned |
| Only workers and the callbacks app can read provider secrets (D-04) | FC-25 (QS-11 credential confinement) | Planned |
| The default is never used as a fallback during retries | FC-24 ("The default provider is never called"; the row is owned by ADR-0004) | Planned |
| Retries keep the first attempt's provider; each attempt records the provider and its source (D-55) | FC-29 (D-55 provider per attempt; approved by D-66) | Planned |
| Provider SDKs stay out of the domain and the routing policy (C-04) | FC-01 (dependency rule; owned by ADR-0001) | Planned |
| Routing configuration is changed only through the administrative endpoints, and each change is written through to the cache (D-06, P-02b) | — (FC-23 covers only admin separation, ADR-0009) | Gap — no check exists |

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-03, D-04, D-06, D-09, D-42, D-43, D-44, D-55); [context §8](../architecture-context.md#8-confirmed-decisions). Constraints: HLD [§2.1](../high-level-design.md#21-confirmed-constraints).
- Related to [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md): routing policy behind a port (D-54), per-provider-account throttling (D-58).
- Related to [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md): same-provider retries; no fallback to the default (D-07, D-10).
- Related to [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md): `FAILED` / `NO_ELIGIBLE_PROVIDER` (D-29).
- Related to [ADR-0009](0009-isolate-tenants-and-integrations-and-separate-admin-traffic.md): administrative traffic separation (D-12); tenant taken from verified credentials.
- Related to [ADR-0010](0010-use-a-database-per-application-on-shared-postgresql.md): database topology (D-45) and the secrets store (D-59). D-44 was paired with D-45 in HLD §13; see [README §7.1](README.md#71-decisions-that-do-not-fit-cleanly).
- Contracts: the administrative OpenAPI contract and the routing data model are not yet produced (HLD §13 items 5 and 7).

## Amendments

None.
