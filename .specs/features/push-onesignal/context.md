# Push through OneSignal Context

**Gathered:** 2026-11-04
**Spec:** `.specs/features/push-onesignal/spec.md`
**Status:** Ready for design, pending spec confirmation

---

## Feature Boundary

The push worker on the shared dispatch workflow, OneSignal send, and Event Stream ingestion through the callbacks application.

---

## Implementation Decisions

### Provider

- The OneSignal Free tier is the first push provider (owner, 2026-11-04; AD-001). It replaces the FCM option offered in discussion, and gives push a status path that FCM lacks.

### Verified facts

- Event Streams are OneSignal's webhooks. They support custom headers only, with no signing.
- Free plan: 1 active stream and up to 1,000 events per month. Behaviour over the cap is not stated.
- Free plan: fewer than 1,000 MAU to send mobile push. Over the limit, mobile push stops until upgrade, with 24 hours to upgrade.
- `POST /notifications` on Free: 150 requests per second per app. A 429 carries `Retry-After`.
- `idempotency_key` is a UUID valid for 30 days. A repeat within the window does not send again.
- Response: `id` empty with HTTP 200 means not sent. `include_subscription_ids` accepts a subscription UUID.
- Each event has a unique `event.id`, and `message.id` identifies the notification.

### To confirm in design

- The exact event kind values for received and failed push: the page read names only `message.push.sent` and the categories.
- The idempotency and response details above came from a truncated page, so they need checking against the reference.

### Risks the owner should weigh

- 1,000 events per month means at most about 1,000 notifications with a status beyond `SENT`, and fewer if a notification yields more than one event.
- Unsigned events make QS-07 weaker than for SES and textbee. Anyone who learns the header secret can set push status.
- Each tenant's mobile app probably needs its own OneSignal app, so the Free tier may not scale across tenants.

### Agent's Discretion

None: the owner chose the provider and tier.

### Declined / Undiscussed Gray Areas → Assumptions

Event selection, recipient form, and handling of limits are logged in the spec's Assumptions table.

---

## Specific References

- [Event Streams](https://documentation.onesignal.com/docs/en/event-streams), [Usage and billing](https://documentation.onesignal.com/docs/en/billing-faq), [Rate limits](https://documentation.onesignal.com/reference/rate-limits), [Push notification API](https://documentation.onesignal.com/reference/push-notification)

---

## Deferred Ideas

- Retrying unknown outcomes on OneSignal, since its idempotency key makes that safe. It belongs with the OQ-16 decision.
