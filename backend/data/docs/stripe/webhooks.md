<!--
title: Webhooks
url: https://docs.stripe.com/webhooks
topic: webhooks
complexity: intermediate
-->

# Webhooks

Listen for events on your Stripe account so your integration can automatically trigger reactions.

Stripe uses webhooks to notify your application when an event happens in your account. Webhooks are particularly useful for asynchronous events like when a customer's bank confirms a payment, a customer disputes a charge, a recurring payment succeeds, or when collecting subscription payments.

## How webhooks work

A webhook is an HTTP POST request sent from Stripe to your server whenever a specific event occurs. When an event is triggered — for example, when a charge succeeds — Stripe creates an **Event** object. This object contains all the relevant information about what just happened, including the type of event and the data associated with it.

Stripe then sends the Event object in the body of an HTTP POST request to any endpoint URLs that you have configured in your webhook settings.

### Webhook lifecycle

1. An event occurs in your Stripe account (e.g., a successful payment).
2. Stripe generates an `Event` object.
3. Stripe sends the `Event` via HTTP POST to each configured endpoint.
4. Your server receives the POST request, verifies the signature, and processes the event.
5. Your server returns a `2xx` status code to acknowledge receipt.
6. If Stripe does not receive a `2xx` response, it retries the delivery with exponential backoff.

## Event types

Stripe generates events for a wide range of activities. Below are the most commonly used event types.

### Payment events

| Event Type | Description |
|---|---|
| `payment_intent.succeeded` | A PaymentIntent was successfully confirmed and the payment completed. |
| `payment_intent.payment_failed` | A payment attempt on a PaymentIntent failed. |
| `payment_intent.created` | A new PaymentIntent was created. |
| `payment_intent.canceled` | A PaymentIntent was canceled. |
| `payment_intent.requires_action` | A PaymentIntent transitions to `requires_action` — usually for 3D Secure authentication. |
| `charge.succeeded` | A charge was successfully created. |
| `charge.failed` | A charge attempt failed. |
| `charge.refunded` | A charge was refunded, either partially or fully. |
| `charge.disputed` | A customer initiated a dispute (chargeback) against a charge. |

### Subscription events

| Event Type | Description |
|---|---|
| `customer.subscription.created` | A new subscription was created. |
| `customer.subscription.updated` | A subscription was changed (e.g., plan switch, quantity update). |
| `customer.subscription.deleted` | A subscription was canceled or expired. |
| `customer.subscription.trial_will_end` | A subscription trial period will end in 3 days. |
| `invoice.payment_succeeded` | An invoice payment completed successfully. |
| `invoice.payment_failed` | An invoice payment attempt failed. |
| `invoice.finalized` | An invoice was finalized and is ready for payment. |

### Customer events

| Event Type | Description |
|---|---|
| `customer.created` | A new Customer object was created. |
| `customer.updated` | A Customer object was updated. |
| `customer.deleted` | A Customer object was deleted. |
| `customer.source.created` | A new payment source was added to a customer. |

### Checkout events

| Event Type | Description |
|---|---|
| `checkout.session.completed` | A Checkout Session was successfully completed. |
| `checkout.session.expired` | A Checkout Session has expired (default: 24 hours). |
| `checkout.session.async_payment_succeeded` | An async payment (e.g., bank debit) on a Checkout Session was confirmed. |
| `checkout.session.async_payment_failed` | An async payment on a Checkout Session failed. |

