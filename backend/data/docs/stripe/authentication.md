<!--
title: Authentication
url: https://docs.stripe.com/authentication
topic: authentication
complexity: intermediate
-->

# Authentication

Stripe authenticates your API requests using your account's API keys. If a request does not include a valid key, Stripe returns an `invalid_request_error`. If a request includes a deleted or expired key, Stripe returns an `authentication_error`.

Every account is provided with separate keys for testing and for running live transactions. All API requests exist in either test mode or live mode, and objects in one mode (for example, customers, charges, or refunds) cannot be manipulated by objects in the other.

---

## API Key Types

Your Stripe account has four types of API keys, organized into two pairs: a **publishable** key and a **secret** key for both test mode and live mode.

| Key Type | Prefix | Visibility | Use Case |
|---|---|---|---|
| Test publishable | `pk_test_` | Client-side | Tokenizing payment details in test mode |
| Test secret | `sk_test_` | Server-side only | Making test API calls from your backend |
| Live publishable | `pk_live_` | Client-side | Tokenizing payment details in production |
| Live secret | `sk_live_` | Server-side only | Making production API calls from your backend |

### Publishable Keys

Publishable keys are meant solely to identify your account with Stripe. They are not secret. They can safely be published in your client-side code (for example, in Stripe.js on the frontend) to collect payment information. Publishable keys only have the power to create tokens, which represent card information.

Publishable keys are prefixed with `pk_test_` or `pk_live_`.

```javascript
// Client-side: using a publishable key with Stripe.js
const stripe = Stripe('pk_test_51ABC123...');

const elements = stripe.elements();
const cardElement = elements.create('card');
cardElement.mount('#card-element');
```

### Secret Keys

Secret keys can perform any API request to Stripe without restriction, including reading and writing all data on your account. They must be kept confidential and stored only on your own servers. Never expose secret keys in client-side code, public repositories, or anywhere accessible to browsers or users.

Secret keys are prefixed with `sk_test_` or `sk_live_`.

> **Warning:** Treat your secret API key as you would any sensitive credential such as a password or SSH private key. If a secret key is compromised, immediately roll it and audit all recent API activity on your account. Anyone with access to your secret key can make arbitrary API calls on your behalf, including issuing refunds, creating payouts, or modifying connected accounts.

---

## Authentication Methods

Stripe supports two methods of authenticating API requests: Bearer token authentication and HTTP Basic authentication. Both methods use your secret API key.

### Bearer Token Authentication (Recommended)

Include your secret key in the `Authorization` header using the `Bearer` scheme. This is the recommended method for all new integrations.

```bash
curl https://api.stripe.com/v1/charges \
  -H "Authorization: Bearer sk_test_51ABC123..."
```

```python
import stripe

stripe.api_key = "sk_test_51ABC123..."

# The library automatically includes the key in the Authorization header
charge = stripe.Charge.retrieve("ch_1ABC123")
print(charge.amount)
```

```javascript
// Node.js
const stripe = require('stripe')('sk_test_51ABC123...');

const charge = await stripe.charges.retrieve('ch_1ABC123');
console.log(charge.amount);
```

```ruby
require 'stripe'

Stripe.api_key = 'sk_test_51ABC123...'

charge = Stripe::Charge.retrieve('ch_1ABC123')
puts charge.amount
```

### HTTP Basic Authentication

Stripe also supports HTTP Basic authentication. Provide your API key as the username and leave the password field empty. Some legacy integrations use this method, but Bearer authentication is preferred.

```bash
curl https://api.stripe.com/v1/charges \
  -u sk_test_51ABC123...:
```

Note the trailing colon after the API key, which prevents curl from prompting for a password.

```python
import requests

response = requests.get(
    'https://api.stripe.com/v1/charges/ch_1ABC123',
    auth=('sk_test_51ABC123...', '')
)
print(response.json())
```

### Per-Request Key Override

All official Stripe client libraries support providing a key on a per-request basis, which is useful when working with Stripe Connect or when switching between test and live contexts.

