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

- **Feature**: `platform-foundation` (`.specs/features/platform-foundation/tasks.md`)
- **Phase / Task**: Execute. T1 and T2 done, in Jira Testing (NTS-61, NTS-62). T3 is next.
- **Completed**: T1 (`2423aed`, PR #6), T2 (`3deb7f7`, PR #7, stacked on #6)
- **In-progress** (file:line): none
- **Atlassian**: Jira project NTS holds all 75 issues (NTS-5 to NTS-79). Sprint 0 is active. Confluence space NTS has parent pages Architecture (917506) and Architecture Decision Records (950273), published by `scripts/publish_confluence.py`, which `.github/workflows/publish-confluence.yml` runs on each push to `main` that changes these documents, the script or the workflow. The workflow needs the repository secrets `CONFLUENCE_EMAIL` and `CONFLUENCE_API_TOKEN`. The HLD page (491522) shows the `.drawio` file through the draw.io app macro. A publish does not overwrite a page edited in Confluence since its last publish.
- **Workflow**: `CLAUDE.md` section "Daily Implementation Workflow" governs Calendar and Jira use: one task at a time, In Progress, then In Review with a review subagent, then Testing. Only the owner moves issues to Done.
- **Next step**: Merge PR #6 then #7, then start T3 when it is on the day's plan.
- **Blockers**: none. Docker Desktop works in WSL (checked 2026-11-05: Docker 29.9.2, Compose v5.6.1, ports 5432, 9092 and 6379 free).
- **Uncommitted files**: none
- **Branch**: `feat/platform-foundation` (PR #7)
