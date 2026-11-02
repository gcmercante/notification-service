# Project Instructions

## Purpose

This repository contains a NestJS monorepo for a multi-channel notification platform. Use this file as project-wide guidance for architecture, documentation, implementation, and verification. It records confirmed constraints and working rules; it is not a substitute for detailed requirements or approved architecture documents.

## Confirmed Context

- The solution is a **NestJS monorepo** containing six applications initially.
- The six planned application responsibilities are:
  1. **API / Gateway** — entry point between clients and the notification-processing workers.
  2. **SMS worker** — sends SMS notifications.
  3. **Email worker** — sends email notifications.
  4. **Push notification worker** — sends push notifications.
  5. **Provider callbacks application** (provider status ingress) — receives provider status updates by webhook or provider queue, depending on the provider. There is no polling for now.
  6. **Delivery-status application** (status projector) — the single writer of notification delivery status for every channel.
- **Apache Kafka** is the initial message broker.
- **PostgreSQL** is the initial database: one shared instance, with a separate database per application.
- **Redis** caches routing configuration. The database remains its source of truth.
- No notification provider has been selected yet.
- Provider routing selects the provider configured for the tenant (the customer) per channel, otherwise a platform-wide default per channel (not yet defined). There is no automatic failover or fallback.
- Integrations authenticate with platform-issued API keys. There is no identity provider for now; OIDC/OAuth 2.0 is the deferred target design.
- The written HLD is at `docs/architecture/notification-service/high-level-design.md`. Confirmed decisions are listed in `docs/architecture/notification-service/architecture-context.md` §8 and in HLD §2.3.
- ADRs live in `docs/architecture/notification-service/decisions/`. Their convention and index are in its `README.md` (convention Confirmed 2026-10-27). Check the index before making architectural changes.
- The architecture diagram is at `docs/architecture/notification-service/diagrams/notification-platform-hld.drawio`. Page "v1 - Current design" reflects the HLD; page "v0 - Initial proposal (superseded)" preserves the original proposal.

Do not invent application names, endpoints, topics/queues, event names, providers, database schemas, payload fields, delivery guarantees, or deployment details. Inspect the repository and existing diagram before proposing them.

## Architectural Goals and Constraints

### Replaceable infrastructure

The platform should isolate business rules and application use cases from vendor- and infrastructure-specific implementations.

- Kafka is the initial broker, but the design must allow evaluating and implementing an adapter for RabbitMQ or AWS SQS without rewriting notification business rules.
- PostgreSQL is the initial database, but persistence must be designed behind a clear boundary so alternative SQL or NoSQL storage (including MongoDB) can be evaluated later.
- Notification providers are not yet selected. The design must allow adding or replacing providers and routing a tenant's notifications to an eligible provider without scattering provider-specific logic throughout the application.
- Keep provider SDKs, broker clients, database drivers, and infrastructure-specific message types outside the core business rules and application use cases wherever practical.
- Define interfaces around the actual capabilities the application needs. Do not build a generic framework or an abstraction for hypothetical use cases without demonstrating its value.

**Portability is a design goal, not a claim of zero-cost substitution.** Kafka, RabbitMQ, and SQS have different delivery, ordering, acknowledgement, retry, and dead-letter capabilities. Relational databases and document databases have different transaction, query, constraint, and consistency models. Make these differences explicit, preserve required business semantics, and document any adapter-specific limitations. Do not silently weaken guarantees to make implementations appear interchangeable.

### Provider routing

- Treat provider selection as an explicit architectural concern, separate from the channel worker's core notification workflow.
- Routing is confirmed as per-tenant configuration with a per-channel default (see the HLD §4.3). Evaluate any additional criteria (provider capabilities, availability, failure behavior) only when they are agreed.
- Keep tenant-specific routing rules and provider credentials/configuration out of hard-coded business logic.
- Do not assume automatic failover, provider fallback, weighted routing, retries, or cost-based routing unless the requirements approve them.

### Application boundaries