```python
import stripe

# Global default
stripe.api_key = "sk_test_51ABC123..."

# Per-request override
charge = stripe.Charge.retrieve(
    "ch_1ABC123",
    api_key="sk_test_DIFFERENT_KEY..."
)
```

```javascript
// Node.js per-request override
const stripe = require('stripe')('sk_test_51ABC123...');

const charge = await stripe.charges.retrieve(
  'ch_1ABC123',
  { apiKey: 'sk_test_DIFFERENT_KEY...' }
);
```

---

## Restricted API Keys

Restricted keys let you limit API access to only the resources your application needs. Instead of granting full read/write access to your entire Stripe account, a restricted key can be scoped to specific permissions.

### Creating Restricted Keys

You can create restricted keys in the Stripe Dashboard under **Developers > API keys > Create restricted key**, or via the API:

```bash
curl https://api.stripe.com/v1/api_keys \
  -H "Authorization: Bearer sk_test_51ABC123..." \
  -d "name=order-service" \
  -d "permissions[charges]=write" \
  -d "permissions[customers]=read" \
  -d "permissions[refunds]=none"
```

### Available Permission Levels

Each API resource can be assigned one of three permission levels:

| Permission | Description |
|---|---|
| `none` | The key cannot access this resource at all |
| `read` | The key can list and retrieve objects of this type |
| `write` | The key can create, update, delete, list, and retrieve objects of this type |

### Common Permission Scopes

| Resource | Description | Typical Grant |
|---|---|---|
| `charges` | Create and manage charges | `write` for payment services |
| `customers` | Manage customer records | `read` or `write` |
| `payment_intents` | Create and confirm payment intents | `write` for checkout flows |
| `refunds` | Issue refunds | `write` for support tools |
| `subscriptions` | Manage subscriptions | `write` for billing services |
| `products` | Manage product catalog | `read` for storefront, `write` for admin |
| `prices` | Manage pricing | `read` for storefront, `write` for admin |
| `invoices` | Manage invoices | `write` for billing services |
| `webhooks` | Manage webhook endpoints | `write` for infrastructure automation |
| `payouts` | Manage payouts | `write` for finance systems |

### Restricted Key Best Practices

1. **Principle of least privilege.** Only grant permissions that are strictly needed by a given service.
2. **One key per service.** If you run separate microservices for payments, billing, and refunds, each should have its own restricted key with its own minimal scope.
3. **Name keys descriptively.** Use names like `checkout-service-prod` or `refund-worker-staging` so you can audit usage.
4. **Audit regularly.** Review restricted key permissions quarterly to revoke unused access.

> **Note:** Restricted keys are prefixed with `rk_test_` or `rk_live_`. They cannot be used for all API operations. For example, restricted keys cannot manage other API keys or modify account-level settings.

---

## Test Mode vs Live Mode

All Stripe API objects exist in either test mode or live mode. The mode is determined by the key used to create the object.

| Aspect | Test Mode | Live Mode |
|---|---|---|
| Key prefix | `sk_test_`, `pk_test_` | `sk_live_`, `pk_live_` |
| Real charges | No | Yes |
| Card network calls | No | Yes |
| Webhook delivery | Test endpoints only | Live endpoints only |
| Dashboard view | Toggle to "Viewing test data" | Default dashboard view |
| Rate limits | Same as live mode | Standard rate limits |

### Test Card Numbers

In test mode, you can use these card numbers to simulate various scenarios:

| Number | Brand | Scenario |
|---|---|---|
| `4242424242424242` | Visa | Successful payment |
| `4000000000009995` | Visa | Declined (insufficient funds) |
| `4000000000000069` | Visa | Declined (expired card) |
| `4000000000003220` | Visa | Requires 3D Secure authentication |
| `5555555555554444` | Mastercard | Successful payment |
| `378282246310005` | American Express | Successful payment |

