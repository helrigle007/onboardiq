<!--
title: Payments Overview
url: https://docs.stripe.com/payments
topic: payments
complexity: intermediate
-->

# Payments Overview

Stripe Payments is a complete platform for accepting payments online and in person. At its core, the Stripe payments flow involves creating a PaymentIntent on your server, passing its `client_secret` to your frontend, and confirming the payment with the customer's chosen payment method. This guide covers the full lifecycle of a payment, from creation through capture, along with the various payment methods, authentication requirements, and configuration options available.

---

## Payment Intents API

The Payment Intents API is Stripe's recommended integration path for accepting payments. A `PaymentIntent` object tracks the lifecycle of a payment from creation through final confirmation, handling complex flows like 3D Secure authentication, asynchronous payment methods, and multi-step authorization automatically.

### Creating a PaymentIntent

Create a PaymentIntent on your server when the customer initiates checkout. Specify the `amount` (in the smallest currency unit, such as cents for USD) and `currency`.

```python
import stripe
import os

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

def create_checkout_payment(amount: int, currency: str, customer_id: str = None) -> dict:
    """Create a PaymentIntent for a checkout session."""
    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency=currency,
        customer=customer_id,
        automatic_payment_methods={"enabled": True},
        metadata={
            "order_id": "ord_12345",
            "source": "web_checkout",
        },
    )
    return {
        "client_secret": intent.client_secret,
        "id": intent.id,
        "status": intent.status,
    }

# Example: Create a $50.00 USD payment
result = create_checkout_payment(amount=5000, currency="usd", customer_id="cus_ABC123")
print(result)
# {
#   "client_secret": "pi_ABC123_secret_XYZ789",
#   "id": "pi_ABC123",
#   "status": "requires_payment_method"
# }
```

```javascript
// Node.js
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

app.post('/api/create-payment-intent', async (req, res) => {
  const { amount, currency, customerId } = req.body;

  const paymentIntent = await stripe.paymentIntents.create({
    amount,
    currency,
    customer: customerId,
    automatic_payment_methods: { enabled: true },
    metadata: {
      order_id: 'ord_12345',
      source: 'web_checkout',
    },
  });

  res.json({
    clientSecret: paymentIntent.client_secret,
    id: paymentIntent.id,
  });
});
```

```bash
curl https://api.stripe.com/v1/payment_intents \
  -H "Authorization: Bearer sk_test_51ABC123..." \
  -d amount=5000 \
  -d currency=usd \
  -d customer=cus_ABC123 \
  -d "automatic_payment_methods[enabled]"=true \
  -d "metadata[order_id]"=ord_12345
```

### Confirming a PaymentIntent

After collecting the customer's payment details on the frontend, confirm the PaymentIntent. For card payments using Stripe.js, this is handled client-side:

```javascript
// Frontend: Confirm payment with Stripe.js
const stripe = Stripe('pk_test_51ABC123...');

async function confirmPayment(clientSecret) {
  const { error, paymentIntent } = await stripe.confirmCardPayment(
    clientSecret,
    {
      payment_method: {
        card: cardElement,
        billing_details: {
          name: 'Jenny Rosen',
          email: 'jenny@example.com',
          address: {
            line1: '123 Main St',
            city: 'San Francisco',
            state: 'CA',
            postal_code: '94111',
            country: 'US',
          },
        },
      },
    }
  );

  if (error) {
    // Show error to the customer (e.g., insufficient funds)
    showError(error.message);
  } else if (paymentIntent.status === 'succeeded') {
    // Payment succeeded — show confirmation
    showSuccess(paymentIntent.id);
  } else if (paymentIntent.status === 'requires_action') {
    // 3D Secure authentication is needed — Stripe.js handles this automatically
    console.log('Additional authentication required');
  }
}
```

You can also confirm a PaymentIntent server-side when you already have a saved payment method:

