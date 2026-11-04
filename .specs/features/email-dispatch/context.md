# Email Dispatch Context

**Gathered:** 2026-11-04
**Spec:** `.specs/features/email-dispatch/spec.md`
**Status:** Ready for design, pending spec confirmation

---

## Feature Boundary

The shared dispatch workflow, proven on email through Amazon SES. Status events from SES are feature 7.

---

## Implementation Decisions

### Provider

- Amazon SES is the first email provider (owner, 2026-11-04; AD-001).

### Verified facts

- SES publishes `Send`, `Delivery`, `Bounce`, `Reject`, `Complaint`, `DeliveryDelay`, `Open`, `Click`, `Rendering Failure` and `Subscription` in the `eventType` field, through SNS.
- `mail.messageId` is the ID SES returned at send, so it is the provider reference.
- SES publishes hard bounces, and soft bounces only once it stops retrying them.
- The pages read describe no idempotency token for sending.

### Agent's Discretion

None: the owner chose only the provider.

### Declined / Undiscussed Gray Areas → Assumptions

Timeouts and unknown outcomes (OQ-16) were not selected for discussion. The default is in the spec's Assumptions table.

---

## Specific References

- [SES event contents](https://docs.aws.amazon.com/ses/latest/dg/event-publishing-retrieving-sns-contents.html)

---

## Deferred Ideas

- Retrying unknown outcomes for providers with idempotency keys. OneSignal could support this, and HLD §7.3 says such keys close the gap. It belongs with the OQ-16 decision.