```python
import stripe

stripe.api_key = "sk_test_51ABC123..."

# Create a test payment intent
payment_intent = stripe.PaymentIntent.create(
    amount=2000,  # $20.00 in cents
    currency="usd",
    payment_method_data={
        "type": "card",
        "card": {
            "number": "4242424242424242",
            "exp_month": 12,
            "exp_year": 2027,
            "cvc": "314",
        },
    },
    confirm=True,
)
print(payment_intent.status)  # "succeeded"
```

> **Warning:** Never use real card numbers in test mode. Always use Stripe's designated test card numbers. Using real card numbers, even in test mode, may violate PCI compliance requirements.

---

## Key Rotation

Stripe supports rolling key rotation so you can update your secret key without downtime. When you roll a key, the old key remains active for 24 hours by default, giving you time to update all references.

### Rotation Procedure

1. **Generate a new key** in the Dashboard under Developers > API keys, or via the API.
2. **Update your services** to use the new key. Deploy configuration changes across all environments that reference the old key.
3. **Monitor for errors.** Watch your logs for `authentication_error` responses, which indicate a service is still using the old key.
4. **Revoke the old key** once all services have migrated. You can explicitly revoke a key or let the 24-hour expiry elapse.

```bash
# Step 1: Create a new key via the API
curl https://api.stripe.com/v1/api_keys/roll \
  -H "Authorization: Bearer sk_test_51ABC123..." \
  -d "expiration_date=2026-03-10T00:00:00Z"

# The response includes both the new key and the old key's expiry
# {
#   "id": "sk_test_NEW_KEY...",
#   "old_key_expiry": "2026-03-10T00:00:00Z",
#   ...
# }
```

### Rotation Best Practices

- **Rotate keys at least every 90 days**, even if you have no reason to suspect compromise.
- **Automate rotation** with a secrets manager (AWS Secrets Manager, HashiCorp Vault, or similar).
- **Never commit keys to version control.** Use environment variables or secret management tools.
- **Set up alerts** for authentication failures during rotation windows.
- **Test rotation in test mode first** before rotating your live secret key.

---

## Server-Side vs Client-Side Key Usage

Choosing the correct key type for each context is critical to both functionality and security.

### Server-Side (Secret Key)

Use your secret key (`sk_test_*` or `sk_live_*`) exclusively on your server. The secret key has full access to all API endpoints.

```python
# backend/payment_service.py
import stripe
import os

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

def create_payment(amount: int, currency: str, customer_id: str) -> dict:
    """Create a payment intent on the server side."""
    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency=currency,
        customer=customer_id,
        automatic_payment_methods={"enabled": True},
    )
    return {
        "client_secret": intent.client_secret,
        "payment_intent_id": intent.id,
    }
```

### Client-Side (Publishable Key)

Use your publishable key (`pk_test_*` or `pk_live_*`) in the browser or mobile app. The publishable key can only tokenize sensitive data and confirm PaymentIntents using a `client_secret`.

```javascript
// frontend/checkout.js
const stripe = Stripe('pk_test_51ABC123...');

async function handlePayment(clientSecret) {
  const { error, paymentIntent } = await stripe.confirmCardPayment(
    clientSecret,
    {
      payment_method: {
        card: cardElement,
        billing_details: {
          name: 'Jenny Rosen',
          email: 'jenny.rosen@example.com',
        },
      },
    }
  );

  if (error) {
    console.error('Payment failed:', error.message);
  } else if (paymentIntent.status === 'succeeded') {
    console.log('Payment succeeded!');
  }
}
```

### Key Usage Summary

| Operation | Key Type | Where |
|---|---|---|
| Tokenize card numbers | Publishable | Browser / mobile |
| Create PaymentIntents | Secret | Server |
| Confirm PaymentIntents (with client_secret) | Publishable | Browser / mobile |
| Retrieve charges | Secret | Server |
| Issue refunds | Secret | Server |
| Manage customers | Secret | Server |
| Create subscriptions | Secret | Server |
| Set up Stripe Elements | Publishable | Browser / mobile |

---

## Rate Limiting

Stripe enforces rate limits on API requests to ensure fair usage and platform stability. Rate limits apply per API key and vary by endpoint and HTTP method.