The six application responsibilities above are the current planned topology, not a fully specified component design. Define their ownership, interfaces, state transitions, and interactions in the HLD. Do not infer that each responsibility must have its own database, schema, deployment unit, or independent domain model unless the architecture supports that decision.

In particular, clarify the boundary between:

- accepting a notification request through the API;
- scheduling and dispatching work to a channel worker;
- communicating with a provider;
- receiving and validating provider callbacks;
- recording and maintaining notification delivery states.

Avoid multiple sources of truth for delivery status. Define ownership and state-transition rules explicitly before implementation.

## Architecture Documentation

### Architecture diagram

Before making or reviewing architecture decisions, inspect:

`docs/architecture/notification-service/diagrams/notification-platform-hld.drawio`

Its page "v1 - Current design" reflects the written HLD; page "v0 - Initial proposal (superseded)" is the original proposal, kept for traceability. Keep the v1 page consistent with the HLD. The diagram may still be incomplete or ambiguous. Do not assume that every box, arrow, technology, or responsibility shown in it is final or fully specified. Record inconsistencies and unanswered questions instead of resolving them silently.

### Required written HLD

The written HLD is maintained at:

`docs/architecture/notification-service/high-level-design.md`

Follow existing repository documentation conventions if they provide a better-established location or format. The HLD should explain, at a high level:

- the purpose, scope, and architectural drivers of the platform;
- confirmed constraints and explicit non-goals;
- the role and responsibility of each planned application;
- the main runtime flows and communication boundaries;
- the relationship between the diagram and the written design;
- broker, persistence, and provider abstraction boundaries;
- ownership of notification data and delivery status;
- important reliability, security, privacy, observability, and operational concerns;
- major trade-offs, open questions, assumptions, and decisions that still require approval.

The HLD must explain the reasoning and behavior behind the diagram; it must not merely describe the boxes and arrows. Keep low-level class details, exhaustive payload schemas, and implementation task lists out of the HLD. Link to focused documents for those details as they are produced.

### Detailed design artifacts

Place detailed architecture material under `docs/architecture/notification-service/`, reusing the repository's existing conventions wherever possible. Create documents when they clarify an approved decision or an unresolved design question; do not generate empty templates or boilerplate for their own sake.

Depending on the design, relevant artifacts may include:

- component/container diagrams;
- sequence diagrams for normal flows and important failure/recovery paths;
- class or domain-model diagrams where they clarify domain concepts and relationships;
- notification lifecycle and delivery-status state diagrams;
- HTTP API contracts (OpenAPI where appropriate);
- event/message contracts (AsyncAPI or another appropriate versioned schema format where appropriate);
- logical data model, ownership, retention, and consistency rules;
- failure handling, retries, idempotency, ordering, deduplication, and dead-letter behavior;
- Architecture Decision Records (ADRs) for consequential decisions.

Keep diagrams and contracts consistent with one another and with the written HLD. Prefer version-controlled text formats where practical, while preserving and maintaining the existing Draw.io diagram.

## Design and Engineering Principles

- Start with the repository's actual state, conventions, dependencies, and scripts. Do not assume the project is empty or that a specific package manager, ORM, validation library, test framework, or monorepo tool is in use.
- Use clear application/domain boundaries and dependency inversion where they support the required replaceability. Do not impose a particular folder structure, DDD pattern, CQRS, event sourcing, or microservice pattern without explaining the problem it solves and its costs.
- Separate domain rules from transport, persistence, provider SDKs, and framework details where practical.
- Prefer explicit contracts, typed boundaries, and validation at trust boundaries.
- Treat notification submission, provider dispatch, callbacks, and status updates as potentially duplicated or out of order until delivery semantics are designed and documented.
- Evaluate idempotency, retry ownership, timeouts, concurrency, ordering, rate limits, callback authentication, data retention, personal-data exposure, and observability as part of the design. Do not assume a specific solution before assessing requirements and trade-offs.
- Do not place sensitive notification payloads, credentials, or unnecessary personal data in logs, traces, or metrics.
- Favor the simplest design that satisfies confirmed requirements. Explain the cost of additional abstractions and operational components.
- Do not present proposals, assumptions, or unverified behavior as accepted decisions.

