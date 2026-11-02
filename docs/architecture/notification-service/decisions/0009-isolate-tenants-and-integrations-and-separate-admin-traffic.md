# ADR-0009: Isolate tenants and integrations, and separate administrative traffic

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-05, D-08, D-12, D-13, D-14, D-36 |
| Decision date | 2026-10-22 |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | Decisions confirmed in the HLD review rounds listed in [HLD §2.3](../high-level-design.md#23-decision-log): D-05 in the revision 2 review; D-08, D-12, D-13 in the revision 3 review; D-14 in the revision 4 review, clarified in the revision 5 review; D-36 in the revision 13 review. This record itself is unreviewed. Record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-15, C-18, C-22, C-23, C-42 |
| HLD sections | [§2.2](../high-level-design.md#22-quality-characteristics-as-scenarios) (QS-09, QS-10), [§2.4](../high-level-design.md#24-terms), [§5.5](../high-level-design.md#55-administration-flow), [§8.1](../high-level-design.md#81-identity-and-access), [§8.3](../high-level-design.md#83-callbacks-tenancy-and-personal-data), [§10](../high-level-design.md#10-trade-offs) |
| Supersedes | — |

## Context

The platform serves many tenants (customers). A tenant can run several independently managed integrations, and every tenant's traffic is sent through platform-owned provider accounts (C-14). Revision 2 of the HLD used "client" for both ideas, which made it unclear what a credential identifies, what data a caller may see, and who may change routing ([§2.4](../high-level-design.md#24-terms)).

Forces:

- **Isolation (QS-10, High).** A caller of tenant *A* must never submit as, read, or influence tenant *B*'s notifications, status, or routing.
- **Shared provider budget (QS-09, C-14).** Every integration routed to a provider spends the same platform account, so one integration's burst or leaked credential affects others.
- **Administrative power.** Administrators change routing configuration (D-06, ADR-0003) and replay dead letters (D-39, ADR-0004). These operations must not be reachable with integration credentials.
- **Caller nature.** D-13 (revision 3 review) required designing for frontend integrations as well as backend services. That opened OQ-34 to OQ-36 and quality scenario QS-12 (abuse containment for frontend integrations). D-14 (revision 4 review) narrowed it, and the revision 5 clarification removed the apparent conflict (I-19).
- **Credential mechanism (Confirmed, D-47).** There is no identity provider for now; integrations use platform-issued API keys. D-05 is worded in OAuth terms. Per I-21, resolved by D-31, it reads as **"one credential per integration"**, either an OAuth client or an API key, never both. The mechanisms are recorded in [ADR-0008](0008-authenticate-callers-with-api-keys-and-defer-oidc-oauth.md), not here.

## Decision

The decision log wording ([context §8](../architecture-context.md#8-confirmed-decisions)) is quoted below.

1. **Integration identity, separate from tenant isolation (D-05).** "One OAuth client per independently managed customer integration. The platform backend controls the client-to-tenant mapping. Scopes are least-privilege. This separates credential identity from customer data isolation, and the platform never trusts tenant identifiers supplied by callers." Under D-31 and D-47, "OAuth client" reads as one credential per integration (an API key for now).
2. **Visibility per integration (D-08).** "An integration can see only the notifications it submitted, never those of other integrations, even within the same tenant." The status-read rule that applies this, D-16, is recorded in [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md).
3. **Separate administrative traffic (D-12).** "Administrative traffic is separated from integration traffic. There is one administrator role for now."
4. **Every caller is a backend (D-13 narrowed by D-14).**
   - D-13: "Integrations include both frontend applications and backend services. It must not be assumed that only administrators are human users of the API."
   - D-14: "Assume every connection to the platform comes from a backend service; the platform only sends notifications. This narrows D-13: tenants' products may have frontends, but those reach the platform only through the tenant's backend."
   - Revision 5 clarification: "the platform does not need to care whether a client is a backend or a frontend; every integration is treated as a backend service. 'We just send notifications' describes the platform's role and does not exclude status reads (D-16)."
   - **Net position:** every integration is treated as a backend service that keeps its credential server-side. The platform neither checks nor designs for the caller's nature. D-13 stays in the log only as history.
5. **Per-integration rate limits (D-36).** "Rate limits per integration from the start, with values set by administrators." This is a protection control rather than an identity rule. It is placed here by the owner's approval of the grouping (README §7.1).

**Not decided here.** The mechanism for D-12 is **Proposed**: a separate listener or host in the API / Gateway codebase, with its own network policy, audience, guards, and contract ([§5.5](../high-level-design.md#55-administration-flow)). These are also **Proposed**: the starting scope set, cross-integration visibility for administrators, managing the integration registry through the administrative endpoints (D-06 covers only routing configuration), and quotas beyond D-36's rate limits ([§8.1](../high-level-design.md#81-identity-and-access)). Rate-limit values, and whether limits are per channel or per operation, are not specified.

## Alternatives considered

- **One credential per tenant, shared by its integrations.** *(Retrospective.)* No HLD section lists this as an option. D-05 (which answered OQ-21) excludes it, and §8.1 and §10 give the reason: separate credentials can be issued, rotated, and revoked one integration at a time ([§8.1](../high-level-design.md#81-identity-and-access), [§10](../high-level-design.md#10-trade-offs)).
- **Accept a tenant identifier from the caller (body, header, query, or a custom token claim).** Rejected by D-05 and D-28: the tenant comes only from the platform's integration registry ([§8.1](../high-level-design.md#81-identity-and-access)).
- **Tenant-wide visibility across integrations (OQ-29).** Rejected by D-08.
- **Designing for frontend integrations (D-13 as read in revision 4).** This meant browser or device callers, frontend end users as OIDC users, and abuse containment (QS-12). It was narrowed by D-14: OQ-34 to OQ-36 became not applicable and QS-12 was retired ([§2.2](../high-level-design.md#22-quality-characteristics-as-scenarios), I-16, I-19).
- **Administrative endpoints in a separate deployable.** Deferred, not rejected. This is a mechanism option under D-12. Moving them later would not change the contract, and the move is worth it if the attack surface or a back-office's release cadence justifies it ([§5.5](../high-level-design.md#55-administration-flow)).
- **Not separating administrative traffic, or adding several administrator roles.** Not recorded when the decision was made.
- **Rate limits per tenant only, or no limits at first (D-36).** Not recorded when the decision was made. *(Retrospective:)* per-tenant limits alone would let one integration exhaust its tenant's allowance, contrary to D-08's per-integration unit.

## Consequences

- **Positive:**
  - Credentials are revocable per integration without affecting the tenant's other integrations.
  - Moving or disabling an integration is a change on the platform side.
  - A forged tenant identifier has no effect.
  - A foreign notification is indistinguishable from an unknown one (D-56).
  - Integration credentials never reach administrative operations.
  - Treating every caller as a backend keeps a single, simpler identity model.
  - Rate limits contain a leaked or misbehaving integration.
- **Negative / accepted risks:**
  - The integration registry is on every request's path (cached for 60 s or less, D-32), and it is one more platform-owned data set to administer ([§10](../high-level-design.md#10-trade-offs)).
  - **Accepted risk (D-14):** a credential that a tenant puts in a frontend is exposed. The platform treats it as a leaked credential, contained by rate limits and revocation, and does not design for it ([§8.1](../high-level-design.md#81-identity-and-access)).
  - The administrative surface sits next to public traffic unless it is exposed separately ([§10](../high-level-design.md#10-trade-offs)).
  - Per-integration limits do not by themselves bound a tenant with many integrations, or protect a shared provider quota (QS-09). Its measure is still TBD.
  - Downstream workers trust the tenant and integration IDs on internal messages, which relies on the proposed broker ACLs ([§8.1](../high-level-design.md#81-identity-and-access) "Edge only").
- **Follow-up:**
  - No OQ-nn remains open under these decisions. Related open items are OQ-11 (provider-account limits, which feed the shared-quota side of QS-09) and OQ-23.
  - Dependent artifacts (HLD [§13](../high-level-design.md#13-follow-up-artifacts) items 5 and 6): the integration-facing and administrative OpenAPI contracts, and the identity and access design note with its leaked-credential threat model.
  - **Revisit trigger:** a requirement for direct frontend or end-user callers would reopen D-14. Several administrator roles or a back-office would revisit D-12.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| Tenant derived only from the registry. Caller-supplied tenant ignored. Cross-tenant access denied. Integration *X* cannot read integration *Y*'s notifications in the same tenant (D-05, D-08) | §14 — FC-10 (QS-10 tenant isolation) | Planned |
| Another integration's or tenant's notification reads as unknown (D-08, with D-16) | §14 — FC-11 (D-08 / D-16 status reads) | Planned |
| Administrative endpoints unreachable from the integration ingress, and integration credentials rejected on them (D-12) | §14 — FC-23 (D-12 separation); also FC-10 (admin-denial case) and FC-22 (ADR-0008, interim keys) | Planned |
| Per-integration rate limits set by administrators are enforced, without affecting sibling integrations (D-36) | §14 — FC-27 (D-36 rate limits; approved by D-66). | Planned |
| Least-privilege scopes per integration (D-05) | Gap — no check exists | Gap — no check exists |
| Single administrator role, enforced as an explicit permission check (D-12) | Gap — no check exists | Gap — no check exists |
| Every integration treated as a backend; no caller-type branching (D-14) | Gap — no check exists (a design-review step may suffice) | Gap — no check exists |

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-05, D-08, D-12, D-13, D-14, D-36); [context §8](../architecture-context.md#8-confirmed-decisions), including the clarification of D-14.
- Inconsistencies: HLD [§12](../high-level-design.md#12-inconsistencies-and-missing-information) I-16, I-19, I-21.
- Related to [ADR-0008](0008-authenticate-callers-with-api-keys-and-defer-oidc-oauth.md): credential mechanisms (D-28, D-31, D-32, D-47, D-51 to D-53, D-64).
- Related to [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md): status reads (D-16, D-56).
- Related to [ADR-0003](0003-route-tenant-notifications-to-configured-or-default-provider.md): administrative routing configuration (D-06) and platform-owned provider credentials (D-04).
- Related to [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md): administrator DLQ replay (D-39).
- Contracts: the integration-facing and administrative OpenAPI contracts, not yet produced (HLD §13 item 5).

## Amendments

None.
