# Architecture Decision Records — Notification Platform

> **Status:** **Confirmed** by the project owner (D-01) on 2026-10-27, in full: §1–§7 and the answers to Q-1 to Q-6 in §8. ADR-0001 to ADR-0013 were written on 2026-11-02 and **accepted** by the project owner the same day. D-66 to D-69 (2026-11-02) are recorded in ADR-0012 (D-66; D-69 as an amendment), ADR-0004 (D-67), and ADR-0013 (D-68).
> **Resolves (when approved):** HLD [§12](../high-level-design.md#12-inconsistencies-and-missing-information) I-12 and the first item of HLD [§13](../high-level-design.md#13-follow-up-artifacts).
> **Inputs:** [`CLAUDE.md`](../../../../CLAUDE.md) ("Architecture Decisions and Unknowns"), [`architecture-context.md`](../architecture-context.md) §8, [`high-level-design.md`](../high-level-design.md) §0, §2.1, §2.3, §13, §14.

This directory holds the Architecture Decision Records (ADRs) for the notification platform. An ADR explains **why** a consequential decision was made: its context, the alternatives, the consequences, and how the decision is verified. It does not replace the decision log; see [§4](#4-traceability-and-sources-of-truth).

---

## 1. Layout and file naming

```text
docs/architecture/notification-service/decisions/
├── README.md                                  # this convention + the ADR index
├── 0001-<imperative-slug>.md
├── 0002-<imperative-slug>.md
└── ...
```

- **Flat directory.** No subfolders by status or topic. Status lives in the record, so status changes never move or rename a file.
- **Identifier:** `ADR-NNNN`, four-digit, zero-padded, sequential across the whole platform (not per application or per topic). The file name starts with the same number.
- **Numbers are never reused or renumbered.** A rejected or withdrawn ADR keeps its number. Gaps are acceptable.
- **Slug:** lowercase kebab-case, a present-tense imperative verb phrase of about 3–8 words, ASCII only. Examples of the *form* (not proposed ADRs): `0007-use-outbox-for-durable-acceptance.md`, not `0007-outbox.md` or `0007-decided-outbox.md`.
- **Language:** English, matching the HLD and context documents (I-10).
- **Template:** embedded in [§2](#2-adr-template) rather than kept in a separate file, so the convention has a single file and no template can be mistaken for a record.
- **`ADR-NNNN` is distinct from the HLD identifiers** (`D-nn`, `C-nn`, `P-nn`, `OQ-nn`, `QS-nn`, `I-nn`). ADRs cite those identifiers; they never re-number or re-label them.

## 2. ADR template

A lightweight Nygard-style record with the MADR "alternatives" and "confirmation" sections added. Copy everything inside the fence into a new file.

```markdown
# ADR-NNNN: <Imperative title>

| Field | Value |
|---|---|
| Status | Proposed \| Accepted \| Rejected \| Superseded by ADR-NNNN \| Deprecated |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-nn, D-nn, … (or "none yet" for a proposal; cite P-nn / OQ-nn instead) |
| Decision date | YYYY-MM-DD — the date the owner confirmed the D-nn entries |
| Record approved | YYYY-MM-DD, by the project owner — or "pending" while Proposed |
| Approval evidence | Where approval is recorded (e.g. "HLD revision 18 review, decision log §2.3") |
| Constraints | C-nn, … |
| HLD sections | §x.y, … |
| Supersedes | ADR-NNNN (or —) |

## Context

The forces at play: the problem, the requirements and constraints (cite C-nn), and
what was unknown. State facts with the CLAUDE.md labels where it matters:
Confirmed, Proposed, Open question, Assumption.

## Decision

The decision in a few sentences, citing each D-nn it records. Use the wording of
the decision log; do not restate a decision more broadly or more narrowly than
the owner confirmed it. If the decision is partly deferred, say which part and
cite the D-nn / OQ-nn that defers it.

## Alternatives considered

- **<Option>** — Rejected: <reason>. (Source: HLD §x.y / owner review rev N.)
- …

Only list alternatives that were actually considered (HLD options, items labelled
Rejected, owner review). If none were recorded, write "Not recorded when the
decision was made." Alternatives analysed after the fact are labelled
"(retrospective)".

## Consequences

- **Positive:** …
- **Negative / accepted risks:** …
- **Follow-up:** open questions left open (OQ-nn), dependent artifacts, revisit triggers.

## Confirmation

How we know the decision is being followed. Link each claim to an HLD §14 fitness
check by its stable ID (e.g. "FC-13 — D-35 idempotency") or to a review step.

| Claim | Check | Evidence state |
|---|---|---|
| … | FC-nn | Planned \| Implemented (link to test/CI job) \| Gap — no check exists |

## Links

- Decision log: HLD §2.3 (D-nn …); context §8.
- Related ADRs: `Refines ADR-NNNN`, `Refined by ADR-NNNN`, `Supersedes ADR-NNNN`,
  `Superseded by ADR-NNNN`, `Related to ADR-NNNN`.
- Contracts / diagrams / sequence diagrams, as they are produced.

## Amendments

(Accepted records only; see README §3.3.) `YYYY-MM-DD — D-nn — <one-line change>`.
```

Keep an ADR short: typically one to two pages. Flow walkthroughs, payloads, schemas, and class details belong in the HLD or in focused contract documents, linked from **Links**.

## 3. Status values and lifecycle

### 3.1 Statuses

| ADR status | Meaning | CLAUDE.md label |
|---|---|---|
| **Proposed** | Drafted, awaiting the owner's review. A proposed ADR may record decisions that are already Confirmed in the log (the *record* is unreviewed) or a recommendation that is not yet decided (the *decision* is unreviewed). | Proposed |
| **Accepted** | The owner approved both the decision and this record of it. | Confirmed |
| **Rejected** | The owner reviewed the proposal and did not adopt it. Kept, with its number and the reason. | Rejected |
| **Superseded by ADR-NNNN** | Replaced by a later accepted ADR. Kept unchanged except for the status line and links. | (historical) |
| **Deprecated** | No longer applies and has no successor (for example, the capability was removed). Reason and date recorded. | (historical) |

**Confirmed (Q-2, 2026-10-27):** **Rejected** is a status, in addition to the four originally requested, because CLAUDE.md treats rejected options as a first-class label and a reviewed-but-declined proposal must stay findable.

### 3.2 Lifecycle

```text
Proposed ──► Accepted ──► Superseded by ADR-NNNN
    │            └──────► Deprecated
    └──────► Rejected
```

- Only the project owner moves an ADR out of **Proposed** (D-01). An agent or contributor never marks an ADR Accepted, Rejected, or Deprecated without evidence of the owner's approval, recorded in the header ([§6](#6-recording-approval)).
- **Accepted means the decision is approved, not that it is implemented.** Implementation evidence lives in the **Confirmation** table, whose rows move from *Planned* to *Implemented* as the §14 checks are built (D-65).

### 3.3 Changing an accepted decision

1. **Every change in substance starts as a new owner decision `D-nn`** in the decision log (context §8 and HLD §2.3). An ADR never changes a decision by itself.
2. **Structural change** (a different mechanism, boundary, owner, technology, or guarantee): write a **new ADR** with `Supersedes: ADR-NNNN`. In the old ADR, change only the status line to `Superseded by ADR-NNNN` and add the link. Its context, decision, and rationale stay as they were.
3. **Narrowing or completing a decision** (for example, resolving a deferred part such as timeouts, OQ-16): write a new ADR that **refines** the old one (`Refines ADR-NNNN`); the old one stays Accepted and gains a `Refined by` link.
4. **Parameter-only change** (a value such as a retry count, a TTL, a retention period, or an alert threshold, with the mechanism unchanged): add a dated line under **Amendments** in the existing ADR, citing the new `D-nn`. No new ADR. This is a deliberate exception to strict immutability (**Confirmed**, Q-4, 2026-10-27).
5. **Editorial fixes** (typos, broken links, adding a link to a newly produced contract or test) are allowed at any time and need no D-nn.

## 4. Traceability and sources of truth

The goal is that each fact has exactly one owner, consistent with CLAUDE.md's "Avoid competing sources of truth".

| Fact | Owner (single source of truth) | What the ADR does |
|---|---|---|
| **That** something was decided, and its exact wording | The decision log. **Confirmed (Q-3, 2026-10-27):** context §8 is canonical for the decision text; HLD §2.3 records what each D-nn resolves and raises. Where the two are worded differently, context §8 wins. | Cites the D-nn and quotes its context §8 wording. Never paraphrases it into a different scope. |
| **Why**: context, alternatives, consequences, verification plan | The ADR | Owns this. The HLD links to the ADR instead of repeating the rationale at length. |
| Constraints derived from decisions | HLD §2.1 (`C-nn`) | Cites the C-nn it relies on. |
| Unresolved questions | HLD §11 (`OQ-nn`) | Lists the OQ-nn it leaves open under **Consequences → Follow-up**. Never resolves an OQ itself. |
| Unapproved recommendations | HLD (`P-nn`) | A Proposed ADR may present a P-nn in decision form; on approval the owner's new D-nn is added to the log and the ADR becomes Accepted. |
| Verification checks | HLD §14 | **Confirmation** links to §14 rows. If a claim has no §14 row, the ADR says "Gap — no check exists" rather than inventing a check. |
| Runtime behaviour, flows, boundaries | HLD §4–§9 | Links to the sections; does not copy them. |
| Contracts, schemas, data model | Focused documents under `docs/architecture/notification-service/` (HLD §13) | Links to them once they exist. |
| Feature requirements, tasks, verification runs | `.specs/` (TLC Spec-Driven) | Not in ADRs; `.specs/` design notes link to ADRs. |

Rules:

- **Each D-nn is recorded in exactly one ADR.** An ADR may *mention* another ADR's D-nn under Links, but only the owning ADR lists it in "Decisions recorded".
- **Narrowed or deferred D-nn stay visible.** When the log narrows a decision (D-13 by D-14; D-22 by D-23/D-24; D-07 by D-10/D-15) or defers part of one (D-02, D-28, D-31, D-32 by D-47), the ADR records both IDs and states the net position, so the history is not lost.
- **Back-links (Confirmed, Q-5, 2026-10-27; to be done in step 2):** add an "ADR" column to HLD §2.3, replace the ADR list in HLD §13 item 1 with a link to the index below, and add a one-line pointer to this index in `CLAUDE.md`.

## 5. What deserves an ADR

**Write an ADR** when a decision meets at least one of these:

- it is hard or costly to reverse (technology adoption, data ownership, source of truth, deployment unit);
- it crosses application boundaries or shapes an external interface (integrations, providers, administrators);
- it fixes a reliability, security, privacy, or regulatory guarantee (delivery semantics, retries, authentication, LGPD);
- it constrains the portability goals (broker, database, provider replaceability, C-02 to C-04);
- real alternatives with trade-offs were weighed, and a future contributor would ask "why not X?".

**Keep it only in the HLD (or a focused document)** when it:

- explains *how* an approved decision works at runtime (flows, sequences, boundaries) rather than *which* option was chosen;
- is a term, assumption, open question, inconsistency, or a proposal still under discussion (`A-nn`, `OQ-nn`, `I-nn`, `P-nn` not yet ready for review);
- is a detail derived directly from an existing ADR with no new trade-off;
- belongs in a contract, schema, or data model (event fields, endpoints, table layouts).

**Grouping:** related decisions confirmed together and sharing one rationale go into one ADR (see [§7](#7-grouping-of-d-01-to-d-65)). One ADR per D-nn would produce 65 thin records that repeat the decision log.

## 6. Recording approval

- **Decision owner:** the project owner (D-01, C-10), for every ADR.
- The header separates **when the decision was confirmed** (`Decision date`, normally 2026-10-22 for D-01 to D-65) from **when this record was approved** (`Record approved`). The owner confirmed the decisions; the rationale, alternatives, and consequences written in an ADR are new text that the owner has not yet reviewed.
- **Confirmed (Q-1, 2026-10-27):** ADRs that record already-confirmed decisions (D-01 to D-65) are created with status **Proposed** and become **Accepted** only after the owner reviews the record. HLD §13's "can be recorded as accepted" does not apply to the ADR text.
- **Approval evidence** names where the approval can be checked: the review round, a commit or pull request approved by the owner, or a dated note. An approval date or approver is never invented; if it is unknown, the field says "pending".
- Approval scope is stated when it is narrower than the platform (for example, "approved for the API-key interim design only; OIDC target deferred").

---

## 7. Grouping of D-01 to D-65

**Confirmed (Q-6, 2026-10-27), including the placements in §7.1 as shown.** 12 groups. Group G-nn is recorded in ADR-00nn (G-01 → ADR-0001, …, G-12 → ADR-0012); see the index in §9. Every decision appears in exactly one group (checked mechanically: 65 of 65).

| Group | Provisional ADR title | Decisions | Rationale |
|---|---|---|---|
| G-01 | Structure the platform as a choreographed pipeline of six applications behind ports and adapters | D-48, D-54, D-57, D-58 | The overall shape and scope: no orchestrator, technology confined to adapters, approved responsibilities, single notifications only. |
| G-02 | Accept notifications durably with outboxes and at-least-once hops | D-27, D-35, D-37, D-49, D-61 | One delivery-semantics story: outbox in every stateful publisher, mandatory idempotency key, no cross-notification ordering, duplicates minimized not eliminated. |
| G-03 | Route each tenant's notifications per channel to its configured provider, else the channel default | D-03, D-04, D-06, D-09, D-42, D-43, D-44, D-55 | The provider-routing boundary end to end: per-tenant/per-channel configuration, platform-owned credentials, admin management, pre-check, Redis cache, resolution at send time. |
| G-04 | Retry failed sends with capped exponential backoff and equal jitter, and replay dead letters manually | D-07, D-10, D-11, D-15, D-17, D-18, D-39, D-40 | A single failure-handling policy; timeouts (OQ-16) remain deferred and will refine this ADR. |
| G-05 | Model delivery status as a forward-only state machine | D-26, D-29, D-30, D-41, D-60 | Vocabulary, `FAILED` vs `NOT DELIVERED`, first-final-wins, and the one DLQ-replay exception form one rule set (confirmed by §14 QS-02). |
| G-06 | Keep delivery status in the delivery-status application's PostgreSQL and expose it only by API pull | D-16, D-19, D-21, D-33, D-56 | Source of truth and read path: single writer, no push to integrations, reads through the internal query interface, freshness accepted as "not found" right after submission. |
| G-07 | Ingest provider status by push only, through the provider-callbacks application | D-20, D-22, D-23, D-24, D-25 | How status enters the platform: webhook or queue per provider, published to Kafka, no polling, and `SENT` as the final known status when a provider never reports. |
| G-08 | Authenticate callers with platform-issued API keys and defer OIDC/OAuth 2.0 | D-02, D-28, D-31, D-32, D-47, D-50, D-51, D-52, D-53, D-64 | The credential mechanisms: the deferred OIDC/OAuth target, the interim API keys for integrations and administrators, service keys, revocation, and key handling. |
| G-09 | Isolate tenants and integrations, and separate administrative traffic | D-05, D-08, D-12, D-13, D-14, D-36 | The authorization model: one credential per integration, tenant from verified credentials only, per-integration visibility and rate limits, every caller treated as a backend. |
| G-10 | Give each application its own database on a shared PostgreSQL instance, with secrets kept in a secrets store | D-45, D-46, D-59 | Persistence topology and data ownership, plus where credentials and configuration live. |
| G-11 | Protect personal data with application-level encryption and bounded retention | D-38, D-62, D-63 | LGPD-driven privacy controls belong together and share the pending legal/DPO review. |
| G-12 | Govern architecture through the project owner and approved fitness checks | D-01, D-34, D-65 | Governance and verification decisions that apply to every other ADR. |

### 7.1 Decisions that do not fit cleanly

| Decision | Placed in | Why it is awkward | Alternative |
|---|---|---|---|
| D-01 | G-12 | A process decision, not an architecture decision. This README already relies on it. | Record it only in this README and the HLD, and drop it from the ADR set. |
| D-34 | G-12 | Defers numeric quality targets; it is closer to observability than governance. | Move to an observability ADR if one is created later. |
| D-37 | G-02 | Two clauses: "each application has its own deployment" (structure, G-01) and "outbox in the API and callbacks app" (G-02, later extended by D-61). | Split the clauses across G-01 and G-02 (would break "exactly one group"). |
| D-58 | G-01 | Approves the HLD §5.1, §5.2, and §5.4 responsibility lists (not §5.3); it also contains the idempotency-conflict rule (G-02), the four outcome classes (G-04), and per-provider-account throttling (G-03). | G-01 records it and the other ADRs link to it. |
| D-59 | G-10 | Mixes data ownership with the secrets-store rule, which also touches D-04 (G-03) and D-46. | Acceptable as placed. |
| D-36 | G-09 | Rate limits per integration are a protection control rather than identity or isolation. | G-01 (responsibilities) or a small ADR of its own. |
| D-44 | G-03 | HLD §13 pairs it with D-45 (database topology); it also introduces Redis as a new technology. | G-10, with G-03 linking to it. |
| D-16 | G-06 | HLD §13 lists it under both the identity ADR and the status-API ADR. | G-09 (as an authorization rule). |
| D-25 | G-07 | Follows HLD §13, but it also defines status semantics (G-05). | G-05. |
| D-40 | G-04 | A stuck-work alert, closer to operations than to retry policy. | G-01 (choreography needs explicit stuck-work detection, per D-57). |
| D-48 | G-01 | A product-scope boundary rather than an architecture choice. | G-12, or HLD only. |
| D-13 | G-09 | Narrowed by D-14; kept so the history is visible. | — |

### 7.2 Confirmation gaps noticed while grouping

When the grouping was proposed (2026-10-27), these confirmed decisions had no matching HLD §14 row. HLD revision 29 added FC-27 to FC-31 for them (still Proposed). The ADRs list further gaps in their own Confirmation tables:

- D-36 (per-integration rate limits);
- D-39 and D-41 (manual DLQ replay keeps the notification ID and may reopen `FAILED`);
- D-55 (retries keep the first attempt's provider; the attempt records provider and source);
- D-58 (per-provider-account throttling), which also depends on OQ-11;
- D-57 (no central orchestrator) and D-49 (no ordering), which may need only a review step rather than an automated check.

**Done in HLD revision 29 (Q-5):** §14 rows now have stable IDs (FC-01 to FC-31), which ADRs cite, and FC-27 to FC-31 were added for these gaps. New rows are labelled **Proposed** in the HLD until approved, because D-65 approved only the checks that existed then.

---

## 8. Questions for the owner

| ID | Question | Impact |
|---|---|---|
| Q-1 | **Answered 2026-10-27: Proposed, then accepted after review.** ADRs for decisions you already confirmed (D-01 to D-65): should they be created as **Proposed** and accepted after you review the text, or written directly as **Accepted**? HLD §13 says "can be recorded as accepted", but the rationale and alternatives are new text. | Status of the first ADR batch. Recommended: Proposed, then a single acceptance review. |
| Q-2 | **Answered 2026-10-27: yes.** Should **Rejected** be added to the four requested statuses? | Whether declined proposals stay in the log. |
| Q-3 | **Answered 2026-10-27: context §8.** Which copy of the D-nn wording is canonical: context §8 or HLD §2.3? Their wording differs (for example D-52, D-55). | Which text the ADRs quote. Recommended: context §8 for the decision text, HLD §2.3 for what it resolves and raises. |
| Q-4 | **Answered 2026-10-27: yes.** Is the parameter-only **Amendments** exception (§3.3 rule 4) acceptable, or should every change produce a new ADR? | Number of ADRs created by tuning values. |
| Q-5 | **Answered 2026-10-27: yes, to all.** In step 2, may the HLD be updated to add an "ADR" column to §2.3, link §13 to this index, give §14 rows stable IDs, and add rows for the gaps in §7.2? Should CLAUDE.md get a one-line pointer to this index? | Back-links and confirmation links; without them, ADRs cite §14 rows by name. |
| Q-6 | **Answered 2026-10-27: grouping approved as shown.** Do you approve the grouping in §7, in particular the placements flagged in §7.1 (D-01, D-36, D-37, D-44)? | The scope of each ADR. |

---

## 9. ADR index

| ADR | Title | Status | Decisions | Record approved |
|---|---|---|---|---|
| [ADR-0001](0001-structure-platform-as-choreographed-pipeline-with-ports-and-adapters.md) | Structure the platform as a choreographed pipeline of six applications behind ports and adapters | Accepted | D-48, D-54, D-57, D-58 | 2026-11-02 |
| [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md) | Accept notifications durably with outboxes and at-least-once hops | Accepted | D-27, D-35, D-37, D-49, D-61 | 2026-11-02 |
| [ADR-0003](0003-route-tenant-notifications-to-configured-or-default-provider.md) | Route each tenant's notifications per channel to its configured provider, else the channel default | Accepted | D-03, D-04, D-06, D-09, D-42, D-43, D-44, D-55 | 2026-11-02 |
| [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md) | Retry failed sends with capped exponential backoff and equal jitter, and replay dead letters manually | Accepted | D-07, D-10, D-11, D-15, D-17, D-18, D-39, D-40, D-67 | 2026-11-02 |
| [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md) | Model delivery status as a forward-only state machine | Accepted | D-26, D-29, D-30, D-41, D-60 | 2026-11-02 |
| [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md) | Keep delivery status in the delivery-status application's PostgreSQL and expose it only by API pull | Accepted | D-16, D-19, D-21, D-33, D-56 | 2026-11-02 |
| [ADR-0007](0007-ingest-provider-status-by-push-through-callbacks-app.md) | Ingest provider status by push only, through the provider-callbacks application | Accepted | D-20, D-22, D-23, D-24, D-25 | 2026-11-02 |
| [ADR-0008](0008-authenticate-callers-with-api-keys-and-defer-oidc-oauth.md) | Authenticate callers with platform-issued API keys and defer OIDC/OAuth 2.0 | Accepted | D-02, D-28, D-31, D-32, D-47, D-50, D-51, D-52, D-53, D-64 | 2026-11-02 |
| [ADR-0009](0009-isolate-tenants-and-integrations-and-separate-admin-traffic.md) | Isolate tenants and integrations, and separate administrative traffic | Accepted | D-05, D-08, D-12, D-13, D-14, D-36 | 2026-11-02 |
| [ADR-0010](0010-use-a-database-per-application-on-shared-postgresql.md) | Give each application its own database on a shared PostgreSQL instance, with secrets kept in a secrets store | Accepted | D-45, D-46, D-59 | 2026-11-02 |
| [ADR-0011](0011-protect-personal-data-with-encryption-and-bounded-retention.md) | Protect personal data with application-level encryption and bounded retention | Accepted | D-38, D-62, D-63 | 2026-11-02 |
| [ADR-0012](0012-govern-architecture-through-owner-approval-and-fitness-checks.md) | Govern architecture through the project owner and approved fitness checks | Accepted | D-01, D-34, D-65, D-66; D-69 (amendment) | 2026-11-02 |
| [ADR-0013](0013-correlate-early-provider-reports-with-attempt-outcomes.md) | Correlate provider status reports that arrive before the attempt outcome | Accepted | D-68 | 2026-11-02 |
| [ADR-0014](0014-select-first-provider-per-channel.md) | Select the first provider per channel | Accepted | D-70 | 2026-11-04 |
| [ADR-0015](0015-use-selected-providers-as-defaults-and-replaceable-onesignal-authentication.md) | Use the selected providers as defaults and keep OneSignal event authentication replaceable | Accepted | D-71, D-72 | 2026-11-04 |