> **Note:** You can find the full list of event types in the [Stripe API reference](https://docs.stripe.com/api/events/types). There are over 200 event types available.

## Event object structure

Every webhook payload is a JSON-serialized `Event` object. Understanding its structure is essential for building reliable webhook handlers.

```json
{
  "id": "evt_1NxBKa2eZvKYlo2CbTdAqEWO",
  "object": "event",
  "api_version": "2023-10-16",
  "created": 1695152462,
  "type": "payment_intent.succeeded",
  "livemode": false,
  "pending_webhooks": 1,
  "request": {
    "id": "req_aBcDeFgHiJkLm",
    "idempotency_key": "key_abc123"
  },
  "data": {
    "object": {
      "id": "pi_3NxBKa2eZvKYlo2C1cuHfJKs",
      "object": "payment_intent",
      "amount": 2000,
      "currency": "usd",
      "status": "succeeded",
      "payment_method": "pm_1NxBKZ2eZvKYlo2CYzzldNrk",
      "customer": "cus_OjK9l2eZvKYlo2C",
      "metadata": {
        "order_id": "order_12345"
      }
    },
    "previous_attributes": {}
  }
}
```

### Key fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier for the event. Use this for deduplication. |
| `type` | string | Description of the event (e.g., `payment_intent.succeeded`). |
| `api_version` | string | The Stripe API version used to render `data`. |
| `created` | integer | Timestamp (Unix epoch) of when the event was created. |
| `livemode` | boolean | `true` if the event occurred in live mode, `false` for test mode. |
| `data.object` | object | The full API resource relevant to the event at the time of the event. |
| `data.previous_attributes` | object | For `*.updated` events, the previous values of updated attributes. |
| `pending_webhooks` | integer | Number of webhooks yet to be delivered for this event. |
| `request.id` | string | The API request ID that triggered this event, if applicable. |
| `request.idempotency_key` | string | The idempotency key of the request that triggered this event. |

## Configuring webhook endpoints

You can configure webhook endpoints through the Stripe Dashboard or programmatically via the API.

### Via the Dashboard

1. Navigate to [Developers > Webhooks](https://dashboard.stripe.com/webhooks).
2. Click **Add endpoint**.
3. Enter your endpoint URL (must be HTTPS in live mode).
4. Select the events you want to listen to.
5. Click **Add endpoint** to save.

### Via the API

You can create, update, and delete webhook endpoints using the `POST /v1/webhook_endpoints` API.

```bash
curl https://api.stripe.com/v1/webhook_endpoints \
  -u sk_test_EXAMPLE_KEY_REPLACE_ME: \
  -d url="https://example.com/webhooks/stripe" \
  -d "enabled_events[]"="payment_intent.succeeded" \
  -d "enabled_events[]"="payment_intent.payment_failed" \
  -d "enabled_events[]"="charge.refunded"
```

**Response:**

```json
{
  "id": "we_1NxBKa2eZvKYlo2CxPM2fjOl",
  "object": "webhook_endpoint",
  "url": "https://example.com/webhooks/stripe",
  "status": "enabled",
  "enabled_events": [
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
    "charge.refunded"
  ],
  "secret": "whsec_abc123...",
  "api_version": "2023-10-16",
  "created": 1695152462
}
```

> **Important:** Store the `secret` value returned when you create the endpoint. You will need it to verify webhook signatures. This value is only shown once.

### Updating an endpoint

```bash
curl https://api.stripe.com/v1/webhook_endpoints/we_1NxBKa2eZvKYlo2CxPM2fjOl \
  -u sk_test_EXAMPLE_KEY_REPLACE_ME: \
  -d "enabled_events[]"="payment_intent.succeeded" \
  -d "enabled_events[]"="customer.subscription.deleted"
```

### Deleting an endpoint

```bash
curl -X DELETE https://api.stripe.com/v1/webhook_endpoints/we_1NxBKa2eZvKYlo2CxPM2fjOl \
  -u sk_test_EXAMPLE_KEY_REPLACE_ME:
```

## Webhook signatures and verification

Stripe signs every webhook event it sends to your endpoints. Verifying these signatures is critical to ensure that the events were actually sent by Stripe and not by a malicious third party.

### How signature verification works

Each webhook endpoint has a unique signing secret (prefixed with `whsec_`). When Stripe sends an event to your endpoint, it includes a `Stripe-Signature` header containing a timestamp and one or more signatures.

The `Stripe-Signature` header has the following format:

```
Stripe-Signature: t=1695152462,v1=abc123def456...,v0=ghi789...
```

- `t` — The timestamp of when Stripe generated the signature (Unix epoch).
- `v1` — The signature generated using the current signing scheme (HMAC with SHA-256).
- `v0` — Signatures generated using a previous signing scheme (deprecated).

### Verification steps

1. Extract the timestamp and signatures from the `Stripe-Signature` header.
2. Construct the signed payload string: `{timestamp}.{raw_request_body}`.
3. Compute the expected signature using HMAC-SHA256 with your endpoint's signing secret.
4. Compare the computed signature with the `v1` signature from the header.
5. Optionally, compare the timestamp to the current time and reject events older than a tolerance threshold (e.g., 5 minutes) to prevent replay attacks.

### Python verification

Using the official `stripe` Python library:

```python
import stripe
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

endpoint_secret = "whsec_abc123..."

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        handle_payment_success(payment_intent)
    elif event["type"] == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        handle_payment_failure(payment_intent)
    elif event["type"] == "charge.refunded":
        charge = event["data"]["object"]
        handle_refund(charge)
    else:
        print(f"Unhandled event type: {event['type']}")

    return {"status": "success"}
```

### Node.js verification

Using the official `stripe` Node.js library:

```javascript
const stripe = require('stripe')('sk_test_...');
const express = require('express');
const app = express();

const endpointSecret = 'whsec_abc123...';

// Stripe requires the raw body to verify webhook signatures.
// Use express.raw() instead of express.json() for the webhook route.
app.post(
  '/webhooks/stripe',
  express.raw({ type: 'application/json' }),
  (req, res) => {
    const sig = req.headers['stripe-signature'];

    let event;

    try {
      event = stripe.webhooks.constructEvent(req.body, sig, endpointSecret);
    } catch (err) {
      console.error(`Webhook signature verification failed: ${err.message}`);
      return res.status(400).send(`Webhook Error: ${err.message}`);
    }

    // Handle the event
    switch (event.type) {
      case 'payment_intent.succeeded':
        const paymentIntent = event.data.object;
        console.log(`PaymentIntent ${paymentIntent.id} succeeded.`);
        // Fulfill the purchase, update your database, send a receipt, etc.
        break;
      case 'payment_intent.payment_failed':
        const failedIntent = event.data.object;
        console.log(`PaymentIntent ${failedIntent.id} failed.`);
        // Notify the customer and prompt for a different payment method.
        break;
      case 'charge.refunded':
        const charge = event.data.object;
        console.log(`Charge ${charge.id} was refunded.`);
        break;
      default:
        console.log(`Unhandled event type: ${event.type}`);
    }

    res.json({ received: true });
  }
);

app.listen(4242, () => console.log('Running on port 4242'));
```

> **Warning:** Always verify webhook signatures before processing events. Without verification, an attacker could send fabricated events to your endpoint, potentially triggering unintended actions such as provisioning access to unpaid services.

## Retry logic and delivery guarantees

Stripe guarantees **at-least-once** delivery of webhook events. If your endpoint does not return a `2xx` HTTP status code within the timeout window, Stripe retries delivery.

### Retry schedule

Stripe uses an exponential backoff strategy for retries. The approximate schedule is:

| Attempt | Delay after previous attempt |
|---|---|
| 1st retry | ~5 minutes |
| 2nd retry | ~30 minutes |
| 3rd retry | ~2 hours |
| 4th retry | ~5 hours |
| 5th retry | ~10 hours |
| 6th retry | ~18 hours |
| 7th retry (final) | ~36 hours |

After all retries are exhausted (approximately 3 days from the original attempt), the event is marked as failed and no further delivery attempts are made.

### Timeout behavior

Your endpoint must return a response within **20 seconds**. If Stripe does not receive a response within this window, it treats the delivery as failed and schedules a retry.

> **Best practice:** Return a `200` response immediately after verifying the signature and before doing any heavy processing. Use a background job queue (e.g., Celery, Bull, Sidekiq) to handle the actual business logic asynchronously.

### Endpoint status

Stripe tracks the health of each webhook endpoint. If an endpoint consistently fails to respond with a `2xx` code, Stripe may disable it and send you an email notification. Endpoint states include:

- **Enabled** — Actively receiving events.
- **Disabled** — Manually disabled by you, or automatically disabled by Stripe after persistent failures.

You can monitor endpoint health in the Dashboard under **Developers > Webhooks**, where you can see recent deliveries, response codes, and error messages.

## Handling duplicate events and idempotency

Because Stripe guarantees at-least-once delivery, your webhook handler **must be idempotent**. The same event may be delivered more than once due to network issues or retry logic.

### Strategies for idempotency

**1. Track processed event IDs**

Store the `event.id` of every event you process. Before processing a new event, check whether you have already handled it:

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def stripe_webhook(request: Request):
    # ... signature verification ...

    event_id = event["id"]

    # Check if we already processed this event
    if redis_client.get(f"stripe_event:{event_id}"):
        return {"status": "already_processed"}

    # Process the event
    await process_event(event)

    # Mark as processed with a TTL (e.g., 7 days)
    redis_client.setex(f"stripe_event:{event_id}", 604800, "processed")

    return {"status": "success"}
```

**2. Use idempotent database operations**

Design your database operations to produce the same result when executed multiple times:

```python
# BAD: This is not idempotent — it increments on every call
async def handle_payment(payment_intent):
    await db.execute(
        "UPDATE accounts SET balance = balance + :amount WHERE id = :id",
        {"amount": payment_intent["amount"], "id": account_id}
    )

# GOOD: This is idempotent — it uses the payment intent ID as a unique key
async def handle_payment(payment_intent):
    await db.execute("""
        INSERT INTO payments (stripe_payment_intent_id, amount, status)
        VALUES (:pi_id, :amount, 'succeeded')
        ON CONFLICT (stripe_payment_intent_id) DO NOTHING
    """, {"pi_id": payment_intent["id"], "amount": payment_intent["amount"]})
```

**3. Check resource state**

Before modifying a resource, check whether it is already in the desired state:

```python
async def handle_subscription_canceled(subscription):
    existing = await db.fetch_one(
        "SELECT status FROM subscriptions WHERE stripe_id = :id",
        {"id": subscription["id"]}
    )
    if existing and existing["status"] == "canceled":
        return  # Already handled
    await db.execute(
        "UPDATE subscriptions SET status = 'canceled' WHERE stripe_id = :id",
        {"id": subscription["id"]}
    )
```

## Testing webhooks with the Stripe CLI

The Stripe CLI is the recommended way to test webhooks during development. It creates a secure tunnel between Stripe and your local server.

### Installation

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Linux (Debian/Ubuntu)
apt-get install stripe

# Windows
scoop install stripe
```

### Forwarding events to your local server

```bash
# Log in to your Stripe account
stripe login

# Forward events to your local endpoint
stripe listen --forward-to localhost:8000/webhooks/stripe
```

The CLI outputs a webhook signing secret (starting with `whsec_`). Use this secret in your application for local development.

```
> Ready! Your webhook signing secret is whsec_1234567890abcdef (^C to quit)
```

### Triggering test events

```bash
# Trigger a specific event type
stripe trigger payment_intent.succeeded

# Trigger a checkout session completion
stripe trigger checkout.session.completed

# Trigger a subscription lifecycle
stripe trigger customer.subscription.updated
```

### Filtering events

```bash
# Only forward specific event types
stripe listen --forward-to localhost:8000/webhooks/stripe \
  --events payment_intent.succeeded,payment_intent.payment_failed,charge.refunded
```

### Viewing event logs

```bash
# View recent events
stripe events list --limit 10

# View details of a specific event
stripe events retrieve evt_1NxBKa2eZvKYlo2CbTdAqEWO
```

## Best practices for webhook handlers

### 1. Return 2xx quickly

Return a `200` or `202` response as soon as you have verified the webhook signature. Offload time-consuming processing (sending emails, updating external systems, running complex queries) to a background job.

```python
from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379/0')

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    # Verify signature...
    event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)

    # Enqueue for async processing
    process_stripe_event.delay(event)

    # Return immediately
    return {"status": "received"}

@celery_app.task
def process_stripe_event(event):
    if event["type"] == "payment_intent.succeeded":
        # Complex processing here...
        pass
```

### 2. Handle events you do not recognize

Your handler should gracefully ignore event types it does not explicitly handle. Stripe may introduce new event types at any time, and your handler should not break when this happens.

```python
def process_event(event):
    handler = EVENT_HANDLERS.get(event["type"])
    if handler:
        handler(event["data"]["object"])
    else:
        logger.info(f"Received unhandled event type: {event['type']}")
```

### 3. Use the event object, not the API

When you receive a webhook event, use the data contained in `event.data.object` rather than making a separate API call to fetch the resource. The event object represents the resource at the exact moment the event was triggered.

> **Exception:** If your webhook processing is significantly delayed (e.g., via a background queue), the resource may have changed since the event was created. In those cases, it may be appropriate to fetch the latest state from the API.

### 4. Register only for events you need

Do not register for all event types (`*`). Instead, subscribe only to the specific events your application needs. This reduces the volume of HTTP traffic to your endpoint and makes your code easier to reason about.

### 5. Secure your endpoint

- Always verify webhook signatures.
- Use HTTPS in production (Stripe requires it for live-mode endpoints).
- Restrict access to your webhook endpoint by IP if possible. Stripe publishes its webhook IP ranges.
- Do not expose sensitive information in webhook responses — Stripe does not inspect response bodies.

### 6. Monitor webhook deliveries

Set up alerting for failed webhook deliveries. You can monitor delivery status in the Stripe Dashboard or programmatically by listening to the `webhook_endpoint.disabled` event type (sent via email if no working endpoint is available).

### 7. Handle event ordering

Events may not arrive in the order they occurred. For example, you might receive `invoice.payment_succeeded` before `invoice.created`. Design your handlers to be resilient to out-of-order delivery.

```python
async def handle_invoice_paid(invoice):
    # Ensure the invoice exists in your database before marking it paid.
    # If it doesn't exist yet, create it first.
    existing = await db.fetch_one(
        "SELECT id FROM invoices WHERE stripe_id = :id",
        {"id": invoice["id"]}
    )
    if not existing:
        await create_invoice_record(invoice)
    await mark_invoice_paid(invoice["id"])
```

## Error handling in webhook endpoints

Proper error handling ensures your webhook endpoint is reliable and does not lose events.

### Distinguish retriable vs. permanent errors

- **Retriable errors** (database timeout, network blip): Return a `5xx` status code so Stripe retries.
- **Permanent errors** (invalid data, business logic violation): Return a `2xx` code but log the error. Retrying will not fix the issue.

```python
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook")

    try:
        await process_event(event)
    except TransientError:
        # Return 500 so Stripe retries
        raise HTTPException(status_code=500, detail="Temporary failure")
    except PermanentError as e:
        # Log the error, but return 200 so Stripe does not retry
        logger.error(f"Permanent error processing {event['id']}: {e}")
        return {"status": "error_logged"}

    return {"status": "success"}
```

### Log everything

Log the full event payload, the event ID, and any errors that occur during processing. This makes debugging significantly easier when something goes wrong.

```python
import structlog

logger = structlog.get_logger()

async def process_event(event):
    logger.info(
        "processing_webhook_event",
        event_id=event["id"],
        event_type=event["type"],
        livemode=event["livemode"],
    )
    try:
        handler = get_handler(event["type"])
        await handler(event["data"]["object"])
        logger.info("webhook_event_processed", event_id=event["id"])
    except Exception as e:
        logger.error(
            "webhook_event_failed",
            event_id=event["id"],
            event_type=event["type"],
            error=str(e),
        )
        raise
```

## Webhook IP addresses

In production, you can optionally restrict incoming traffic to your webhook endpoint to Stripe's published IP ranges. Stripe publishes a list of IP addresses from which webhook deliveries originate:

- `3.18.12.63`
- `3.130.192.163`
- `13.235.14.237`
- `13.235.122.149`
- `18.211.135.69`
- `35.154.171.200`
- `52.15.183.38`
- `54.88.130.119`
- `54.88.130.237`
- `54.187.174.169`
- `54.187.205.235`
- `54.187.216.72`

> **Note:** This list is subject to change. Check [Stripe's documentation](https://docs.stripe.com/ips) for the most current set of IP addresses.

## Summary

Webhooks are the backbone of reliable Stripe integrations. By following the patterns outlined in this guide — verifying signatures, handling idempotency, returning responses quickly, and building resilience against out-of-order and duplicate deliveries — you can build a webhook handler that is robust, secure, and production-ready.
