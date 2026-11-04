# Notification Platform — Architecture Context

> **Purpose:** This document records the project context and constraints currently supplied by the project owner. It is not the HLD and does not approve any proposed architecture. Update it when confirmed decisions change.

## 1. Goal and scope

The project is a multi-channel notification platform, initially supporting SMS, email, and push notifications. It is implemented as a NestJS monorepo with six planned applications.

## 2. Planned applications

The current application responsibilities are:

1. **API / Gateway** — entry point between clients and the notification-processing workers.
2. **SMS Worker** — processes SMS notifications.
3. **Email Worker** — processes email notifications.
4. **Push Notification Worker** — processes push notifications.
5. **Provider Callbacks Application** — receives callbacks from notification providers.
6. **Delivery Status Management Application** — maintains notification delivery statuses across channels.

These are high-level responsibilities only. Detailed interfaces, internal components, data ownership, process boundaries, deployment topology, and communication protocols remain to be designed. Do not assume that each application has its own database or must be independently deployed unless that is explicitly decided.

## 3. Initial technology choices

- **Application framework:** NestJS.
- **Initial message broker:** Apache Kafka.
- **Initial database:** PostgreSQL.
- **Cache:** Redis, for routing configuration (D-44). The database remains the source of truth.
- **Notification providers:** Amazon SES for email, hosted textbee.dev for SMS, and the OneSignal Free tier for push (D-70).

## 4. Architectural goals and constraints

### 4.1. Broker independence

Kafka is the initial broker, but the architecture should keep notification business rules and application use cases from depending directly on Kafka-specific APIs or message types. A future implementation using RabbitMQ or AWS SQS should be feasible without rewriting core notification behavior unnecessarily.

This is not a requirement that brokers be perfectly interchangeable or that migration have zero cost. Their semantics differ, including delivery, ordering, acknowledgements, retry mechanisms, routing, and dead-letter handling. Identify which semantics the platform actually requires and document any adapter-specific limitations.

### 4.2. Provider independence and client-based routing

The first providers are selected (D-70). The architecture should support adding and replacing providers without spreading vendor-specific SDKs or logic throughout the core application.

Provider routing must be possible based on the client/customer (the tenant, D-09) using the platform. The base routing policy is now confirmed (see §8, D-03): each client's configured provider is stored in the database, and a default provider is used when none is configured. Do not assume automatic failover, fallback providers, weighted routing, cost-based routing, or routing by availability/capability unless those requirements are agreed.

Keep provider selection, provider-specific integration, credentials/configuration, and channel processing responsibilities explicit in the design. Do not invent provider names or provider-specific APIs.

### 4.3. Database independence

PostgreSQL is the initial database, but the design should avoid unnecessary coupling between core business rules and database-specific implementation details. Future alternatives may include another SQL database or a NoSQL database such as MongoDB.

This is a design goal, not a promise of zero-cost substitution. Relational and document databases differ in transactions, constraints, query capabilities, consistency, and data modeling. Identify the required guarantees and explain portability limits instead of hiding those differences behind a generic repository interface.

### 4.4. Appropriate abstraction

Define abstractions around capabilities the application actually needs. Do not build a generic framework for hypothetical use cases or impose architectural patterns by default. Evaluate the benefit, complexity, and operational cost of each significant abstraction.

## 5. Existing architecture input

The initial architecture diagram is:

`docs/architecture/notification-service/diagrams/notification-platform-hld.drawio`

The diagram now has two pages: "v1 - Current design", which reflects the written HLD, and "v0 - Initial proposal (superseded)", the original proposal kept for traceability. The written HLD exists at the location below. Inspect the diagram before documenting flows or responsibilities. Treat unclear or contradictory elements as questions to resolve, not as facts.

The intended written HLD location is:

`docs/architecture/notification-service/high-level-design.md`

The HLD should explain the rationale and runtime behavior behind the diagram, not merely restate its boxes and arrows.

## 6. Decisions not yet established

Unless clarified by existing project artifacts or subsequently approved, do not assume:

- provider names, provider SDKs, provider endpoints, or provider-specific capabilities;
- exact API endpoints, authentication scheme, request/response payloads, event names, schemas, topic/queue names, or routing keys;
- delivery guarantees, ordering requirements, idempotency strategy, retry policies, timeout values, dead-letter behavior, or replay procedures;
- the full notification lifecycle, status-transition rules, or authoritative owner/source of truth for delivery status;
- table/entity/document schemas, indexes, retention periods, database-per-application ownership, or transaction boundaries;
- whether the six applications are separate deployment units or processes;
- throughput targets, SLOs, availability targets, compliance obligations, or detailed deployment topology.

