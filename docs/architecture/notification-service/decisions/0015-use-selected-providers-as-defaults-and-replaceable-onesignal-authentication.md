# ADR-0015: Use the selected providers as defaults and keep OneSignal event authentication replaceable

| Field | Value |
|---|---|
| Status | Accepted |
| Decision owner | Project owner (D-01) |
| Decisions recorded | D-71, D-72 |
| Decision date | 2026-11-04 |
| Record approved | 2026-11-04, by the project owner |
| Approval evidence | The owner answered OQ-59 and OQ-60 on 2026-11-04 during implementation planning. The owner accepted this record on 2026-11-04, in reply to the Atlassian pilot summary. |
| Constraints | C-04, C-13, C-48, C-49, C-72, C-73 |
| HLD sections | [§4.3](../high-level-design.md#43-provider-routing-boundary), [§5.3](../high-level-design.md#53-callback-flow), [§8.3](../high-level-design.md#83-callbacks-tenancy-and-personal-data) |
| Supersedes | — |

## Context

ADR-0014 selected the first provider per channel and left two questions open.

- **OQ-59:** D-03 and D-42 require one platform-wide default per channel, and no default was defined. Without defaults, every submission from a tenant with no configuration is rejected (D-43).
- **OQ-60:** QS-07 and FC-05 expect inbound status to carry provider-supported proof of authenticity. OneSignal Event Streams offer no signing, only custom headers, so the available proof is a static secret. OneSignal also does not provide a signed timestamp, so replay protection rests on deduplicating `event.id`.

## Decision

**Decided (D-71, 2026-11-04).** "The D-70 providers are also the platform-wide default per channel."

**Decided (D-72, 2026-11-04).** "OneSignal events are authenticated by a static secret in a custom header, for now. The service must be ready for this to change at any time."

The second sentence of D-72 is a requirement on the design. Its reading here, accepted with this record:

1. Each provider's event authentication sits behind a per-provider authenticator in the provider-callbacks application.
2. Changing OneSignal's mechanism changes only that authenticator and its configuration. Normalization, the outbox, the provider-event contract, and the Delivery-status app do not change.
3. The header secret can be rotated through configuration with no code change, and old and new values both work during the rotation.

No mechanism other than the static header is built now, because no other is available (C-06).

## Alternatives considered

- **No platform-wide defaults until a tenant needs one** — Not chosen. Every unconfigured tenant would be rejected. (Source: OQ-59, HLD revision 32.)
- **Reject OneSignal because its events are unsigned** — Not chosen. The owner accepted the static header for now. (Source: OQ-60, owner answer 2026-11-04.)
- **Add a generic authentication framework or configurable mechanisms now** — Not adopted (retrospective). A single narrow authenticator per provider meets D-72, and a framework would serve only hypothetical mechanisms (C-06).

## Consequences

- **Positive:** tenants work with no configuration. The push mechanism can change without touching the status path.
- **Negative / accepted risks:**
  - A tenant with no configuration depends on whichever provider is the default, including its limits (ADR-0014).
  - Anyone who learns the OneSignal header secret can set push status until the secret is rotated. Forged reports can only move status forward under the normal rules, but a forged final status would stay, because the first final status wins (D-30).
- **Follow-up:** revisit D-72 if OneSignal offers signing, or when push moves to a provider that does.

## Confirmation

| Claim | Check | Evidence state |
|---|---|---|
| An unconfigured tenant resolves to the channel default | [§14](../high-level-design.md#14-fitness-checks-confirmed-d-65-d-66-d-67-d-69) — FC-26 | Planned |
| A wrong or missing header secret is rejected and counted | §14 — FC-05 | Planned |
| The authenticator can be replaced with no change outside the adapter and configuration | Gap — no §14 row; planned as the PSH-24 test in `.specs/features/push-onesignal/` | Gap — planned |
| The secret rotates with no code change | Gap — no §14 row; planned as the PSH-25 test in `.specs/features/push-onesignal/` | Gap — planned |

## Links

- Decision log: HLD [§2.3](../high-level-design.md#23-decision-log); [context §8](../architecture-context.md#8-confirmed-decisions) (D-71, D-72).
- Related ADRs: Refines [ADR-0014](0014-select-first-provider-per-channel.md) (D-70); Refines [ADR-0003](0003-route-tenant-notifications-to-configured-or-default-provider.md) (D-03, D-42); Related to [ADR-0007](0007-ingest-provider-status-by-push-through-callbacks-app.md) (D-23); Related to [ADR-0005](0005-model-delivery-status-as-forward-only-state-machine.md) (D-30).

## Amendments

None.
