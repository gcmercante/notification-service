# ADR-0006: Keep delivery status in the delivery-status application's PostgreSQL and expose it only by API pull

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-16, D-19, D-21, D-33, D-56 |
| Decision date | 2026-10-22 |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | Decisions confirmed in the HLD review rounds listed in the [§2.3](../high-level-design.md#23-decision-log) intro: D-16 in the revision 5 review, D-19 in the revision 6 review, D-21 in the revision 7 review, D-33 in the revision 12 review, D-56 in the revision 17 review. This record itself is not yet reviewed. Record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-07, C-25, C-27, C-29, C-39, C-62 |
| HLD sections | [§5.4](../high-level-design.md#54-status-maintenance-flow), [§5.6](../high-level-design.md#56-status-read-flow) (P-04), [§6.1](../high-level-design.md#61-ownership-table-confirmed-d-58-d-59), [§6.2](../high-level-design.md#62-source-of-truth-for-delivery-status), [§10](../high-level-design.md#10-trade-offs) |
| Supersedes | — |

## Context

- **Confirmed (C-07):** there must be exactly one source of truth for delivery status, with ownership and transition rules defined before implementation. The delivery-status application is the single writer of status (HLD §5.4).
- The diagram was ambiguous about what is authoritative: its subtitle reads "PostgreSQL como projeção de estado" (event streams authoritative, PostgreSQL derived), while the node label reads "estado e histórico" (I-05, HLD §6.2).
- Treating the event log as authoritative would require effectively indefinite or compacted topic retention and replayable-forever event schemas. RabbitMQ and SQS cannot provide that, which works against broker portability (C-02, HLD §4.4).
- Integrations need to read the status of their own notifications (C-25), and only their own (C-18 / D-08, recorded in [ADR-0009](0009-isolate-tenants-and-integrations-and-separate-admin-traffic.md)).
- With a database per application (D-45, [ADR-0010](0010-use-a-database-per-application-on-shared-postgresql.md)), the API / Gateway cannot share the status app's tables; it needs some read path to the status owner (P-04).
- **Open question at the time:** how fast status must become visible. The owner answered qualitatively (C-27); the numeric target is deferred (D-34, OQ-02).

## Decision

The project owner confirmed (context §8 wording):

- **D-33:** "PostgreSQL, written only by the delivery-status application, is the source of truth for delivery status. Event topics are inputs with operational retention only."
- **D-16:** "Integrations can read the status of the notifications they submitted, and only those (with D-08)."
- **D-21:** "Integrations retrieve status from the platform through its API. The platform does not push status to integrations."
- **D-56:** "The API / Gateway serves status reads by calling the delivery-status application's internal query interface, scoped by tenant and integration. Another integration's notification is indistinguishable from an unknown one." (P-04 option A.)
- **D-19:** "Status must be made visible and read as fast as possible. "Not found" for a notification read immediately after submission is acceptable."

Net position: status lives only in the delivery-status application's PostgreSQL database; no recovery relies on replaying topics; integrations pull status through the API, which calls the status app's internal query interface; read-your-writes is not required.

**Deferred:** the numeric freshness/latency target (D-19 raises OQ-02, answered by D-34 as "deferred until real load is known; measured from day one", recorded in [ADR-0012](0012-govern-architecture-through-owner-approval-and-fitness-checks.md)). The speed measures in HLD §5.6 (relay latency, consumer lag, indexed lookups, no synchronous joins) remain **Proposed**.

## Alternatives considered

- **Event log authoritative, PostgreSQL a rebuildable projection** — Rejected (D-33): needs indefinite or compacted retention and permanently replayable schemas; not available on RabbitMQ/SQS, against C-02. (Source: HLD §6.2.)
- **P-04 option B: API reads the status tables directly with a read-only grant** — Rejected: not viable with a database per application (D-45); couples the API to the status store's schema and technology, weakening C-03. (Source: HLD §5.6.)
- **P-04 option C: API keeps its own read copy built from status events** — Rejected: a second copy of status that would have to be argued against C-07, with more moving parts; D-19 does not require read-your-writes or reads during a status-app outage. (Source: HLD §5.6.)
- **Push of status to integrations (outbound webhooks or similar)** — Not selected by D-21, which closed OQ-05 and assumption A-07. No further alternatives analysis was recorded when the decision was made.

## Consequences

- **Positive:**
  - One owner and one store for status (C-07); the API never depends on the status store's schema, so replacing that store (C-03) affects only the status app (HLD §10).
  - Recovery is a database backup/restore concern; topics need only operational retention; broker portability is preserved (HLD §6.2, §10).
  - Foreign and unknown notifications are indistinguishable, so callers cannot discover other integrations' notification IDs (C-62).
  - No outbound delivery channel to integrations to secure, retry, or operate.
- **Negative / accepted risks:**
  - Status cannot be rebuilt from topics beyond their retention; re-deriving status after a rule change must use the stored history (HLD §6.2).
  - Backup and point-in-time recovery of the status store become a required operational capability.
  - An extra internal hop on every read, and status reads fail while the status app is unavailable (HLD §10).
  - Reads lag submissions; a "not found" right after submission is accepted (D-19). Integrations that want timely status must poll.
  - A future alternative status store must give system-of-record guarantees, not cache guarantees (HLD §4.5).
- **Follow-up:**
  - Numeric freshness target and backup/recovery targets: OQ-02 / D-34 (ADR-0012).
  - The internal query interface is authenticated with a per-application service key and a network restriction (D-53, [ADR-0008](0008-authenticate-callers-with-api-keys-and-defer-oidc-oauth.md)).
  - Administrator access to the same query interface without the integration filter is **Proposed** (HLD §5.6, §8.1).
  - Status transition rules: [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md). Integration-facing status read contract: HLD §13 item 5.
  - Revisit trigger: a measured freshness target that option A cannot meet, or an owner requirement for status push.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| Integrations read only their own notifications; a foreign notification looks like an unknown one (D-16, D-56) | [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69) — FC-11; also FC-10 (D-08 cross-integration case) | Planned |
| Status visibility is measured from day one; lag and outbox backlog are alerted (D-19) | §14 — FC-12 (target deferred, D-34) | Planned |
| The status query interface accepts only the API's service key and is unreachable from integration ingress (D-56 read path) | §14 — FC-22 | Planned |
| Only the delivery-status application writes status (D-33) | §14 — FC-21 covers database isolation between applications (D-45) only indirectly | Gap — no check exists for single-writer of status specifically |
| No recovery relies on replaying topics; topics have operational retention only (D-33) | §14 — FC-18 checks topic retention ≤ 30 days (D-38), not the recovery rule | Gap — no check exists for the recovery rule |
| No status push to integrations (D-21) | — | Gap — no check exists |

None of the cited FC rows is marked *(Proposed)*; all fall under D-65.

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-16, D-19, D-21, D-33, D-56); [context §8](../architecture-context.md#8-confirmed-decisions).
- HLD: [§5.4](../high-level-design.md#54-status-maintenance-flow), [§5.6](../high-level-design.md#56-status-read-flow), [§6.2](../high-level-design.md#62-source-of-truth-for-delivery-status), [§10](../high-level-design.md#10-trade-offs), [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69).
- Related to [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md) (status rules), [ADR-0007](0007-ingest-provider-status-by-push-through-callbacks-app.md) (status inputs), [ADR-0008](0008-authenticate-callers-with-api-keys-and-defer-oidc-oauth.md) (D-53 service keys), [ADR-0009](0009-isolate-tenants-and-integrations-and-separate-admin-traffic.md) (D-08 per-integration visibility), [ADR-0010](0010-use-a-database-per-application-on-shared-postgresql.md) (D-45), [ADR-0012](0012-govern-architecture-through-owner-approval-and-fitness-checks.md) (D-34).
- Contracts: integration-facing OpenAPI contract (HLD §13 item 5), not yet produced.

## Amendments

None.
