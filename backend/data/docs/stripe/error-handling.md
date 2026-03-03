<!--
title: Error Handling
url: https://docs.stripe.com/error-handling
topic: errors
complexity: intermediate
-->

# Error Handling

Gracefully handle errors from the Stripe API to build a resilient integration.

Stripe uses conventional HTTP response codes to indicate the success or failure of an API request. Codes in the `2xx` range indicate success, codes in the `4xx` range indicate an error caused by information provided in the request (e.g., a required parameter was missing, a charge failed, etc.), and codes in the `5xx` range indicate an error on Stripe's servers.

Understanding how to properly catch, classify, and respond to these errors is essential for building a production-quality Stripe integration.

## HTTP status codes

Stripe returns the following HTTP status codes:

| Status Code | Meaning |
|---|---|
| `200 - OK` | The request succeeded. |
| `400 - Bad Request` | The request was unacceptable, often due to a missing required parameter. |
| `401 - Unauthorized` | No valid API key was provided. |
| `402 - Request Failed` | The parameters were valid but the request failed (e.g., card declined). |
| `403 - Forbidden` | The API key does not have permission to perform the request. |
| `404 - Not Found` | The requested resource does not exist. |
| `409 - Conflict` | The request conflicts with another request (idempotency key reuse with different parameters). |
| `429 - Too Many Requests` | Too many requests hit the API too quickly. You are being rate limited. |
| `500, 502, 503 - Server Errors` | Something went wrong on Stripe's end. These are rare. |

## Error response structure

All Stripe API errors return a JSON body with a consistent structure. The top-level object contains an `error` key with the error details.

```json
{
  "error": {
    "type": "card_error",
    "code": "card_declined",
    "decline_code": "insufficient_funds",
    "message": "Your card has insufficient funds.",
    "param": null,
    "charge": "ch_3NxBKa2eZvKYlo2C0iCx1234",
    "payment_intent": {
      "id": "pi_3NxBKa2eZvKYlo2C1cuHfJKs",
      "status": "requires_payment_method"
    },
    "payment_method": {
      "id": "pm_1NxBKZ2eZvKYlo2CYzzldNrk",
      "type": "card"
    },
    "doc_url": "https://docs.stripe.com/error-codes/card-declined"
  }
}
```

### Error object fields