```python
# Server-side confirmation with a saved payment method
payment_intent = stripe.PaymentIntent.create(
    amount=5000,
    currency="usd",
    customer="cus_ABC123",
    payment_method="pm_card_visa",
    confirm=True,                      # Confirm immediately
    off_session=True,                  # Customer is not in the checkout flow
    return_url="https://example.com/return",
)

if payment_intent.status == "succeeded":
    print("Payment completed successfully")
elif payment_intent.status == "requires_action":
    # Customer needs to authenticate — redirect them
    print(f"Redirect to: {payment_intent.next_action.redirect_to_url.url}")
```

---

## PaymentIntent Lifecycle

A PaymentIntent moves through a defined set of statuses as it progresses from creation to completion. Understanding this lifecycle is essential for building a robust payment flow.

### Status State Machine

```
                          +-----------------------+
                          | requires_payment_method|
                          +-----------+-----------+
                                      |
                          (attach payment method)
                                      |
                                      v
                          +-----------+-----------+
                          |   requires_confirmation|
                          +-----------+-----------+
                                      |
                               (confirm)
                                      |
                          +-----------v-----------+
               +----------|    requires_action     |
               |          +-----------+-----------+
               |                      |
          (failed)          (authentication
               |              complete)
               v                      |
        +------+------+   +----------v----------+
        |   canceled   |   |     processing       |
        +-------------+   +----------+----------+
                                      |
                          +-----------+-----------+
                          |                       |
                          v                       v
                  +-------+------+   +-----------+-----------+
                  |  succeeded   |   | requires_capture      |
                  +--------------+   | (manual capture only) |
                                     +-----------+-----------+
                                                 |
                                           (capture)
                                                 |
                                                 v
                                         +-------+------+
                                         |  succeeded   |
                                         +--------------+
```

### Status Descriptions

| Status | Description | Typical Next Steps |
|---|---|---|
| `requires_payment_method` | No payment method attached yet | Collect payment details from customer |
| `requires_confirmation` | Payment method attached, awaiting confirmation | Call `confirm` on client or server |
| `requires_action` | Additional customer action needed (e.g., 3D Secure) | Redirect or display authentication challenge |
| `processing` | Payment is being processed by the network | Wait for async result via webhook |
| `requires_capture` | Authorized but not yet captured (manual capture mode) | Call `capture` to finalize |
| `succeeded` | Payment completed successfully | Fulfill the order |
| `canceled` | PaymentIntent was canceled | No further action needed |

> **Note:** The `processing` status is most common with asynchronous payment methods like bank debits and transfers, where the result is not immediately known. For card payments, the transition from `requires_action` or `requires_confirmation` to `succeeded` is typically instantaneous.

---

## Authorize and Capture

By default, Stripe charges are authorized and captured in a single step. However, you can separate authorization from capture, which is common in e-commerce, travel, and hospitality where the final amount may differ from the initial authorization.

### Authorization Only

Set `capture_method` to `manual` when creating the PaymentIntent:

```python
# Authorize $100.00 without capturing
payment_intent = stripe.PaymentIntent.create(
    amount=10000,
    currency="usd",
    customer="cus_ABC123",
    payment_method="pm_card_visa",
    capture_method="manual",  # Authorize only
    confirm=True,
)

print(payment_intent.status)  # "requires_capture"
print(payment_intent.id)      # "pi_ABC123" — save this for later capture
```

### Capturing an Authorized Payment

Capture the full amount or a partial amount within 7 days of authorization:

```python
# Capture the full authorized amount
captured = stripe.PaymentIntent.capture("pi_ABC123")
print(captured.status)  # "succeeded"

# Capture a partial amount (e.g., $85.00 of $100.00 authorized)
captured = stripe.PaymentIntent.capture(
    "pi_ABC123",
    amount_to_capture=8500,
)
print(captured.amount_received)  # 8500
```

```bash
# Capture via API
curl https://api.stripe.com/v1/payment_intents/pi_ABC123/capture \
  -H "Authorization: Bearer sk_test_51ABC123..." \
  -d amount_to_capture=8500
```

> **Warning:** Uncaptured PaymentIntents automatically expire and are canceled after 7 days. For certain card networks, holding an authorization for the full 7 days may increase the risk of a declined capture. Capture as soon as possible after the authorized service or goods are ready.