## Architecture Decisions and Unknowns

Distinguish clearly between:

- **Confirmed** — explicitly provided by the project owner or already approved in project artifacts.
- **Proposed** — a recommendation awaiting review or approval.
- **Open question** — information needed to choose a design.
- **Rejected** — an option considered and not selected, with a reason where useful.

For consequential decisions, create an ADR following the repository's existing ADR conventions. If no convention exists, propose a lightweight convention under `docs/architecture/notification-service/decisions/` before creating a collection of records. Do not mark an ADR as accepted without evidence of approval.

When information is missing, state the impact of the uncertainty and ask a focused question when the answer is needed to proceed. Otherwise, continue with clearly labeled assumptions and keep them visible for review. Never invent requirements to make a diagram, contract, or implementation look complete.

## Skill and Workflow Responsibilities

Use installed skills when available. First verify that a skill exists in the current environment; do not assume a skill is installed merely because it is named here.

- **`software-architecture`** — system-level and target architecture, boundaries, runtime behavior, trade-offs, failure behavior, and the written HLD.
- **`api-design-and-evolution`** — HTTP APIs, events, webhooks, payload/schema contracts, compatibility, and interface evolution.
- **`data-architect`** — data ownership, logical data modeling, persistence trade-offs, consistency, and data lifecycle.
- **`adr-authoring`** — documenting consequential decisions, alternatives, consequences, and their lifecycle.
- **`tlc-spec-driven`** — feature specification, acceptance criteria, task decomposition, implementation, and verification.

Do not use TLC Spec-Driven as the primary workflow for pure system-wide architecture analysis or for producing a standalone technical design document. Complete and review the architecture work in `docs/architecture/notification-service/` first when that is the requested task. When the owner asks to plan or implement a feature, use TLC Spec-Driven for its `.specs/` artifacts and execution workflow.

Avoid competing sources of truth:

- `docs/architecture/notification-service/` owns the detailed, reusable architecture documentation and technical contracts.
- `.specs/` owns feature-specific requirements, acceptance criteria, tasks, and verification artifacts produced by TLC Spec-Driven.
- A TLC `design.md`, when applicable, should summarize the feature-relevant approved design and link to the canonical architecture documents. Do not copy large portions of the HLD or duplicate detailed contracts into it.
- If an implementation task exposes a conflict with an approved design, stop and report the conflict. Update the architecture/ADR through review before implementing a materially different design.

## Expected Workflow for Architecture Work

1. Inspect `CLAUDE.md`, the repository README, package/workspace configuration, existing source and tests (if present), documentation, installed skills, and the initial Draw.io HLD.
2. Summarize the current state, confirmed decisions, material gaps, and contradictions grounded in the repository.
3. Propose a bounded architecture-documentation plan. Identify which artifacts are necessary and why; do not create every possible diagram by default.
4. Design the end-to-end flows and application boundaries, including important failure and recovery paths.
5. Reconcile diagrams, contracts, data ownership, and state transitions. Explicitly list remaining decisions.
6. Write or update the HLD and other justified artifacts. Keep proposed decisions visibly distinct from approved ones.
7. Review the documents for consistency, portability assumptions, failure behavior, security/privacy concerns, and traceability to requirements.
8. Do not start feature implementation or create TLC task plans unless requested. Architecture approval does not authorize deployment, remote operations, or destructive actions.

## Implementation and Verification

When implementing approved work:

- Follow the existing codebase patterns unless they conflict with an approved architectural constraint; explain such conflicts before changing direction.
- Inspect available project scripts and run the relevant formatter, linter, type checks, unit/integration tests, and build checks that the repository actually supports.
- Tests must prove observable requirements and edge cases, not merely mirror implementation details.
- Never remove or weaken tests simply to obtain a passing result.
- Report what was run, the result, and any checks that could not be run. Do not claim validation that has not occurred.
- Follow TLC Spec-Driven's own validation gates and commit rules whenever that skill governs the task.
- Do not push, deploy, change production data, or perform other externally visible/destructive operations without explicit authorization for that action.
