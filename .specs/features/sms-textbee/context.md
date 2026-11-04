# SMS through textbee Context

**Gathered:** 2026-11-04
**Spec:** `.specs/features/sms-textbee/spec.md`
**Status:** Ready for design, pending spec confirmation

---

## Feature Boundary

The SMS worker on the shared dispatch workflow, textbee send, and textbee status webhooks through the callbacks application.

---

## Implementation Decisions

### Provider

- textbee.dev is the first SMS provider, in its hosted form (owner, 2026-11-04; AD-001).

### Verified facts

- Send: `POST /api/v1/gateway/send-sms` with an `x-api-key` header. The response carries `smsBatchId`.
- Events: `MESSAGE_SENT`, `MESSAGE_DELIVERED`, `MESSAGE_FAILED`, `UNKNOWN_STATE`, `MESSAGE_RECEIVED`. `SMS_STATUS_UPDATED` is reserved and not emitted.
- Signature: HMAC-SHA256 of the raw body, lowercase hex, in `X-Signature`, with a secret per subscription. No timestamp is signed.
- `idempotencyKey` is unique per delivery and stable across retries of that delivery. A repeated status from the phone gets a new key.
- Order is not guaranteed: `MESSAGE_DELIVERED` can arrive before `MESSAGE_SENT`. `delivered` and `failed` are final.
- Carriers do not always send delivery reports.
- Retries: up to 10 attempts on 5xx, timeout, or network error; up to 3 on 3xx or 4xx. Repeated failure pauses the subscription and sends an email.
- Plans: Free 50 per day and 300 per month with 1 device; Pro 5,000 per month with 5 devices; Scale 25,000 per month with 15 devices.

### Risks the owner should weigh

- Capacity is low compared with a carrier API, and one phone is a single point of failure for its account.
- Hosted textbee stores messages on its servers, in a region it does not state. Content leaves the encrypted path at that point (D-62, D-63).

### Agent's Discretion

None: the owner chose the provider and hosted deployment.

### Declined / Undiscussed Gray Areas → Assumptions

Status mapping, throttle value, and device selection are logged in the spec's Assumptions table.

---

## Specific References

- [Webhooks](https://textbee.dev/docs/webhooks), [Webhook events](https://textbee.dev/docs/webhooks/events), [Delivery status](https://textbee.dev/docs/sending-sms/delivery-status), [FAQ](https://textbee.dev/docs/faq), [OpenAPI](https://textbee.dev/openapi.json)

---

## Deferred Ideas

- Balancing across several devices on one account.
