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
- **Atlassian**: Jira project NTS holds all 75 issues (NTS-5 to NTS-79). Confluence space NTS has parent pages Architecture (917506) and Architecture Decision Records (950273), holding ADR-0001 to ADR-0015, the architecture context and the HLD, published by `scripts/publish_confluence.py`, which `.github/workflows/publish-confluence.yml` runs on each push to `main` that changes these documents, the script or the workflow. The workflow needs the repository secrets `CONFLUENCE_EMAIL` and `CONFLUENCE_API_TOKEN`. The HLD's four Mermaid diagrams use the Mermaid app by Narva Software. The `.drawio` file is attached to the HLD page (491522). The page shows the diagram through the draw.io app macro. Each publish uploads the repository's file and sets the macro to the uploaded version. Whether the macro renders without a `.drawio.png` preview, which only the app's editor generates, has not been confirmed on a live page. A publish does not overwrite a page edited in Confluence since its last publish; it fails until the edit is copied to the repository and the workflow is run with `overwrite_manual_edits`.
- **Next step**: Execute starts at T1 only when the owner says so.
- **Blockers**: Docker is not enabled in this WSL distro, and integration gates need PostgreSQL, Kafka and Redis.
- **Uncommitted files**: the starter scaffold (`package.json`, `src/`, `test/` and config files are untracked; T1 commits them)
- **Branch**: docs/hld-confluence-edits