### When to Use Manual Capture

| Use Case | Example | Reason |
|---|---|---|
| Pre-orders | Customer orders an item not yet in stock | Capture when item ships |
| Hotels and rentals | Guest books a hotel room | Capture at checkout; adjust for incidentals |
| Restaurants | Authorize card before meal | Capture with tip after meal |
| Marketplace holds | Buyer purchases from seller | Capture after seller confirms shipment |
| Estimated pricing | Ride-share fare estimate | Capture final fare after ride completes |

---

## Payment Methods

Stripe supports a wide range of payment methods. The `automatic_payment_methods` parameter dynamically enables payment methods based on the customer's currency, location, and your Dashboard configuration.

### Card Payments

Card payments are the most common payment method. Stripe supports all major card networks.

| Network | Supported Regions | 3D Secure | Tokenization |
|---|---|---|---|
| Visa | Global | Yes | Apple Pay, Google Pay |
| Mastercard | Global | Yes | Apple Pay, Google Pay |
| American Express | Global | Yes | Apple Pay, Google Pay |
| Discover | US, Canada | Yes | Apple Pay, Google Pay |
| Diners Club | Global | Yes | Limited |
| JCB | Japan, Global | Yes | Limited |
| UnionPay | China, Global | Limited | No |

```python
# Create a payment with a specific card payment method
payment_intent = stripe.PaymentIntent.create(
    amount=2000,
    currency="usd",
    payment_method_types=["card"],
)
```

### Bank Debits and Transfers

| Payment Method | Type | Regions | Confirmation Time | Refund Support |
|---|---|---|---|---|
| ACH Direct Debit | Bank debit | US | 4-5 business days | Yes (up to 60 days) |
| SEPA Direct Debit | Bank debit | EU/EEA | 6-14 business days | Yes (up to 8 weeks) |
| Bacs Direct Debit | Bank debit | UK | 3-4 business days | Yes |
| iDEAL | Bank redirect | Netherlands | Instant | Yes |
| Bancontact | Bank redirect | Belgium | Instant | Yes |
| Sofort | Bank redirect | EU | 2-14 days for confirmation | Yes |
| Przelewy24 (P24) | Bank redirect | Poland | Instant | Yes |

```python
# Create a payment supporting bank redirects
payment_intent = stripe.PaymentIntent.create(
    amount=2000,
    currency="eur",
    payment_method_types=["ideal", "bancontact", "sepa_debit"],
)
```

### Wallets

| Wallet | Platforms | Integration |
|---|---|---|
| Apple Pay | iOS, Safari, macOS | Stripe.js / Payment Request Button |
| Google Pay | Android, Chrome | Stripe.js / Payment Request Button |
| Link | Cross-platform | Automatic with Payment Element |
| WeChat Pay | China | QR code or in-app |
| Alipay | China, Global | Redirect |

```javascript
// Payment Request Button for Apple Pay / Google Pay
const paymentRequest = stripe.paymentRequest({
  country: 'US',
  currency: 'usd',
  total: {
    label: 'Order Total',
    amount: 5000,
  },
  requestPayerName: true,
  requestPayerEmail: true,
});

const prButton = elements.create('paymentRequestButton', {
  paymentRequest,
});

// Check if Apple Pay or Google Pay is available
const result = await paymentRequest.canMakePayment();
if (result) {
  prButton.mount('#payment-request-button');
} else {
  document.getElementById('payment-request-button').style.display = 'none';
}
```

---

## Charges API vs Payment Intents

The Charges API is Stripe's original payments API. While still functional, Stripe recommends the Payment Intents API for all new integrations.

| Feature | Charges API | Payment Intents API |
|---|---|---|
| SCA / 3D Secure | Manual handling | Built-in support |
| Asynchronous payment methods | Not supported | Fully supported |
| Multi-step authentication | Not supported | Automatic redirects |
| Saved payment methods | Via tokens | Via PaymentMethods |
| Webhooks | `charge.succeeded` | `payment_intent.succeeded` |
| Status tracking | Limited | Full lifecycle tracking |
| Recommended for new code | No | Yes |