| Field | Type | Description |
|---|---|---|
| `type` | string | The type of error. See [Error types](#error-types) below. |
| `code` | string | A short string identifying the specific error. See [Error codes](#error-codes). |
| `decline_code` | string | For card errors, the decline code from the card issuer. |
| `message` | string | A human-readable description of the error. Not intended for programmatic use — may change without notice. |
| `param` | string | If the error is related to a specific parameter, this field names the parameter. |
| `charge` | string | For card errors from a charge, the ID of the failed charge. |
| `payment_intent` | object | For errors on a PaymentIntent, the PaymentIntent object in its current state. |
| `payment_method` | object | For card errors, the PaymentMethod object related to the error. |
| `doc_url` | string | A URL to the Stripe documentation page for this specific error code. |

## Error types

The `type` field categorizes the error at a high level. Your application should use this field as the primary basis for routing error handling logic.

### `api_error`

An unexpected error occurred on Stripe's side. These are rare and typically transient. You should retry the request with exponential backoff.

**HTTP status:** `500`, `502`, `503`

```json
{
  "error": {
    "type": "api_error",
    "message": "An unexpected error occurred. Please retry your request."
  }
}
```

### `card_error`

The card could not be charged for some reason. This is the most common error type you will encounter. These errors carry a `code` and often a `decline_code` that provides more detail about why the card was declined.

**HTTP status:** `402`

```json
{
  "error": {
    "type": "card_error",
    "code": "card_declined",
    "decline_code": "generic_decline",
    "message": "Your card was declined."
  }
}
```

### `idempotency_error`

You used an idempotency key with parameters that differ from a previous request using the same key. Each idempotency key must be used with identical parameters.

**HTTP status:** `409`

```json
{
  "error": {
    "type": "idempotency_error",
    "message": "Keys for idempotent requests can only be used with the same parameters they were first used with."
  }
}
```

### `invalid_request_error`

The request had invalid parameters or was otherwise malformed. Common causes include missing required fields, invalid parameter types, and referencing resources that do not exist.

**HTTP status:** `400`, `404`

```json
{
  "error": {
    "type": "invalid_request_error",
    "code": "parameter_missing",
    "param": "amount",
    "message": "Missing required param: amount."
  }
}
```

### `authentication_error`

The API key provided is invalid, expired, or otherwise unable to authenticate the request.

**HTTP status:** `401`

```json
{
  "error": {
    "type": "authentication_error",
    "message": "Invalid API Key provided: sk_test_****1234"
  }
}
```

### `rate_limit_error`

You are sending too many requests to the API in a short period. Stripe enforces rate limits to ensure the stability of the API for all users.

**HTTP status:** `429`

```json
{
  "error": {
    "type": "rate_limit_error",
    "message": "Too many requests. Please retry after a brief wait."
  }
}
```

## Error codes

The `code` field provides a more granular classification of the error. Below are the most common error codes you will encounter.

### Card-specific error codes

| Code | Description |
|---|---|
| `card_declined` | The card was declined. Refer to `decline_code` for more detail. |
| `expired_card` | The card has expired. The customer should use a different card. |
| `incorrect_cvc` | The CVC number is incorrect. |
| `incorrect_number` | The card number is incorrect. |
| `incorrect_zip` | The ZIP/postal code is incorrect. |
| `insufficient_funds` | The card has insufficient funds to complete the purchase. |
| `invalid_cvc` | The CVC number is not valid. |
| `invalid_expiry_month` | The expiration month is invalid. |
| `invalid_expiry_year` | The expiration year is invalid. |
| `invalid_number` | The card number is not a valid credit card number. |
| `processing_error` | An error occurred while processing the card. Retry may succeed. |

### General error codes

| Code | Description |
|---|---|
| `amount_too_large` | The specified amount is greater than the maximum amount allowed. |
| `amount_too_small` | The specified amount is less than the minimum amount allowed. |
| `balance_insufficient` | The Stripe balance is insufficient for this transfer. |
| `country_unsupported` | Your account does not support the specified country. |
| `coupon_expired` | The coupon has expired and can no longer be applied. |
| `email_invalid` | The provided email address is invalid. |
| `parameter_missing` | A required parameter is missing from the request. |
| `parameter_invalid_integer` | A parameter that should be an integer was provided as another type. |
| `parameter_invalid_empty` | A required parameter was provided but is empty. |
| `resource_missing` | The specified resource (ID) does not exist. |
| `resource_already_exists` | A resource with the specified ID already exists. |
| `secret_key_required` | This API endpoint requires a secret key, not a publishable key. |
| `url_invalid` | The URL provided is not valid. |

## Decline codes

When a card is declined (`code: card_declined`), the `decline_code` field contains the reason provided by the card issuer. These codes help you understand why the card was declined and what action the customer should take.

### Common decline codes

| Decline Code | Description | Customer Action |
|---|---|---|
| `generic_decline` | The card was declined for an unspecified reason. | Try another card or contact the bank. |
| `insufficient_funds` | The card has insufficient funds. | Use a different card or add funds. |
| `lost_card` | The card has been reported lost. | Use a different card. |
| `stolen_card` | The card has been reported stolen. | Use a different card. |
| `card_velocity_exceeded` | The customer exceeded the balance or credit limit. | Contact the bank or wait. |
| `do_not_honor` | The card issuer declined for an unspecified reason. | Contact the bank. |
| `fraudulent` | The payment was flagged as likely fraudulent. | Use a different card. |
| `not_permitted` | The payment is not permitted, possibly restricted by the cardholder. | Contact the bank. |
| `pickup_card` | The card cannot be used for this payment. | Contact the bank. |
| `try_again_later` | The issuer returned a temporary error. | Retry after a brief wait. |
| `withdrawal_count_limit_exceeded` | The customer has exceeded their withdrawal limit. | Use a different card or wait. |
| `authentication_required` | The card requires 3D Secure authentication. | Complete the authentication flow. |
| `approve_with_id` | The payment cannot be authorized. | Retry the payment. |

> **Note:** Decline codes are provided by the card issuer and may vary. The `generic_decline` code is the most common and is used when the issuer does not provide a specific reason. For the full list, see [Stripe's decline codes documentation](https://docs.stripe.com/declines/codes).

## Handling errors in code

### Python

```python
import stripe

stripe.api_key = "sk_test_EXAMPLE_KEY_REPLACE_ME"

def create_payment_intent(amount: int, currency: str, payment_method: str):
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            confirm=True,
            automatic_payment_methods={
                "enabled": True,
                "allow_redirects": "never",
            },
        )
        return {"success": True, "payment_intent": payment_intent}

    except stripe.error.CardError as e:
        # Card was declined
        error = e.error
        print(f"Card error: {error.code}")
        print(f"Decline code: {error.decline_code}")
        print(f"Message: {error.message}")

        if error.decline_code == "insufficient_funds":
            return {"success": False, "user_message": "Your card has insufficient funds. Please try a different card."}
        elif error.decline_code == "authentication_required":
            return {"success": False, "requires_action": True, "payment_intent_id": error.payment_intent["id"]}
        else:
            return {"success": False, "user_message": "Your card was declined. Please try a different payment method."}

    except stripe.error.RateLimitError as e:
        # Too many requests — retry with backoff
        print(f"Rate limit error: {e}")
        return {"success": False, "user_message": "We're experiencing high traffic. Please try again in a moment."}

    except stripe.error.InvalidRequestError as e:
        # Invalid parameters
        print(f"Invalid request: {e}")
        return {"success": False, "user_message": "There was an issue with your request. Please try again."}

    except stripe.error.AuthenticationError as e:
        # API key issues — this is a server configuration problem
        print(f"Authentication error: {e}")
        return {"success": False, "user_message": "We're experiencing a technical issue. Please try again later."}

    except stripe.error.APIConnectionError as e:
        # Network communication with Stripe failed
        print(f"Network error: {e}")
        return {"success": False, "user_message": "We could not connect to our payment processor. Please try again."}

    except stripe.error.StripeError as e:
        # Catch-all for other Stripe errors
        print(f"Stripe error: {e}")
        return {"success": False, "user_message": "An unexpected error occurred. Please try again."}

    except Exception as e:
        # Non-Stripe error
        print(f"Unexpected error: {e}")
        return {"success": False, "user_message": "Something went wrong. Please try again later."}
```

### Node.js

```javascript
const stripe = require('stripe')('sk_test_EXAMPLE_KEY_REPLACE_ME');

async function createPaymentIntent(amount, currency, paymentMethod) {
  try {
    const paymentIntent = await stripe.paymentIntents.create({
      amount,
      currency,
      payment_method: paymentMethod,
      confirm: true,
      automatic_payment_methods: {
        enabled: true,
        allow_redirects: 'never',
      },
    });

    return { success: true, paymentIntent };

  } catch (error) {
    if (error.type === 'StripeCardError') {
      // Card was declined
      console.error(`Card error [${error.code}]: ${error.message}`);
      console.error(`Decline code: ${error.decline_code}`);

      switch (error.decline_code) {
        case 'insufficient_funds':
          return {
            success: false,
            userMessage: 'Your card has insufficient funds. Please try a different card.',
          };
        case 'authentication_required':
          return {
            success: false,
            requiresAction: true,
            paymentIntentId: error.payment_intent.id,
          };
        default:
          return {
            success: false,
            userMessage: 'Your card was declined. Please try a different payment method.',
          };
      }

    } else if (error.type === 'StripeRateLimitError') {
      console.error(`Rate limit error: ${error.message}`);
      return {
        success: false,
        userMessage: "We're experiencing high traffic. Please try again in a moment.",
      };

    } else if (error.type === 'StripeInvalidRequestError') {
      console.error(`Invalid request: ${error.message}`);
      return {
        success: false,
        userMessage: 'There was an issue with your request. Please try again.',
      };

    } else if (error.type === 'StripeAuthenticationError') {
      console.error(`Authentication error: ${error.message}`);
      return {
        success: false,
        userMessage: "We're experiencing a technical issue. Please try again later.",
      };

    } else if (error.type === 'StripeAPIError') {
      console.error(`Stripe API error: ${error.message}`);
      return {
        success: false,
        userMessage: 'An unexpected error occurred. Please try again.',
      };

    } else if (error.type === 'StripeConnectionError') {
      console.error(`Connection error: ${error.message}`);
      return {
        success: false,
        userMessage: 'We could not connect to our payment processor. Please try again.',
      };

    } else {
      console.error(`Unknown error: ${error.message}`);
      return {
        success: false,
        userMessage: 'Something went wrong. Please try again later.',
      };
    }
  }
}
```

## Retry strategies

Not all errors should be retried. Understanding which errors are retriable is critical to building a robust integration.

### Retriable errors

| Error Type | HTTP Code | Should Retry? |
|---|---|---|
| `api_error` | 500, 502, 503 | Yes, with exponential backoff |
| `rate_limit_error` | 429 | Yes, after respecting `Retry-After` header |
| Network/connection errors | N/A | Yes, with exponential backoff |
| `card_error` with `processing_error` | 402 | Yes, once or twice |

### Non-retriable errors

| Error Type | HTTP Code | Should Retry? |
|---|---|---|
| `card_error` (most decline codes) | 402 | No, ask customer for different payment method |
| `invalid_request_error` | 400 | No, fix the request parameters |
| `authentication_error` | 401 | No, fix the API key |
| `idempotency_error` | 409 | No, use a new idempotency key |

### Implementing exponential backoff

```python
import time
import random
import stripe

def create_payment_with_retry(amount, currency, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                automatic_payment_methods={"enabled": True},
            )
        except stripe.error.RateLimitError:
            if attempt == max_retries:
                raise
            delay = (2 ** attempt) + random.uniform(0, 1)
            print(f"Rate limited. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
        except stripe.error.APIError:
            if attempt == max_retries:
                raise
            delay = (2 ** attempt) + random.uniform(0, 1)
            print(f"API error. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
        except stripe.error.APIConnectionError:
            if attempt == max_retries:
                raise
            delay = (2 ** attempt) + random.uniform(0, 1)
            print(f"Connection error. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
```

```javascript
async function createPaymentWithRetry(amount, currency, maxRetries = 3) {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await stripe.paymentIntents.create({
        amount,
        currency,
        automatic_payment_methods: { enabled: true },
      });
    } catch (error) {
      const isRetriable =
        error.type === 'StripeRateLimitError' ||
        error.type === 'StripeAPIError' ||
        error.type === 'StripeConnectionError';

      if (!isRetriable || attempt === maxRetries) {
        throw error;
      }

      const delay = Math.pow(2, attempt) * 1000 + Math.random() * 1000;
      console.log(
        `${error.type}. Retrying in ${(delay / 1000).toFixed(1)}s (attempt ${attempt + 1}/${maxRetries})`
      );
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
}
```

## Idempotency

Stripe supports [idempotency](https://docs.stripe.com/api/idempotent_requests) for safely retrying requests without accidentally performing the same operation twice. This is essential for write operations like creating charges, payment intents, and refunds.

### How idempotency works

Pass an `Idempotency-Key` header with a unique key (typically a UUID) on any POST request. If Stripe receives a second request with the same key within 24 hours, it returns the same response as the first request without re-executing the operation.

```python
import uuid
import stripe

idempotency_key = str(uuid.uuid4())

payment_intent = stripe.PaymentIntent.create(
    amount=2000,
    currency="usd",
    payment_method="pm_card_visa",
    confirm=True,
    idempotency_key=idempotency_key,
)
```

```javascript
const { v4: uuidv4 } = require('uuid');

const paymentIntent = await stripe.paymentIntents.create(
  {
    amount: 2000,
    currency: 'usd',
    payment_method: 'pm_card_visa',
    confirm: true,
  },
  {
    idempotencyKey: uuidv4(),
  }
);
```

### Idempotency key rules

- Keys must be unique per operation. Using the same key with different parameters results in an `idempotency_error`.
- Keys expire after **24 hours**. After that, a new request with the same key is treated as a new operation.
- Only **POST** requests support idempotency keys. GET and DELETE requests are naturally idempotent.
- If the original request is still in progress, a subsequent request with the same key returns a `409 Conflict`.

> **Best practice:** Generate the idempotency key on the client side and include it in the request to your server. This ensures that even if the client retries the request to your server (e.g., due to a network timeout), the payment is only processed once.

## Rate limiting

Stripe enforces rate limits on the API to maintain stability. The standard rate limits are:

- **Live mode:** 100 read operations/second, 100 write operations/second per account.
- **Test mode:** 25 read operations/second, 25 write operations/second per account.

When you exceed these limits, Stripe returns a `429 Too Many Requests` response with a `Retry-After` header indicating how long to wait before retrying.

### Handling rate limits

```python
import stripe

try:
    customers = stripe.Customer.list(limit=100)
except stripe.error.RateLimitError as e:
    retry_after = int(e.headers.get("Retry-After", 1))
    print(f"Rate limited. Retry after {retry_after} seconds.")
    time.sleep(retry_after)
    # Retry the request
    customers = stripe.Customer.list(limit=100)
```

### Strategies to avoid rate limits

1. **Batch operations:** Use Stripe's list endpoints with pagination instead of making individual requests for each resource.
2. **Cache responses:** Cache frequently accessed data (e.g., product catalogs, prices) instead of fetching from Stripe on every request.
3. **Use webhooks:** Instead of polling for status changes, use webhooks to receive real-time notifications.
4. **Spread requests:** If you need to process a large number of operations, spread them over time rather than sending them all at once.

## Testing error scenarios

Stripe provides special test card numbers and tokens that trigger specific errors, making it easy to test your error handling without making real charges.

### Test cards for specific errors

| Card Number | Error Triggered |
|---|---|
| `4000000000000002` | `card_declined` — generic decline |
| `4000000000009995` | `card_declined` — `insufficient_funds` |
| `4000000000009987` | `card_declined` — `lost_card` |
| `4000000000009979` | `card_declined` — `stolen_card` |
| `4000000000000069` | `expired_card` |
| `4000000000000127` | `incorrect_cvc` |
| `4000000000000119` | `processing_error` |
| `4100000000000019` | Blocked as high risk by Radar |
| `4000002500003155` | Requires 3D Secure authentication |
| `4000000000000341` | Attaching to a customer succeeds, but charge fails |

### Test tokens for specific errors

| Token | Error Triggered |
|---|---|
| `tok_chargeDeclined` | Generic charge decline |
| `tok_chargeDeclinedInsufficientFunds` | Insufficient funds decline |
| `tok_chargeDeclinedFraudulent` | Fraudulent decline |
| `tok_chargeDeclinedProcessingError` | Processing error |
| `tok_chargeDeclinedExpiredCard` | Expired card decline |
| `tok_chargeDeclinedIncorrectCvc` | Incorrect CVC decline |

### Example test

```python
import stripe
import pytest

stripe.api_key = "sk_test_EXAMPLE_KEY_REPLACE_ME"

def test_card_declined():
    """Test that a declined card returns the expected error."""
    with pytest.raises(stripe.error.CardError) as exc_info:
        stripe.PaymentIntent.create(
            amount=2000,
            currency="usd",
            payment_method_data={
                "type": "card",
                "card": {"token": "tok_chargeDeclined"},
            },
            confirm=True,
        )

    error = exc_info.value.error
    assert error.type == "card_error"
    assert error.code == "card_declined"


def test_expired_card():
    """Test that an expired card returns the expected error."""
    with pytest.raises(stripe.error.CardError) as exc_info:
        stripe.PaymentIntent.create(
            amount=2000,
            currency="usd",
            payment_method_data={
                "type": "card",
                "card": {"token": "tok_chargeDeclinedExpiredCard"},
            },
            confirm=True,
        )

    error = exc_info.value.error
    assert error.type == "card_error"
    assert error.code == "expired_card"


def test_insufficient_funds():
    """Test that an insufficient funds decline returns the expected decline code."""
    with pytest.raises(stripe.error.CardError) as exc_info:
        stripe.PaymentIntent.create(
            amount=2000,
            currency="usd",
            payment_method_data={
                "type": "card",
                "card": {"token": "tok_chargeDeclinedInsufficientFunds"},
            },
            confirm=True,
        )

    error = exc_info.value.error
    assert error.type == "card_error"
    assert error.code == "card_declined"
    assert error.decline_code == "insufficient_funds"
```

## Best practices

### 1. Never expose raw Stripe errors to users

Stripe error messages are designed for developers. Always map them to user-friendly messages before displaying to customers.

```python
USER_MESSAGES = {
    "card_declined": "Your card was declined. Please try a different payment method.",
    "expired_card": "Your card has expired. Please update your card details.",
    "incorrect_cvc": "The security code you entered is incorrect. Please check and try again.",
    "insufficient_funds": "Your card has insufficient funds. Please try a different card.",
    "processing_error": "An error occurred while processing your card. Please try again.",
    "rate_limit_error": "We're experiencing high demand. Please try again in a moment.",
}

def get_user_message(error):
    code = getattr(error, 'code', None) or error.type
    return USER_MESSAGES.get(code, "An error occurred. Please try again or use a different payment method.")
```

### 2. Log errors with full context

Always log the error type, code, message, request ID, and any associated resource IDs. The request ID (`error.request_id` or the `Request-Id` response header) is essential for Stripe support to help debug issues.

```python
import structlog

logger = structlog.get_logger()

except stripe.error.CardError as e:
    logger.error(
        "stripe_card_error",
        error_type=e.error.type,
        error_code=e.error.code,
        decline_code=e.error.decline_code,
        message=e.error.message,
        request_id=e.request_id,
        payment_intent_id=getattr(e.error.payment_intent, 'id', None),
        http_status=e.http_status,
    )
```

### 3. Classify errors by recoverability

Build a utility that classifies errors so your application can take the right action:

```python
from enum import Enum

class ErrorRecoverability(Enum):
    RETRIABLE = "retriable"           # Retry with backoff
    USER_ACTIONABLE = "user_actionable"  # Ask user to fix (e.g., new card)
    DEVELOPER_FIX = "developer_fix"    # Fix the code or configuration
    UNRECOVERABLE = "unrecoverable"    # Log and alert

def classify_stripe_error(error):
    if isinstance(error, stripe.error.RateLimitError):
        return ErrorRecoverability.RETRIABLE
    elif isinstance(error, stripe.error.APIError):
        return ErrorRecoverability.RETRIABLE
    elif isinstance(error, stripe.error.APIConnectionError):
        return ErrorRecoverability.RETRIABLE
    elif isinstance(error, stripe.error.CardError):
        if error.error.code == "processing_error":
            return ErrorRecoverability.RETRIABLE
        return ErrorRecoverability.USER_ACTIONABLE
    elif isinstance(error, stripe.error.InvalidRequestError):
        return ErrorRecoverability.DEVELOPER_FIX
    elif isinstance(error, stripe.error.AuthenticationError):
        return ErrorRecoverability.DEVELOPER_FIX
    else:
        return ErrorRecoverability.UNRECOVERABLE
```

### 4. Use structured error responses in your API

Return consistent, structured error responses from your own API so your frontend can handle them predictably:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

class PaymentErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    user_message: str
    requires_action: bool = False
    payment_intent_id: Optional[str] = None
    retriable: bool = False

@app.post("/api/payments")
async def create_payment(request: PaymentRequest):
    try:
        intent = stripe.PaymentIntent.create(...)
        return {"success": True, "payment_intent": intent}
    except stripe.error.CardError as e:
        return PaymentErrorResponse(
            error_code=e.error.code,
            user_message=get_user_message(e.error),
            requires_action=(e.error.decline_code == "authentication_required"),
            payment_intent_id=getattr(e.error.payment_intent, "id", None),
            retriable=(e.error.code == "processing_error"),
        )
```

### 5. Set up alerting for unexpected errors

Monitor for error types that indicate problems with your integration rather than normal customer behavior:

- **`authentication_error`** — Your API key may have been rotated or revoked.
- **`invalid_request_error`** — Your code is sending malformed requests.
- **`api_error`** (sustained) — Stripe may be experiencing an outage.
- **`rate_limit_error`** (sustained) — You may need to optimize your API usage.

### 6. Handle webhooks and API errors consistently

Your webhook handlers and direct API calls should use the same error handling patterns. Wrap both in consistent error classification and logging utilities.

## Summary

Effective error handling is not an afterthought — it is a core part of any production Stripe integration. By understanding error types, implementing retry logic with exponential backoff, using idempotency keys, mapping errors to user-friendly messages, and setting up structured logging and alerting, you can build an integration that handles failures gracefully and provides a smooth experience for your users.