These are design questions. The HLD should distinguish items that can be proposed with stated assumptions from items that require a decision before implementation.

## 7. HLD expectations

The first HLD should cover, at a high level:

- purpose, scope, constraints, and relevant context;
- responsibilities and boundaries of all six applications;
- main submission, processing, callback, and status-maintenance flows;
- broker, provider, and persistence boundaries and the trade-offs of portability;
- data ownership and delivery-status consistency questions;
- reliability and failure concerns, including duplicate/out-of-order processing where relevant;
- security, privacy, observability, and operational concerns;
- major trade-offs, risks, assumptions, open questions, and decisions requiring approval;
- next design artifacts needed after the HLD review.

Do not try to settle every class, payload, event schema, provider integration, or physical data model during the HLD phase.

## 8. Confirmed decisions

Confirmed by the project owner on 2026-10-22, during review of the HLD; D-66 to D-69 on 2026-11-02, during review of the ADRs; D-70 to D-72 on 2026-11-04, during implementation planning. See [`high-level-design.md`](high-level-design.md) §2.3 for the follow-up questions each decision raises.

| ID | Decision |
|---|---|
| D-01 | The project owner is the architecture decision owner and approver. |
| D-02 | Identity and access: OpenID Connect (OIDC) for user identity, OAuth 2.0 for delegated access and service-to-service access, NestJS guards for enforcement. The identity provider is not yet selected. |
| D-03 | Once the client is identified, the platform routes to the provider configured for that client in the database. If the client has no configured provider, a default provider is used. The default provider is not yet defined. |
| D-04 | Provider credentials are owned by the platform only. Clients have credentials to access the platform and nothing else. |
| D-05 | One OAuth client per independently managed customer integration. The platform backend controls the client-to-tenant mapping. Scopes are least-privilege. This separates credential identity from customer data isolation, and the platform never trusts tenant identifiers supplied by callers. |
| D-06 | Routing configuration is managed through administrative endpoints, so that a back-office can be built on them later. |
| D-07 | When a send fails, it is retried with exponential backoff up to 3 times before the notification fails for good. |
| D-08 | An integration can see only the notifications it submitted, never those of other integrations, even within the same tenant. |
| D-09 | Provider configuration is per tenant. In D-03, "client" means tenant. |
| D-10 | At most 4 attempts in total (the original plus 3 retries). Exponential backoff with base 1 s and cap 30 s. Permanent rejections are not retried. Timeout handling is not yet defined. |
| D-11 | A failure reported by a provider after it accepted a send is final. It does not trigger a resend. |
| D-12 | Administrative traffic is separated from integration traffic. There is one administrator role for now. |
| D-13 | Integrations include both frontend applications and backend services. It must not be assumed that only administrators are human users of the API. (Narrowed by D-14.) |
| D-14 | Assume every connection to the platform comes from a backend service; the platform only sends notifications. This narrows D-13: tenants' products may have frontends, but those reach the platform only through the tenant's backend. |
| D-15 | Retry delay before retry *n* (*n* = 1 for the first retry) is d<sub>n</sub> = min(cap, base × 2<sup>n−1</sup>), with base = 1 s and cap = 30 s. Under D-10 the delays are 1 s, 2 s, and 4 s. |
| D-16 | Integrations can read the status of the notifications they submitted, and only those (with D-08). |
| D-17 | Jitter is applied to the D-15 retry delays. The form is set by D-18. |
| D-18 | Equal jitter: actual retry delay = d<sub>n</sub>/2 + random in [0, d<sub>n</sub>/2]. |
| D-19 | Status must be made visible and read as fast as possible. "Not found" for a notification read immediately after submission is acceptable. |
| D-20 | Providers report status updates in provider-specific ways. The provider-callbacks application receives them and publishes them to a Kafka topic, from which the status projector (delivery-status application) updates status. |
| D-21 | Integrations retrieve status from the platform through its API. The platform does not push status to integrations. |
| D-22 | Status is received from each provider by polling, webhook, or queue, depending on what that provider offers. Whatever a provider supports is implemented, even if it is only one of the three. Narrowed by D-23 and D-24. |
| D-23 | Only push mechanisms (webhook or queue) are used to receive provider status. There is no reconciliation polling. |
| D-24 | The platform does not poll providers for now; it only sends notifications. Polling is deferred to a future feature that will update states providers did not report. |
| D-25 | For outcomes a provider never reports, "accepted by provider" is the final known status, for now. |
| D-26 | Status vocabulary: PROCESSING (still processing on the platform's side), SENT (sent to the provider), DELIVERED (provider reported delivery), BOUNCED (provider reported a bounce; probably email only, but usable by other channels), NOT DELIVERED (provider reported errors on delivery). |
| D-27 | Durable acceptance through a transactional outbox (HLD P-03) is approved. |
| D-28 | Integration authentication, initial direction: OAuth 2.0 client credentials or API keys, depending on client requirements. Tenant identity is tied to credentials verified by the backend, never trusted from a client-supplied tenantId alone. The maximum revocation propagation time must be explicit, using a common community value. If JWTs are used, short lifetimes and the cost of revocation checks must be evaluated. |
| D-29 | A FAILED status, with a status reason, covers failures before the provider accepted the notification: the provider rejecting the send, retries exhausted, no eligible provider, or an unprocessable message. NOT DELIVERED is set only when a provider reports a delivery failure. |
| D-30 | When final statuses conflict, the first final status wins, for now. |
| D-31 | Each integration has exactly one credential type, OAuth 2.0 client credentials or an API key, chosen by an administrator when the integration is created. Never both. |
| D-32 | Revocation takes effect within 5 minutes at most: revocation happens in the integration registry, the registry cache lasts 60 s or less, and JWT access tokens last 5 minutes. |
| D-33 | PostgreSQL, written only by the delivery-status application, is the source of truth for delivery status. Event topics are inputs with operational retention only. |
| D-34 | Numeric quality targets are deferred until real load is known; every measure is collected from day one. |
| D-35 | Every submission must carry an idempotency key, scoped per integration and remembered for 24 hours. A retry with the same key returns the original notification. |
| D-36 | Rate limits per integration from the start, with values set by administrators. |
| D-37 | Each of the six applications has its own deployment. The outbox pattern runs in the API / Gateway and in the provider-callbacks application. |
| D-38 | Content and recipient data: 30 days, then deleted or anonymized. Status history: 1 year. Topics and DLQ: no longer than 30 days. LGPD recommendations apply. |
| D-39 | No maximum notification age for now. DLQ messages are replayed manually by administrators through an admin endpoint, keeping the original notification ID. Alert when the DLQ grows. |
| D-40 | Alert when a notification stays in PROCESSING for more than 5 minutes. |
| D-41 | A manual DLQ replay by an administrator may reopen a notification from FAILED to PROCESSING. This is the only exception to D-30. |
| D-42 | Provider configuration is per channel, with at most one configured provider per tenant per channel, and one platform-wide default provider per channel. |
| D-43 | A submission is rejected only after the platform has tried to find a valid provider for it (tenant configuration, then default) and found none. |
| D-44 | How fast routing changes take effect does not matter. Routing configuration can be served from a Redis cache; the database remains its source of truth. |
| D-45 | One shared PostgreSQL instance, with a separate database per application. |
| D-46 | Kafka, PostgreSQL (and other infrastructure) credentials are secrets made available through environment variables, to be set up later. |
| D-47 | No identity provider for now. Integrations authenticate with platform-issued API keys ("API key/token"). The IdP-dependent parts of D-02, D-28, D-31, and D-32 are deferred until an IdP is introduced. |
| D-48 | Only single notifications for now. Templates, scheduled sends, recipient preferences, and bulk sends are future scope. |
| D-49 | There is no ordering requirement across notifications; delivery order may differ from submission order. |
| D-50 | Delegated access (a system acting on behalf of a person) is not needed for now. |
| D-51 | "API key" and "token" mean the same thing: one platform-issued secret per integration, sent in a request header. |
| D-52 | Administrators authenticate with administrator API keys that are valid only on the administrative endpoints, never on integration traffic. |
| D-53 | Internal service-to-service calls (for example API → delivery-status application) authenticate with a service key per calling application, injected through environment variables, plus a network restriction. |
| D-54 | Business rules and use cases depend only on narrow interfaces (ports) built around the capabilities they need. Kafka, PostgreSQL, Redis, and provider client libraries live only in replaceable adapters. No generic framework. |
| D-55 | The channel worker selects the provider at send time through a separate routing policy. Retries keep the provider chosen for the first attempt. Each attempt records the provider used and whether it came from tenant configuration or the default. |
| D-56 | The API / Gateway serves status reads by calling the delivery-status application's internal query interface, scoped by tenant and integration. Another integration's notification is indistinguishable from an unknown one. |
| D-57 | The platform is a choreographed, event-driven pipeline: each application reacts to facts published by the previous one, with no central orchestrator. |
| D-58 | Application responsibilities as described in the HLD (§5.1, §5.2, §5.4) are approved. This includes: the same idempotency key with a different body is rejected; worker outcomes are classified as accepted, permanent, retryable, or unknown; the three workers share one send workflow but deploy separately; workers throttle to each provider account's rate limit. |
| D-59 | Data ownership as described in the HLD (§4.5, §6.1) is approved, including the worker attempt ledger and immutable accepted requests. Sensitive values (all credentials and keys) are kept in a secrets store; non-sensitive configuration is kept in environment variables. Secrets may be delivered to applications as environment variables (D-46). |
| D-60 | Status only moves forward (PROCESSING, then SENT, then a final status), except for a manual DLQ replay. A provider report may skip SENT. The attempt number is a field, not a status. FAILED reasons start as REJECTED_BY_PROVIDER, RETRIES_EXHAUSTED, NO_ELIGIBLE_PROVIDER, UNPROCESSABLE. BOUNCED and NOT DELIVERED may carry a normalized provider reason. |
| D-61 | Every hop between applications is at-least-once. Duplicate sends are minimized, not eliminated; exactly-once delivery to recipients is not promised. Provider idempotency keys are used where supported and are a provider-selection criterion. The channel workers also use an outbox, so every application that stores state and publishes events has one. |
| D-62 | LGPD considerations are approved: status history holds no personal data; the platform acts as operator (processor) and tenants as controllers; data is collected and used only for sending and status; administrators can delete a recipient's data per tenant; international transfer is a provider-selection criterion; encryption and an incident path are required. To be reviewed by a lawyer or DPO before production. |
| D-63 | Message content and recipient data are encrypted at application level, from acceptance until the worker's provider call. |
| D-64 | API keys (integration and administrator) are generated by the platform and shown once, stored only as peppered hashes, sent only in request headers, scoped to one integration or to the administrative surface, rotated with a short overlap period, and never logged; a non-secret prefix identifies them. |
| D-65 | The automated fitness checks listed in the HLD (§14) are approved, to be built together with the features they protect. |
| D-66 | Fitness checks FC-27 to FC-31 in the HLD (§14) are approved, to be built together with the features they protect, as for D-65. (Confirmed 2026-11-02.) |
| D-67 | FC-09 is redefined around D-40: a notification that stays in PROCESSING for more than 5 minutes must raise an alert. A notification at SENT with no further provider report is not stuck (D-25) and raises no alert. (Confirmed 2026-11-02.) |
| D-68 | The handling of provider status reports that arrive before the attempt outcome is approved as recorded in ADR-0013: the Delivery-status app parks unmatched provider events durably before acknowledging them, applies them through the normal transition rules when an attempt outcome establishes the correlation, and raises an alert, changing no status, for any event still unmatched after a bounded period. Parking and reconciling stay inside the Delivery-status app. The hold period, retention, and correlation-key scope remain open (OQ-57, OQ-58). (Confirmed 2026-11-02.) |
| D-69 | Fitness checks FC-32 and FC-33 in the HLD (§14), which confirm ADR-0013 (D-68), are approved, to be built together with the features they protect, as for D-65 and D-66. (Confirmed 2026-11-02.) |
| D-70 | The first provider per channel is Amazon SES for email, hosted textbee.dev for SMS, and the OneSignal Free tier for push. Whether they are also the platform-wide defaults, and whether OneSignal's static-header event authentication is acceptable, remain open (OQ-59, OQ-60). (Confirmed 2026-11-04.) |
| D-71 | The D-70 providers are also the platform-wide default per channel. (Confirmed 2026-11-04.) |
| D-72 | OneSignal events are authenticated by a static secret in a custom header, for now. The service must be ready for this to change at any time. (Confirmed 2026-11-04.) |

**Clarification of D-14 (revision 5 review):** the platform does not need to care whether a client is a backend or a frontend; every integration is treated as a backend service. "We just send notifications" describes the platform's role and does not exclude status reads (D-16).

Timeouts remain explicitly deferred by the project owner (2026-10-22).
