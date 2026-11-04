# STATE

## Decisions

### AD-001
- **Decision**: The first provider per channel is Amazon SES for email, hosted textbee.dev for SMS, and the OneSignal Free tier for push.
- **Reason**: The project owner selected them on 2026-11-04 during TLC discussion, in preference to building against a simulated adapter first.
- **Trade-off**: Plans now target real APIs and accounts. textbee capacity is bound to phones and plan limits. OneSignal Free caps Event Streams at 1,000 events per month and mobile push at fewer than 1,000 MAU, and its events are unsigned. No idempotency key is available for SES or textbee, so their crash-after-send duplicate window stays open (QS-03).
- **Scope**: email-dispatch, provider-status-ingress, sms-textbee, push-onesignal. Provider-neutral layers stay unaware of these names (QS-04).
- **Date**: 2026-11-04
- **Status**: active. Recorded as D-70 and ADR-0014 (Accepted). D-71 and D-72 complete it, in ADR-0015 (Accepted).

## Handoff

- **Feature**: planning, all features in `.specs/ROADMAP.md`
- **Phase / Task**: Specs approved for all ten features. `platform-foundation` design and tasks approved. The owner said not to start implementation.
- **Completed**: none (no implementation started)
- **In-progress** (file:line): none
- **Next step**: Owner reviews the Atlassian pilot (Jira NTS-5, Confluence page 589825). Then publish the remaining issues and pages. Execute starts at T1 only when the owner says so.
- **Blockers**: Docker is not enabled in this WSL distro, and integration gates need PostgreSQL, Kafka and Redis.
- **Uncommitted files**: the starter scaffold (`package.json`, `src/`, `test/` and config files are untracked; T1 commits them)
- **Branch**: docs/architecture-adrs
