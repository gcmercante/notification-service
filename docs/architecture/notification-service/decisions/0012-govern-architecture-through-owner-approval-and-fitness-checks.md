# ADR-0012: Govern architecture through the project owner and approved fitness checks

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-01, D-34, D-65, D-66 |
| Decision date | 2026-10-22 (D-01, D-34, D-65); 2026-11-02 (D-66) |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | Decisions: HLD [§2.3](../high-level-design.md#23-decision-log) — D-01 confirmed during review of revision 1, D-34 during review of revision 13, D-65 during the item-by-item review of revision 18, D-66 during the ADR review of 2026-11-02 (HLD revision 30). This record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-10, C-40, C-71 |
| HLD sections | §0, §2.1, §2.2, §2.3, §9, §11, §14 |
| Supersedes | — |

## Context

Every other ADR depends on three governance questions: who may approve an architecture decision, how quality is judged before any numbers exist, and how a confirmed decision is shown to be followed once code exists.

- **Approval.** CLAUDE.md requires that proposals, assumptions, and unverified behaviour are never presented as accepted decisions, and that an ADR is not marked accepted without evidence of approval. The HLD labels every statement Confirmed, Proposed, Assumption, Open question, or Rejected ([§0](../high-level-design.md#0-how-to-read-this-document)). Before D-01, who approved was an open question (OQ-01, [§11.1](../high-level-design.md#111-resolved-in-revision-2)).
- **Quality targets.** No quantitative targets have been supplied (**Confirmed**, context [§6](../architecture-context.md#6-decisions-not-yet-established)). The quality scenarios QS-01 to QS-11 ([§2.2](../high-level-design.md#22-quality-characteristics-as-scenarios)) state what must be true, but their measures were TBD (OQ-02). The platform has no production load from which to derive targets.
- **Verification.** Many decisions express guarantees (status integrity, tenant isolation, durability, privacy) that silently erode unless something checks them. Nothing is implemented yet.

## Decision

Quoted from context [§8](../architecture-context.md#8-confirmed-decisions) (canonical wording):

- **D-01:** "The project owner is the architecture decision owner and approver." (C-10.)
- **D-34:** "Numeric quality targets are deferred until real load is known; every measure is collected from day one." (C-40; resolves OQ-02.)
- **D-65:** "The automated fitness checks listed in the HLD (§14) are approved, to be built together with the features they protect." (C-71.)

Net position and scope:

- D-01 governs both decisions and ADR records. How it is applied to ADRs (statuses, lifecycle, recording approval) is the Confirmed convention in [`README.md`](README.md) §3 and §6, and is not restated here.
- D-34 defers *numeric* targets only. The measures themselves are required from day one. Alert thresholds other than D-40's are set once targets exist ([§9](../high-level-design.md#9-observability-and-operations)).
- D-65 covers the checks that existed in [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69) when it was confirmed: **FC-01 to FC-26**. FC-27 to FC-31 were added in HLD revision 29 and approved by **D-66** (2026-11-02): "Fitness checks FC-27 to FC-31 in the HLD (§14) are approved, to be built together with the features they protect, as for D-65." Rows added later (for example FC-32 and FC-33 with ADR-0013) need their own owner decision.

## Alternatives considered

Not recorded when the decision was made, for D-01, D-34, or D-65. The HLD lists no options, P-nn variants, or Rejected items for them, and [§10](../high-level-design.md#10-trade-offs) has no row on governance.

The only recorded alternative concerns the *placement* of these decisions, not their substance ([`README.md`](README.md) §7.1, approved as placed under Q-6):

- **Record D-01 only in the ADR README and the HLD, and drop it from the ADR set** — not chosen: kept here because D-01 is a process decision that every ADR relies on.
- **Record D-34 in an observability ADR** — not chosen for now; D-34 may move to, or be refined by, an observability ADR if one is created later.

## Consequences

- **Positive:**
  - One approver and one approval path: nothing is Confirmed without the owner, so the Confirmed/Proposed labels stay meaningful across the HLD, contracts, and ADRs.
  - No invented targets: the design does not commit to numbers that real load may contradict, while the data needed to set them is collected from the start.
  - Confirmed guarantees have named, stable checks (FC IDs) that ADR Confirmation tables cite, and checks are built with the feature rather than retrofitted.
- **Negative / accepted risks:**
  - The owner is a single approval bottleneck; progress on any design question waits for review.
  - Until targets exist, quality scenarios and several checks (for example FC-12 and threshold-based alerts) can show trends but cannot pass or fail against a number. Capacity, SLO, and alert decisions stay provisional.
  - "Collect every measure from day one" adds instrumentation work to every feature, with cardinality and cost risk noted in [§9](../high-level-design.md#9-observability-and-operations).
  - Building checks with features means a decision has no evidence until its feature exists; all Confirmation rows are Planned today.
- **Follow-up:**
  - Owner approval of FC-32 and FC-33 (Proposed with ADR-0013).
  - Define when and by whom numeric targets are set once real load is known; no open question currently tracks this, because OQ-02 is resolved by D-34.
  - Revisit D-34's placement if an observability ADR is created.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| D-01: only the project owner approves decisions and moves an ADR out of Proposed. | Review step: the approval rules in [`README.md`](README.md) §3.2 and §6 (approval evidence in each ADR header). Not an automated check. | Planned (applied at each ADR review) |
| D-34: numeric targets are not set before real load is known. | Review step: §2.2 measures and §9 thresholds stay TBD until an owner decision sets them. | Gap — no check exists |
| D-34: every measure is collected from day one. | FC-12 covers status freshness only. No check verifies that the other measures in §2.2 and §9 are collected. | Partial: FC-12 Planned; otherwise Gap — no check exists |
| D-65: approved fitness checks are built together with the features they protect. | §14 — FC-01 to FC-26, each tracked in the Confirmation table of the ADR that owns the protected decision. | Planned |
| D-66: FC-27 to FC-31 are built together with the features they protect. Rows not yet approved (FC-32, FC-33) are not treated as approved. | §14 — FC-27 to FC-31; FC-32 and FC-33 marked *(Proposed)*. | Planned |

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-01, D-34, D-65); context [§8](../architecture-context.md#8-confirmed-decisions).
- Constraints: HLD [§2.1](../high-level-design.md#21-confirmed-constraints) (C-10, C-40, C-71). Quality scenarios: [§2.2](../high-level-design.md#22-quality-characteristics-as-scenarios). Fitness checks: [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69).
- ADR convention: [`README.md`](README.md) (Confirmed 2026-10-27).
- Related to every other ADR, whose Confirmation tables cite §14: [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md), [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md), [ADR-0003](0003-route-tenant-notifications-to-configured-or-default-provider.md), [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md), [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md), [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md) (D-19 freshness, measured by FC-12), [ADR-0007](0007-ingest-provider-status-by-push-through-callbacks-app.md), [ADR-0008](0008-authenticate-callers-with-api-keys-and-defer-oidc-oauth.md), [ADR-0009](0009-isolate-tenants-and-integrations-and-separate-admin-traffic.md), [ADR-0010](0010-use-a-database-per-application-on-shared-postgresql.md), [ADR-0011](0011-protect-personal-data-with-encryption-and-bounded-retention.md).

## Amendments

- 2026-11-02 — D-69 — "Fitness checks FC-32 and FC-33 in the HLD (§14), which confirm ADR-0013 (D-68), are approved, to be built together with the features they protect, as for D-65 and D-66." Same rule as D-65/D-66, applied to two more rows; this resolves the follow-up "Owner approval of FC-32 and FC-33" above. (README §3.3 rule 4.)
