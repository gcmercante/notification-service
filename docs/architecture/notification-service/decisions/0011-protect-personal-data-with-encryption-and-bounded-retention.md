# ADR-0011: Protect personal data with application-level encryption and bounded retention

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-38, D-62, D-63 |
| Decision date | 2026-10-22 |
| Record approved | 2026-11-02, by the project owner |
| Approval evidence | Decisions confirmed in the HLD review rounds recorded in HLD [§2.3](../high-level-design.md#23-decision-log): D-38 during review of revision 13; D-62 and D-63 during the item-by-item review of revision 18. This record itself has not been reviewed. **Scope:** this ADR is not legal approval. D-62 is subject to review by a lawyer or DPO, and approving this record does not extend to production use until that review has taken place. Record: accepted by the project owner on 2026-11-02, together with ADR-0001 to ADR-0013. |
| Constraints | C-09, C-44, C-68, C-69 |
| HLD sections | §6.4, §8.3, §9 |
| Supersedes | — |

## Context

The platform carries personal and possibly sensitive data: recipient addresses, phone numbers, device tokens, and message content. This data passes through the API store, the outboxes, the channel topics, the worker databases, the DLQs, and the provider requests (HLD [§8.3](../high-level-design.md#83-callbacks-tenancy-and-personal-data)). Several of these are copies the platform makes only to move work between applications. Each copy lengthens the time the data exists and widens the set of places that can expose it.

Forces:

- **Confirmed (C-09, from `CLAUDE.md`):** sensitive payloads, credentials, and unnecessary personal data must not appear in logs, traces, or metrics.
- **Confirmed:** the platform is subject to LGPD (Lei nº 13.709/2018). Open question OQ-13 asked how long each kind of data should be kept. D-38 answered it.
- **Confirmed (D-33):** delivery status is kept for audit and status reads, so status history outlives the message it describes. Status history therefore needs a rule on whether it holds personal data.
- **Open question:** no provider has been selected. Providers may process data outside Brazil (HLD [§6.4](../high-level-design.md#64-retention)).
- **Open question:** which secrets store or key-management product to use (D-59, [ADR-0010](0010-use-a-database-per-application-on-shared-postgresql.md)). Encryption keys depend on that choice.
- The HLD's LGPD analysis is described as "derived from general LGPD principles, not legal advice" (§6.4).

## Decision

The owner confirmed three decisions. Context §8 wording is quoted:

- **D-38:** "Content and recipient data: 30 days, then deleted or anonymized. Status history: 1 year. Topics and DLQ: no longer than 30 days. LGPD recommendations apply." (C-44)
- **D-62:** "LGPD considerations are approved: status history holds no personal data; the platform acts as operator (processor) and tenants as controllers; data is collected and used only for sending and status; administrators can delete a recipient's data per tenant; international transfer is a provider-selection criterion; encryption and an incident path are required. To be reviewed by a lawyer or DPO before production." (C-68)
- **D-63:** "Message content and recipient data are encrypted at application level, from acceptance until the worker's provider call." (C-69)

Net position: personal data lives only in the pipeline stages that need it to send. It is encrypted by the application in all of those stages and is deleted or anonymized after 30 days. Status history keeps only identifiers, statuses, reasons, and timestamps for 1 year.

**Not decided here:**

- **Encryption design.** HLD §6.4 marks the design as *Proposed*. This covers encryption in the API / Gateway at acceptance, decryption only in the channel worker immediately before the provider call, envelope encryption with a key-encryption key in the secrets store, key rotation, a keyed-hash "blind index" for deletion by recipient, and comparing a body hash for idempotency conflicts.
- **Key-management or secrets-store product.** Open (D-59, [ADR-0010](0010-use-a-database-per-application-on-shared-postgresql.md)).
- **Delete versus anonymize.** D-38 allows either; the choice per store is not decided.
- **Legal confirmation of D-62.** Pending the lawyer or DPO review. This ADR states no legal conclusion beyond the wording of D-62.

## Alternatives considered

- **Retention periods (D-38):** D-38 resolved OQ-13 by adopting the periods the HLD recommended ("as recommended", HLD §2.3). No other periods were recorded. Not recorded when the decision was made.
- **LGPD considerations (D-62):** the owner approved the HLD §6.4 considerations as written. No alternative positions were recorded. Not recorded when the decision was made.
- **Application-level encryption (D-63):** HLD §2.3 says this was "previously an open option" in §6.4. The current HLD does not keep the text of that option or of any alternative to it. Not recorded when the decision was made.
- **Rely on database and transport encryption only** (retrospective) — not chosen. §6.4 describes application-level encryption as "on top of database and transport encryption". Database and transport encryption alone would leave plain content and recipients readable by anything with access to a topic, DLQ, or database, including operators and replay tooling.

## Consequences

- **Positive:**
  - Personal data has a bounded lifetime (30 days) in every table, topic, and DLQ.
  - Status history can be kept for a year without extending the life of personal data, because it holds none (D-62).
  - A leaked topic, DLQ, or database copy exposes no plain content or recipients.
  - The platform's position as operator (processor) for tenants (controllers) is stated explicitly, ready for contracts and records of processing.
- **Negative / accepted risks** (HLD §6.4 "Cost"):
  - Each message costs CPU to encrypt and decrypt.
  - Key management must be operated.
  - Content and recipients cannot be queried, except through the blind index (Proposed).
  - A lost key makes its data unreadable. The HLD accepts this because the data expires within 30 days anyway.
  - Status reads and audit cannot show recipients or content.
  - Retention, deletion, and encryption add work to every store, every topic, and the DLQ.
  - The legal basis may still change after the lawyer or DPO review.
- **Follow-up:**
  - The lawyer or DPO review of D-62 must happen before production. Its outcome may need a new D-nn.
  - Choose the secrets-store / key-management product (D-59, ADR-0010).
  - Include international transfer as a criterion when providers are selected (D-62).
  - Define the incident path (D-62). No artifact exists for it yet.
  - The logical data model must cover the deletion and anonymization paths (HLD [§13](../high-level-design.md#13-follow-up-artifacts) item 7).
  - The §8.3 controls (minimal status events, encryption in transit and at rest, topic ACLs per application) and the §9 logging and redaction rules are still Proposed.
  - No OQ-nn in HLD [§11.2](../high-level-design.md#112-still-open) is specific to this ADR.
  - Changing a retention period is a parameter-only change, recorded under Amendments with a new D-nn (README §3.3 rule 4).

## Confirmation

The FC IDs refer to HLD [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69). FC-08, FC-15, and FC-18 are approved checks under D-65; none of them is marked *(Proposed)*.

| Claim | Check | Evidence state |
|---|---|---|
| No personal data or content in logs, traces, or metrics (C-09) | FC-08 | Planned |
| Content and recipients are never plain text in the request store, topics, worker databases, or DLQ; the status store and logs contain none at all (D-63, D-62) | FC-15 | Planned |
| An administrator can delete a recipient's data per tenant (D-62) | FC-15 (deletion through the blind index; the blind index itself is a Proposed design) | Planned |
| No content or recipient older than 30 days remains; topic and DLQ retention is 30 days or less (D-38) | FC-18 | Planned |
| Status history is kept for 1 year | Gap — no check exists | — |
| International transfer is assessed when a provider is selected (D-62) | Gap — no check exists | — |
| An incident path exists (D-62) | Gap — no check exists | — |
| The operator/controller roles are reflected in contracts and records of processing (D-62) | Gap — no check exists | — |
| Lawyer or DPO review completed before production (D-62) | Gap — no check exists | — |

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log) (D-38, D-62, D-63); [context §8](../architecture-context.md#8-confirmed-decisions).
- Constraints: HLD [§2.1](../high-level-design.md#21-confirmed-constraints) (C-09, C-44, C-68, C-69).
- Design: HLD [§6.4](../high-level-design.md#64-retention), [§8.3](../high-level-design.md#83-callbacks-tenancy-and-personal-data), [§9](../high-level-design.md#9-observability-and-operations), [§10](../high-level-design.md#10-trade-offs).
- Related to [ADR-0010](0010-use-a-database-per-application-on-shared-postgresql.md): secrets store (D-59), which will hold the key-encryption key; product still open.
- Related to [ADR-0002](0002-accept-notifications-durably-with-outboxes-and-at-least-once-hops.md): outboxes and topics carry encrypted data and follow retention; idempotency keys are kept for 24 hours (D-35).
- Related to [ADR-0006](0006-keep-delivery-status-in-postgresql-and-expose-it-by-api-pull.md): the status store holds no personal data.
- Related to [ADR-0004](0004-retry-failed-sends-with-capped-backoff-and-manual-dlq-replay.md): DLQ retention and replay of encrypted messages.
- Related to [ADR-0012](0012-govern-architecture-through-owner-approval-and-fitness-checks.md): fitness checks (D-65).
- Logical data model and deletion/anonymization paths: not yet produced (HLD §13 item 7).

## Amendments

None.