```python
# Legacy: Charges API (not recommended for new integrations)
charge = stripe.Charge.create(
    amount=2000,
    currency="usd",
    source="tok_visa",  # Token-based (legacy)
    description="Legacy charge",
)

# Modern: Payment Intents API (recommended)
payment_intent = stripe.PaymentIntent.create(
    amount=2000,
    currency="usd",
    payment_method="pm_card_visa",  # PaymentMethod-based
    confirm=True,
)
```

> **Note:** If you are migrating from the Charges API to Payment Intents, see the [Migration Guide](https://docs.stripe.com/payments/payment-intents/migration). Existing Charges API integrations continue to work, but they do not support SCA or newer payment methods.

---

## 3D Secure and Strong Customer Authentication (SCA)

Strong Customer Authentication (SCA) is a European regulatory requirement under PSD2 that mandates multi-factor authentication for many online payments. Stripe handles SCA through 3D Secure (3DS), an authentication protocol supported by Visa, Mastercard, and other card networks.

### How 3D Secure Works with Payment Intents

1. Your server creates a PaymentIntent.
2. The customer submits their card details on the frontend.
3. Stripe.js confirms the payment. If 3DS is required, Stripe automatically presents an authentication challenge (pop-up or redirect).
4. The customer completes authentication with their bank.
5. Stripe finalizes the payment. The PaymentIntent status moves to `succeeded` or `requires_capture`.

```python
# Server-side: Request 3D Secure when appropriate
payment_intent = stripe.PaymentIntent.create(
    amount=5000,
    currency="eur",
    payment_method="pm_card_threeDSecure2Required",
    confirmation_method="manual",
)

# When you confirm, Stripe determines if 3DS is needed
confirmed = stripe.PaymentIntent.confirm(
    payment_intent.id,
    return_url="https://example.com/return",
)

if confirmed.status == "requires_action":
    # Customer must complete 3D Secure
    redirect_url = confirmed.next_action.redirect_to_url.url
    print(f"Redirect customer to: {redirect_url}")
elif confirmed.status == "succeeded":
    print("Payment succeeded without 3DS")
```

### 3D Secure Request Preferences

You can influence when 3D Secure is requested by setting `request_three_d_secure` on the PaymentIntent or in Radar rules:

| Setting | Behavior |
|---|---|
| `automatic` (default) | Stripe uses Radar and issuer signals to determine if 3DS is needed |
| `any` | Always request 3DS if the card supports it |
| `challenge` | Request a challenge flow (not frictionless) for higher assurance |

> **Warning:** Requiring 3D Secure on every transaction increases friction and may reduce conversion rates. Use `automatic` unless your business or regulatory requirements demand otherwise.

### Exemptions

Certain transactions may qualify for SCA exemptions, which Stripe can request automatically:

| Exemption | Criteria | Example |
|---|---|---|
| Low-value | Transaction under 30 EUR | Small digital purchases |
| Transaction Risk Analysis (TRA) | Low fraud rate on your account | Established merchants |
| Merchant-initiated | Recurring payments after initial auth | Subscription renewals |
| Trusted beneficiary | Customer has whitelisted your business | Repeat customers |

---

## Currency Handling

Stripe processes payments in over 135 currencies. Amounts are specified in the smallest currency unit (cents, pence, yen, etc.).

### Zero-Decimal Currencies

Most currencies have a smallest unit that is 1/100th of the standard unit. However, some currencies are "zero-decimal" -- the amount you pass is the actual charge amount.

| Currency | Decimal Type | $50 Equivalent |
|---|---|---|
| USD (US Dollar) | Two-decimal | `amount: 5000` |
| EUR (Euro) | Two-decimal | `amount: 5000` |
| GBP (British Pound) | Two-decimal | `amount: 5000` |
| JPY (Japanese Yen) | Zero-decimal | `amount: 5000` (5000 yen) |
| KRW (Korean Won) | Zero-decimal | `amount: 65000` (65,000 won) |
| BIF (Burundian Franc) | Zero-decimal | `amount: 50` |

```python
# Two-decimal currency: USD
usd_payment = stripe.PaymentIntent.create(
    amount=5000,    # $50.00
    currency="usd",
)

# Zero-decimal currency: JPY
jpy_payment = stripe.PaymentIntent.create(
    amount=5000,    # 5,000 yen
    currency="jpy",
)
```

> **Warning:** Passing the wrong amount for zero-decimal currencies is a common mistake. For example, setting `amount=5000` for JPY charges 5,000 yen (approximately $33 USD), not 50 yen. Always check the [currency documentation](https://docs.stripe.com/currencies) when adding support for a new currency.

### Currency Conversion

Stripe can automatically convert currencies for settlements. If you charge in EUR but your payout currency is USD, Stripe converts the funds at the current exchange rate plus a conversion fee (typically 1%).

```python
# Check the exchange rate applied to a charge
charge = stripe.Charge.retrieve("ch_1ABC123")

if charge.balance_transaction:
    bt = stripe.BalanceTransaction.retrieve(charge.balance_transaction)
    print(f"Original amount: {charge.amount} {charge.currency}")
    print(f"Converted amount: {bt.amount} {bt.currency}")
    print(f"Exchange rate: {bt.exchange_rate}")
    print(f"Fee: {bt.fee} {bt.currency}")
```

---

## Payment Status and Webhooks

While you can poll the PaymentIntent status, Stripe strongly recommends using webhooks for payment status updates. Webhooks are server-to-server HTTP POST requests that Stripe sends when an event occurs.

### Key Payment Webhooks

| Event | When It Fires | Typical Action |
|---|---|---|
| `payment_intent.created` | PaymentIntent is created | Log the intent |
| `payment_intent.requires_action` | Customer authentication needed | Wait for customer action |
| `payment_intent.processing` | Payment is being processed | Show "processing" UI |
| `payment_intent.succeeded` | Payment completed successfully | Fulfill the order |
| `payment_intent.payment_failed` | Payment attempt failed | Notify customer; retry |
| `payment_intent.canceled` | PaymentIntent was canceled | Update order status |
| `charge.succeeded` | Charge completed (legacy and new) | Fulfill the order |
| `charge.refunded` | Charge was refunded | Process refund in your system |
| `charge.dispute.created` | Customer initiated a dispute | Respond with evidence |

```python
import stripe
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.environ["STRIPE_WEBHOOK_SECRET"]

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook")

    match event["type"]:
        case "payment_intent.succeeded":
            intent = event["data"]["object"]
            await fulfill_order(intent["id"], intent["metadata"])

        case "payment_intent.payment_failed":
            intent = event["data"]["object"]
            error = intent["last_payment_error"]
            await notify_customer_payment_failed(
                intent["id"],
                error["message"] if error else "Unknown error",
            )

        case "charge.dispute.created":
            dispute = event["data"]["object"]
            await flag_dispute_for_review(dispute["id"])

    return {"status": "ok"}
```

---

## Metadata and Receipts

### Metadata

Every Stripe object supports up to 50 key-value metadata pairs (keys up to 40 characters, values up to 500 characters). Use metadata to attach your internal identifiers to Stripe objects.

```python
payment_intent = stripe.PaymentIntent.create(
    amount=5000,
    currency="usd",
    metadata={
        "order_id": "ord_12345",
        "customer_email": "jenny@example.com",
        "plan": "premium",
        "referral_code": "FRIEND20",
    },
)

# Later, retrieve and read metadata
intent = stripe.PaymentIntent.retrieve("pi_ABC123")
order_id = intent.metadata.get("order_id")
```

### Receipts

Stripe can automatically send email receipts when a payment succeeds. Enable this by providing the customer's email:

```python
payment_intent = stripe.PaymentIntent.create(
    amount=5000,
    currency="usd",
    receipt_email="jenny@example.com",
    description="Premium plan subscription",
    statement_descriptor="MYAPP PREMIUM",    # Appears on bank statement (22 chars max)
    statement_descriptor_suffix="PLAN",       # Appended to descriptor (up to 22 chars)
)
```

| Receipt Setting | Description | Limit |
|---|---|---|
| `receipt_email` | Email address for the receipt | Valid email |
| `description` | Internal description (visible in Dashboard) | No limit |
| `statement_descriptor` | Text on customer's bank statement | 22 characters |
| `statement_descriptor_suffix` | Appended to your account's default descriptor | 22 characters |

---

## Idempotency

When creating payments, network errors can make it unclear whether a request succeeded. Use idempotency keys to safely retry requests without creating duplicate payments.

```python
import uuid

idempotency_key = str(uuid.uuid4())

payment_intent = stripe.PaymentIntent.create(
    amount=5000,
    currency="usd",
    customer="cus_ABC123",
    idempotency_key=idempotency_key,
)

# Retrying with the same key returns the original result
# instead of creating a new PaymentIntent
retry_result = stripe.PaymentIntent.create(
    amount=5000,
    currency="usd",
    customer="cus_ABC123",
    idempotency_key=idempotency_key,
)

assert payment_intent.id == retry_result.id  # Same object
```

```bash
curl https://api.stripe.com/v1/payment_intents \
  -H "Authorization: Bearer sk_test_51ABC123..." \
  -H "Idempotency-Key: unique-key-12345" \
  -d amount=5000 \
  -d currency=usd
```

> **Note:** Idempotency keys expire after 24 hours. After that, a request with the same key creates a new object. Always generate a new key for each distinct business operation.

---

## Error Handling

Payment failures are a normal part of processing. Handle them gracefully to provide a good customer experience.

### Common Payment Error Codes

| Code | Meaning | Customer-Facing Message |
|---|---|---|
| `card_declined` | The card was declined | "Your card was declined. Please try a different card." |
| `insufficient_funds` | Not enough funds | "Your card has insufficient funds." |
| `expired_card` | Card has expired | "Your card has expired. Please update your card." |
| `incorrect_cvc` | CVC check failed | "The CVC number is incorrect." |
| `processing_error` | Temporary processing issue | "An error occurred processing your card. Please try again." |
| `authentication_required` | SCA authentication needed | Stripe.js handles this automatically |
| `payment_intent_unexpected_state` | Invalid state transition | Check PaymentIntent status before acting |

```python
import stripe

def process_payment(amount: int, currency: str, payment_method: str) -> dict:
    """Process a payment with comprehensive error handling."""
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            confirm=True,
        )
        return {"status": "succeeded", "id": intent.id}

    except stripe.error.CardError as e:
        error = e.error
        return {
            "status": "failed",
            "code": error.code,
            "decline_code": error.decline_code,
            "message": error.message,
        }

    except stripe.error.InvalidRequestError as e:
        # Invalid parameters (e.g., negative amount)
        return {"status": "error", "message": str(e)}

    except stripe.error.APIConnectionError:
        # Network error — safe to retry with idempotency key
        return {"status": "retry", "message": "Network error. Please try again."}

    except stripe.error.StripeError as e:
        # Catch-all for other Stripe errors
        return {"status": "error", "message": "An unexpected error occurred."}
```

---

## Related Resources

- [Payment Intents API Reference](https://docs.stripe.com/api/payment_intents) -- Full API reference
- [Payment Methods](https://docs.stripe.com/payments/payment-methods) -- All supported payment methods
- [Webhooks](https://docs.stripe.com/webhooks) -- Listen for payment events
- [Testing](https://docs.stripe.com/testing) -- Test cards and scenarios
- [Strong Customer Authentication](https://docs.stripe.com/strong-customer-authentication) -- SCA compliance guide
- [Currencies](https://docs.stripe.com/currencies) -- Supported currencies and formatting
- [Disputes and Fraud](https://docs.stripe.com/disputes) -- Handle chargebacks
- [Connect Payments](https://docs.stripe.com/connect/charges) -- Payments for platforms and marketplaces