### Default Rate Limits

| Tier | Limit | Applies To |
|---|---|---|
| Standard | 100 requests/second per key | Most read endpoints |
| Write | 100 requests/second per key | Create/update/delete endpoints |
| Search | 20 requests/second per key | Search API endpoints |
| Files | 20 requests/second per key | File upload endpoints |

### Rate Limit Headers

Every API response includes rate-limit information in the headers:

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1709500000
```

When you exceed the rate limit, Stripe returns a `429 Too Many Requests` response:

```json
{
  "error": {
    "type": "rate_limit_error",
    "message": "Too many requests hit the API too quickly. We recommend an exponential backoff of your requests.",
    "code": "rate_limit"
  }
}
```

### Handling Rate Limits

Implement exponential backoff with jitter when you receive a `429` response:

```python
import stripe
import time
import random

def make_api_call_with_retry(func, max_retries=5, **kwargs):
    """Make a Stripe API call with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            return func(**kwargs)
        except stripe.error.RateLimitError:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff: 1s, 2s, 4s, 8s, 16s + jitter
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            print(f"Rate limited. Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)

# Usage
charge = make_api_call_with_retry(
    stripe.Charge.retrieve,
    id="ch_1ABC123"
)
```

```javascript
// Node.js: The stripe library has built-in retry support
const stripe = require('stripe')('sk_test_51ABC123...', {
  maxNetworkRetries: 3, // Automatically retries on rate limit errors
  timeout: 10000,       // 10 second timeout
});
```

---

## Security Considerations

### Storing API Keys

Never hardcode API keys in your source code. Use environment variables or a secrets management service.

```bash
# .env file (do NOT commit this file)
STRIPE_SECRET_KEY=sk_test_51ABC123...
STRIPE_PUBLISHABLE_KEY=pk_test_51ABC123...
STRIPE_WEBHOOK_SECRET=whsec_ABC123...
```

```python
# Load keys from environment
import os

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

if not stripe.api_key:
    raise ValueError("STRIPE_SECRET_KEY environment variable is not set")
```

### Webhook Signature Verification

When receiving webhook events, always verify the signature to confirm the event originated from Stripe and was not tampered with in transit.

```python
import stripe
from flask import Flask, request

app = Flask(__name__)
endpoint_secret = os.environ["STRIPE_WEBHOOK_SECRET"]

@app.route("/webhooks/stripe", methods=["POST"])
def webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return "Invalid payload", 400
    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400

    # Handle the event
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        print(f"Payment succeeded: {payment_intent['id']}")

    return "", 200
```

### Common Security Mistakes

| Mistake | Risk | Mitigation |
|---|---|---|
| Committing keys to Git | Full account compromise | Use `.env` files and `.gitignore`; use git-secrets |
| Using secret keys client-side | Full account compromise | Only use publishable keys in browsers |
| Not verifying webhook signatures | Spoofed webhook events | Always verify with `Webhook.construct_event` |
| Sharing keys via chat/email | Key interception | Use a secrets manager with access controls |
| Not rotating keys | Prolonged exposure if leaked | Rotate every 90 days; automate with Vault |
| Using live keys in development | Accidental real charges | Enforce test keys in non-production envs |

---

## Key Management in Team Environments

When multiple developers or teams work with Stripe, proper key management prevents unauthorized access and simplifies auditing.

### Recommended Team Practices

1. **Use restricted keys per service or team.** Rather than sharing one secret key across all microservices, create a restricted key for each service with only the permissions it needs.

2. **Centralize key storage.** Use a secrets manager (AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault) rather than distributing keys via environment files or chat.

3. **Use Stripe Dashboard roles.** Stripe supports multiple team roles with different levels of Dashboard access:

   | Role | API Key Access | Dashboard Access |
   |---|---|---|
   | Administrator | Full | Full |
   | Developer | Can view/create keys | Full |
   | Analyst | No key access | Read-only |
   | Support Specialist | No key access | Limited (customers, disputes) |
   | View Only | No key access | Read-only |

4. **Enable audit logging.** Monitor the Security & events log in the Dashboard for key creation, rotation, and revocation events.

5. **Separate environments.** Maintain distinct key sets for development, staging, and production. Never reuse the same key across environments.

### Environment Isolation Example

```yaml
# config/environments.yaml
development:
  stripe_key_env_var: STRIPE_SECRET_KEY_DEV
  stripe_mode: test

staging:
  stripe_key_env_var: STRIPE_SECRET_KEY_STAGING
  stripe_mode: test

production:
  stripe_key_env_var: STRIPE_SECRET_KEY_PROD
  stripe_mode: live
```

```python
import os

ENVIRONMENT = os.environ.get("APP_ENV", "development")

STRIPE_KEY_MAP = {
    "development": "STRIPE_SECRET_KEY_DEV",
    "staging": "STRIPE_SECRET_KEY_STAGING",
    "production": "STRIPE_SECRET_KEY_PROD",
}

env_var_name = STRIPE_KEY_MAP[ENVIRONMENT]
stripe.api_key = os.environ[env_var_name]

# Safety check: prevent live keys in non-production
if ENVIRONMENT != "production" and stripe.api_key.startswith("sk_live_"):
    raise RuntimeError(
        f"Live key detected in {ENVIRONMENT} environment. "
        "Use test keys for non-production environments."
    )
```

---

## Versioning and API Keys

Stripe uses API versioning to manage breaking changes. Your account has a default API version, but you can override it per-request using the `Stripe-Version` header.

```bash
curl https://api.stripe.com/v1/charges \
  -H "Authorization: Bearer sk_test_51ABC123..." \
  -H "Stripe-Version: 2024-12-18.acacia"
```

```python
import stripe

stripe.api_key = "sk_test_51ABC123..."
stripe.api_version = "2024-12-18.acacia"

# Or per-request
charge = stripe.Charge.retrieve(
    "ch_1ABC123",
    stripe_version="2024-12-18.acacia"
)
```

> **Note:** Webhook events are always sent using your account's default API version, not the version specified in your requests. Pin your account to a specific version in the Dashboard to ensure consistent webhook payloads.

---

## Troubleshooting Authentication Errors

| HTTP Status | Error Type | Common Cause | Solution |
|---|---|---|---|
| 401 | `authentication_error` | Invalid, expired, or revoked key | Verify the key in Dashboard; generate a new one if needed |
| 401 | `authentication_error` | Key from wrong mode (test vs live) | Check key prefix matches your environment |
| 403 | `forbidden` | Restricted key lacks required permission | Update the restricted key's permissions in Dashboard |
| 429 | `rate_limit_error` | Too many requests per second | Implement exponential backoff; request a rate limit increase |

```python
import stripe

try:
    charge = stripe.Charge.retrieve("ch_1ABC123")
except stripe.error.AuthenticationError as e:
    print(f"Authentication failed: {e.user_message}")
    print("Check that your API key is correct and not expired.")
except stripe.error.PermissionError as e:
    print(f"Permission denied: {e.user_message}")
    print("Your restricted key may lack the required permissions.")
except stripe.error.RateLimitError as e:
    print(f"Rate limited: {e.user_message}")
    print("Implement backoff and retry logic.")
except stripe.error.StripeError as e:
    print(f"Stripe error: {e.user_message}")
```

---

## Related Resources

- [API Keys Dashboard](https://dashboard.stripe.com/apikeys) -- Manage your API keys
- [Stripe CLI Authentication](https://docs.stripe.com/stripe-cli#login) -- Authenticate the Stripe CLI
- [Webhook Signatures](https://docs.stripe.com/webhooks/signatures) -- Verify webhook payloads
- [PCI Compliance](https://docs.stripe.com/security/guide) -- Security best practices
- [Stripe Connect Authentication](https://docs.stripe.com/connect/authentication) -- Authentication for platform integrations
- [API Versioning](https://docs.stripe.com/upgrades) -- Manage API version upgrades
