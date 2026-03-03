<!--
title: SDKs and Quickstart
url: https://docs.stripe.com/sdks
topic: getting-started
complexity: beginner
-->

# SDKs and Quickstart

Stripe provides official server-side SDKs in six languages and a CLI for local development and testing. This guide walks you through installation, configuration, and making your first API calls.

## SDK Installation

### Python

Requires Python 3.8 or later.

```bash
pip install stripe
```

Or add to your `requirements.txt`:

```
stripe>=8.0.0
```

### Node.js

Requires Node.js 14 or later.

```bash
npm install stripe
```

Or with Yarn:

```bash
yarn add stripe
```

### Ruby

Requires Ruby 2.7 or later.

```bash
gem install stripe
```

Or add to your `Gemfile`:

```ruby
gem 'stripe', '~> 10.0'
```

### Go

Requires Go 1.20 or later.

```bash
go get github.com/stripe/stripe-go/v78
```

### Java

Requires Java 1.8 or later. Add to your `pom.xml`:

```xml
<dependency>
  <groupId>com.stripe</groupId>
  <artifactId>stripe-java</artifactId>
  <version>25.0.0</version>
</dependency>
```

Or with Gradle:

```groovy
implementation 'com.stripe:stripe-java:25.0.0'
```

### PHP

Requires PHP 8.1 or later.

```bash
composer require stripe/stripe-php
```

## Basic Configuration and Initialization

Every Stripe SDK requires your secret API key to authenticate requests. Use your **test mode** key during development and your **live mode** key in production.

> **Warning:** Never hardcode API keys in your source code. Always load them from environment variables or a secrets manager. Exposing your secret key can allow unauthorized access to your Stripe account.

### Python

```python
import stripe

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

# Optional: set the API version explicitly
stripe.api_version = "2025-12-18.acacia"

# Optional: configure timeouts (in seconds)
stripe.max_network_retries = 2
stripe.default_http_client = stripe.HTTPClient(
    timeout=30,
    connect_timeout=10,
)
```

### Node.js

```javascript
const Stripe = require('stripe');

const stripe = Stripe(process.env.STRIPE_SECRET_KEY, {
  apiVersion: '2025-12-18.acacia',
  maxNetworkRetries: 2,
  timeout: 30000, // milliseconds
});
```

### Ruby

```ruby
require 'stripe'

Stripe.api_key = ENV['STRIPE_SECRET_KEY']
Stripe.api_version = '2025-12-18.acacia'
Stripe.max_network_retries = 2
```

### Go

```go
package main

import (
    "os"
    "github.com/stripe/stripe-go/v78"
    "github.com/stripe/stripe-go/v78/customer"
)

func main() {
    stripe.Key = os.Getenv("STRIPE_SECRET_KEY")
    stripe.DefaultLeveledLogger = &stripe.LeveledLogger{
        Level: stripe.LevelWarn,
    }
}
```

### Java

```java
import com.stripe.Stripe;

public class Application {
    public static void main(String[] args) {
        Stripe.apiKey = System.getenv("STRIPE_SECRET_KEY");
        Stripe.setApiVersion("2025-12-18.acacia");
        Stripe.setMaxNetworkRetries(2);
        Stripe.setConnectTimeout(10 * 1000); // milliseconds
        Stripe.setReadTimeout(30 * 1000);
    }
}
```

### PHP

```php
require_once 'vendor/autoload.php';

\Stripe\Stripe::setApiKey(getenv('STRIPE_SECRET_KEY'));
\Stripe\Stripe::setApiVersion('2025-12-18.acacia');
\Stripe\Stripe::setMaxNetworkRetries(2);
```

## Making Your First API Call

The simplest way to verify that your integration is working is to retrieve your account information.

### Python

```python
import stripe
import os

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

account = stripe.Account.retrieve()
print(f"Connected to Stripe account: {account.id}")
print(f"Business name: {account.business_profile.name}")
```

### Node.js

```javascript
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

async function main() {
  const account = await stripe.accounts.retrieve();
  console.log(`Connected to Stripe account: ${account.id}`);
  console.log(`Business name: ${account.business_profile?.name}`);
}

main();
```

### Ruby

```ruby
require 'stripe'

Stripe.api_key = ENV['STRIPE_SECRET_KEY']

account = Stripe::Account.retrieve
puts "Connected to Stripe account: #{account.id}"
puts "Business name: #{account.business_profile.name}"
```

Expected output:

```
Connected to Stripe account: acct_1NkBG2Jx9cFp8LRc
Business name: My Test Business
```

## Creating a Simple Payment Flow

A complete payment flow involves creating a PaymentIntent on the server, collecting payment details on the client with Stripe.js, and confirming the payment.

### Step 1: Create a PaymentIntent (Server)

```python
# Python (FastAPI example)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import stripe
import os

app = FastAPI()
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

class PaymentRequest(BaseModel):
    amount: int  # in cents
    currency: str = "usd"

@app.post("/api/create-payment-intent")
async def create_payment_intent(req: PaymentRequest):
    try:
        intent = stripe.PaymentIntent.create(
            amount=req.amount,
            currency=req.currency,
            automatic_payment_methods={"enabled": True},
            metadata={"order_id": "order_12345"},
        )
        return {"client_secret": intent.client_secret}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Step 2: Collect Payment Details (Client)

```javascript
// Frontend (React example)
import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';

const stripePromise = loadStripe('pk_test_...');

function CheckoutForm() {
  const stripe = useStripe();
  const elements = useElements();

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!stripe || !elements) return;

    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: 'https://example.com/order/success',
      },
    });

    if (error) {
      console.error(error.message);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <PaymentElement />
      <button type="submit" disabled={!stripe}>Pay now</button>
    </form>
  );
}

function App() {
  const [clientSecret, setClientSecret] = useState('');

  useEffect(() => {
    fetch('/api/create-payment-intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount: 2000 }),
    })
      .then(res => res.json())
      .then(data => setClientSecret(data.client_secret));
  }, []);

  return (
    clientSecret && (
      <Elements stripe={stripePromise} options={{ clientSecret }}>
        <CheckoutForm />
      </Elements>
    )
  );
}
```

### Step 3: Handle the Result

After the customer completes payment, they are redirected to your `return_url`. Retrieve the PaymentIntent to check the status:

```python
@app.get("/api/payment-status/{payment_intent_id}")
async def get_payment_status(payment_intent_id: str):
    intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    return {
        "status": intent.status,
        "amount": intent.amount,
        "currency": intent.currency,
    }
```

PaymentIntent status values:

| Status | Meaning |
|--------|---------|
| `requires_payment_method` | Customer has not provided payment details |
| `requires_confirmation` | Payment details collected, awaiting confirmation |
| `requires_action` | Additional authentication needed (e.g., 3D Secure) |
| `processing` | Payment is being processed |
| `succeeded` | Payment completed successfully |
| `canceled` | Payment was canceled |
| `requires_capture` | Payment authorized, awaiting capture (manual capture flow) |

## Setting Up a Customer

Creating a customer object allows you to store payment methods, track purchase history, and create subscriptions.

```python
# Create a customer
customer = stripe.Customer.create(
    email="jenny@example.com",
    name="Jenny Rosen",
    metadata={"user_id": "usr_abc123"},
)

print(f"Customer created: {customer.id}")
# Output: Customer created: cus_NkBG2Jx9cFp8LRc
```

```javascript
// Node.js
const customer = await stripe.customers.create({
  email: 'jenny@example.com',
  name: 'Jenny Rosen',
  metadata: { user_id: 'usr_abc123' },
});
```

### Attaching a Payment Method to a Customer

```python
# Attach a payment method to a customer
stripe.PaymentMethod.attach(
    "pm_1NkBG2Jx9cFp8LRc",
    customer="cus_NkBG2Jx9cFp8LRc",
)

# Set as the default payment method
stripe.Customer.modify(
    "cus_NkBG2Jx9cFp8LRc",
    invoice_settings={
        "default_payment_method": "pm_1NkBG2Jx9cFp8LRc",
    },
)
```

### Listing a Customer's Payment Methods

```
GET /v1/customers/cus_NkBG2Jx9cFp8LRc/payment_methods?type=card
```

```json
{
  "object": "list",
  "data": [
    {
      "id": "pm_1NkBG2Jx9cFp8LRc",
      "object": "payment_method",
      "type": "card",
      "card": {
        "brand": "visa",
        "last4": "4242",
        "exp_month": 12,
        "exp_year": 2027
      }
    }
  ],
  "has_more": false
}
```

## Using the Stripe CLI

The Stripe CLI is an essential tool for local development. It lets you test webhooks, trigger events, and interact with the API from your terminal.

### Installation

```bash
# macOS
brew install stripe/stripe-cli/stripe

# Linux (Debian/Ubuntu)
curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public | gpg --dearmor | sudo tee /usr/share/keyrings/stripe.gpg
echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main" | sudo tee /etc/apt/sources.list.d/stripe.list
sudo apt update && sudo apt install stripe

# Windows
scoop install stripe

# Docker
docker run --rm -it stripe/stripe-cli
```

### Login and Setup

```bash
stripe login
# Opens a browser window for authentication
# Generates a restricted key for the CLI session
```

### Forwarding Webhooks Locally

```bash
# Forward webhook events to your local server
stripe listen --forward-to localhost:8000/api/webhook

# Output:
# > Ready! Your webhook signing secret is whsec_abc123... (use this for verification)
```

### Triggering Test Events

```bash
# Trigger a payment_intent.succeeded event
stripe trigger payment_intent.succeeded

# Trigger a customer.subscription.created event
stripe trigger customer.subscription.created

# Trigger a checkout.session.completed event
stripe trigger checkout.session.completed
```

### Useful CLI Commands

```bash
# List recent charges
stripe charges list --limit 5

# Retrieve a specific customer
stripe customers retrieve cus_NkBG2Jx9cFp8LRc

# Create a product
stripe products create --name="Premium Plan" --description="Full access"

# Tail API request logs
stripe logs tail
```

## Development vs Production Setup

### Environment Configuration

| Setting | Development | Production |
|---------|-------------|------------|
| API key prefix | `sk_test_`, `pk_test_` | `sk_live_`, `pk_live_` |
| Webhook secret | From `stripe listen` | From Dashboard |
| Stripe.js | Uses test mode | Uses live mode |
| Cards | Test card numbers only | Real card numbers |
| Charges | Simulated, not real | Real money movement |
| Webhooks | CLI forwarding | HTTPS endpoint |

### Test Card Numbers

Use these card numbers in test mode to simulate different scenarios:

| Card Number | Scenario |
|-------------|----------|
| `4242 4242 4242 4242` | Successful payment |
| `4000 0000 0000 3220` | 3D Secure authentication required |
| `4000 0000 0000 9995` | Payment declined (insufficient funds) |
| `4000 0000 0000 0069` | Expired card |
| `4000 0000 0000 0127` | Incorrect CVC |
| `4000 0025 0000 3155` | SCA required (EU) |

For all test cards, use any future expiration date, any 3-digit CVC, and any 5-digit postal code.

## Environment Variable Management

### Recommended Setup

```bash
# .env file (never commit this to version control)
STRIPE_SECRET_KEY=sk_test_EXAMPLE_KEY_REPLACE_ME
STRIPE_PUBLISHABLE_KEY=pk_test_51NkBG2Jx9cFp8LRcAbCdEfGhIjKlMnOpQrStUvWxYz
STRIPE_WEBHOOK_SECRET=whsec_abc123def456
STRIPE_API_VERSION=2025-12-18.acacia
```

> **Important:** Add `.env` to your `.gitignore` file. Never commit API keys to version control. If a key is accidentally exposed, rotate it immediately in the Stripe Dashboard under **Developers > API keys**.

### Loading Environment Variables

**Python (python-dotenv):**

```python
from dotenv import load_dotenv
import os

load_dotenv()
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
```

**Node.js (dotenv):**

```javascript
require('dotenv').config();
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
```

**Ruby (dotenv):**

```ruby
require 'dotenv/load'
Stripe.api_key = ENV['STRIPE_SECRET_KEY']
```

## SDK Versioning and API Versions

### How Stripe Versioning Works

Stripe maintains backward compatibility within a major API version. Each API version is named by its release date (e.g., `2025-12-18.acacia`). When you create your Stripe account, it is pinned to the latest API version at that time.

Key concepts:

- **Account API version:** The default version used when you make API requests without specifying a version. Set in the Dashboard under **Developers > API keys > API version**.
- **Request-level version override:** You can override the version on a per-request basis.
- **Webhook API version:** Webhook events are sent using your account's API version, not the version specified in individual requests.

### Upgrading API Versions

```python
# Override the API version for a single request
charge = stripe.Charge.retrieve(
    "ch_abc123",
    stripe_version="2025-12-18.acacia",
)
```

```javascript
// Override for a single request in Node.js
const charge = await stripe.charges.retrieve('ch_abc123', {
  stripeVersion: '2025-12-18.acacia',
});
```

### SDK Version Compatibility

| SDK | Minimum API Version | Latest SDK Version |
|-----|--------------------|--------------------|
| stripe-python | 2019-08-14 | 8.x |
| stripe-node | 2019-08-14 | 14.x |
| stripe-ruby | 2019-08-14 | 10.x |
| stripe-go | 2019-08-14 | 78.x |
| stripe-java | 2019-08-14 | 25.x |
| stripe-php | 2019-08-14 | 13.x |

## Common Patterns

### Creating a One-Time Charge

The modern way to process a one-time payment uses PaymentIntents:

```python
import stripe

# Create a PaymentIntent
intent = stripe.PaymentIntent.create(
    amount=5000,  # $50.00
    currency="usd",
    payment_method="pm_card_visa",
    confirm=True,
    automatic_payment_methods={
        "enabled": True,
        "allow_redirects": "never",
    },
)

print(f"Payment status: {intent.status}")
# Output: Payment status: succeeded
```

### Creating a Subscription

Subscriptions require a customer with a default payment method and a price object:

```python
# Step 1: Create a product and price
product = stripe.Product.create(
    name="Pro Plan",
    description="Full access to all features",
)

price = stripe.Price.create(
    product=product.id,
    unit_amount=2999,  # $29.99
    currency="usd",
    recurring={"interval": "month"},
)

# Step 2: Create a subscription
subscription = stripe.Subscription.create(
    customer="cus_NkBG2Jx9cFp8LRc",
    items=[{"price": price.id}],
    payment_behavior="default_incomplete",
    expand=["latest_invoice.payment_intent"],
)

# Return the client_secret for the frontend to confirm
client_secret = subscription.latest_invoice.payment_intent.client_secret
```

```javascript
// Node.js equivalent
const subscription = await stripe.subscriptions.create({
  customer: 'cus_NkBG2Jx9cFp8LRc',
  items: [{ price: 'price_1NkBG2Jx9cFp8LRc' }],
  payment_behavior: 'default_incomplete',
  expand: ['latest_invoice.payment_intent'],
});
```

### Handling Subscription Lifecycle Events

Set up webhooks to respond to subscription changes:

```python
# Key webhook events for subscriptions
SUBSCRIPTION_EVENTS = {
    "customer.subscription.created": handle_subscription_created,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_canceled,
    "invoice.payment_succeeded": handle_payment_success,
    "invoice.payment_failed": handle_payment_failure,
    "customer.subscription.trial_will_end": handle_trial_ending,
}
```

## TypeScript Support

The Node.js SDK includes full TypeScript type definitions. No additional `@types` package is needed.

```typescript
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2025-12-18.acacia',
  typescript: true,
});

async function createCustomer(
  email: string,
  name: string,
): Promise<Stripe.Customer> {
  const customer: Stripe.Customer = await stripe.customers.create({
    email,
    name,
  });
  return customer;
}

async function listCharges(
  customerId: string,
): Promise<Stripe.ApiList<Stripe.Charge>> {
  const charges = await stripe.charges.list({
    customer: customerId,
    limit: 10,
  });
  return charges;
}

// Type-safe event handling
function handleWebhookEvent(event: Stripe.Event): void {
  switch (event.type) {
    case 'payment_intent.succeeded': {
      const paymentIntent = event.data.object as Stripe.PaymentIntent;
      console.log(`Payment succeeded: ${paymentIntent.id}`);
      break;
    }
    case 'customer.subscription.deleted': {
      const subscription = event.data.object as Stripe.Subscription;
      console.log(`Subscription canceled: ${subscription.id}`);
      break;
    }
    default:
      console.log(`Unhandled event type: ${event.type}`);
  }
}
```

### Type Imports

Import specific types for use in your application:

```typescript
import Stripe from 'stripe';

// Request parameter types
type CreateCustomerParams = Stripe.CustomerCreateParams;
type CreatePaymentIntentParams = Stripe.PaymentIntentCreateParams;

// Response types
type Customer = Stripe.Customer;
type PaymentIntent = Stripe.PaymentIntent;
type Subscription = Stripe.Subscription;
type Invoice = Stripe.Invoice;

// Event types
type WebhookEvent = Stripe.Event;
type EventType = Stripe.Event.Type;
```

## Error Handling

All Stripe SDKs raise typed exceptions that you can catch and handle appropriately. Stripe errors include a `type`, `code`, `message`, and optionally a `param` indicating which parameter caused the error.

### Error Types

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| `card_error` | 402 | Card was declined or failed validation |
| `invalid_request_error` | 400 | Request had invalid parameters |
| `authentication_error` | 401 | Invalid API key |
| `rate_limit_error` | 429 | Too many requests |
| `api_connection_error` | - | Network communication failure |
| `api_error` | 500+ | Something went wrong on Stripe's end |
| `idempotency_error` | 400 | Idempotency key was reused with different parameters |

### Python Error Handling

```python
import stripe

try:
    charge = stripe.PaymentIntent.create(
        amount=2000,
        currency="usd",
        payment_method="pm_card_chargeDeclined",
        confirm=True,
    )
except stripe.error.CardError as e:
    # Card was declined
    print(f"Card error: {e.user_message}")
    print(f"Error code: {e.code}")  # e.g., "card_declined"
    print(f"Decline code: {e.error.decline_code}")  # e.g., "insufficient_funds"
except stripe.error.RateLimitError:
    # Too many requests -- implement exponential backoff
    print("Rate limited. Retrying...")
except stripe.error.InvalidRequestError as e:
    # Invalid parameters
    print(f"Invalid request: {e.user_message}")
    print(f"Parameter: {e.param}")
except stripe.error.AuthenticationError:
    # Invalid API key
    print("Authentication failed. Check your API key.")
except stripe.error.APIConnectionError:
    # Network error
    print("Network error. Check your internet connection.")
except stripe.error.StripeError as e:
    # Catch-all for other Stripe errors
    print(f"Stripe error: {e.user_message}")
```

### Node.js Error Handling

```javascript
try {
  const paymentIntent = await stripe.paymentIntents.create({
    amount: 2000,
    currency: 'usd',
    payment_method: 'pm_card_chargeDeclined',
    confirm: true,
  });
} catch (error) {
  switch (error.type) {
    case 'StripeCardError':
      console.log(`Card declined: ${error.message}`);
      console.log(`Decline code: ${error.decline_code}`);
      break;
    case 'StripeRateLimitError':
      console.log('Rate limited. Retrying...');
      break;
    case 'StripeInvalidRequestError':
      console.log(`Invalid parameter: ${error.param}`);
      break;
    case 'StripeAuthenticationError':
      console.log('Check your API key.');
      break;
    case 'StripeAPIError':
      console.log('Stripe server error. Try again later.');
      break;
    case 'StripeConnectionError':
      console.log('Network error.');
      break;
    default:
      console.log(`Unexpected error: ${error.message}`);
  }
}
```

### Ruby Error Handling

```ruby
begin
  intent = Stripe::PaymentIntent.create(
    amount: 2000,
    currency: 'usd',
    payment_method: 'pm_card_chargeDeclined',
    confirm: true,
  )
rescue Stripe::CardError => e
  puts "Card error: #{e.message}"
  puts "Code: #{e.code}"
rescue Stripe::RateLimitError
  puts "Rate limited."
rescue Stripe::InvalidRequestError => e
  puts "Invalid request: #{e.message}"
rescue Stripe::AuthenticationError
  puts "Invalid API key."
rescue Stripe::APIConnectionError
  puts "Network error."
rescue Stripe::StripeError => e
  puts "Stripe error: #{e.message}"
end
```

### Go Error Handling

```go
intent, err := paymentintent.New(&stripe.PaymentIntentParams{
    Amount:   stripe.Int64(2000),
    Currency: stripe.String(string(stripe.CurrencyUSD)),
})

if err != nil {
    if stripeErr, ok := err.(*stripe.Error); ok {
        switch stripeErr.Type {
        case stripe.ErrorTypeCard:
            fmt.Printf("Card error: %s\n", stripeErr.Msg)
        case stripe.ErrorTypeInvalidRequest:
            fmt.Printf("Invalid request: %s\n", stripeErr.Msg)
        default:
            fmt.Printf("Stripe error: %s\n", stripeErr.Msg)
        }
    } else {
        fmt.Printf("Other error: %v\n", err)
    }
}
```

## Logging and Debugging

### Enabling SDK Logging

**Python:**

```python
import logging
import stripe

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('stripe')
logger.setLevel(logging.DEBUG)

# Or use Stripe's built-in logging
stripe.log = 'debug'  # 'debug' or 'info'
```

**Node.js:**

```javascript
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY, {
  telemetry: true,
  appInfo: {
    name: 'MyApp',
    version: '1.0.0',
    url: 'https://myapp.com',
  },
});

// Access request/response details
stripe.on('request', (event) => {
  console.log(`Request to ${event.path}`);
  console.log(`Method: ${event.method}`);
});

stripe.on('response', (event) => {
  console.log(`Response status: ${event.status}`);
  console.log(`Request ID: ${event.request_id}`);
  console.log(`Elapsed: ${event.elapsed}ms`);
});
```

**Go:**

```go
import (
    "github.com/stripe/stripe-go/v78"
)

stripe.DefaultLeveledLogger = &stripe.LeveledLogger{
    Level: stripe.LevelDebug,
}
```

### Request IDs

Every Stripe API response includes a unique `Request-Id` header. When contacting Stripe support, always include this ID for faster debugging.

```python
try:
    customer = stripe.Customer.create(email="test@example.com")
    print(f"Request ID: {customer.last_response.request_id}")
except stripe.error.StripeError as e:
    print(f"Request ID: {e.request_id}")
    # Include this when contacting support
```

### Using the Dashboard for Debugging

The Stripe Dashboard provides detailed request logs under **Developers > Logs**. Each log entry shows:

- HTTP method and endpoint
- Request and response bodies
- HTTP status code
- Request ID
- IP address and API key used
- Timestamp

Filter logs by:

| Filter | Example |
|--------|---------|
| Status | `status:200`, `status:402` |
| Method | `method:POST` |
| Endpoint | `/v1/charges`, `/v1/customers` |
| Source | `source:api`, `source:dashboard` |
| IP address | `ip:192.168.1.1` |

### Idempotency Keys

Use idempotency keys to safely retry requests without creating duplicate resources. This is especially important for payment creation.

```python
import uuid

# Generate a unique idempotency key
idempotency_key = str(uuid.uuid4())

intent = stripe.PaymentIntent.create(
    amount=2000,
    currency="usd",
    payment_method="pm_card_visa",
    idempotency_key=idempotency_key,
)

# Retrying with the same key returns the original result
intent_retry = stripe.PaymentIntent.create(
    amount=2000,
    currency="usd",
    payment_method="pm_card_visa",
    idempotency_key=idempotency_key,
)

assert intent.id == intent_retry.id  # Same PaymentIntent
```

```javascript
// Node.js
const intent = await stripe.paymentIntents.create(
  {
    amount: 2000,
    currency: 'usd',
    payment_method: 'pm_card_visa',
  },
  {
    idempotencyKey: 'unique-key-abc123',
  },
);
```

> **Note:** Idempotency keys expire after 24 hours. After expiration, a new request with the same key will create a new resource. Keys are scoped to your API key -- test and live mode keys have separate idempotency namespaces.

---

*Last updated: February 2026. For the latest SDK documentation, visit [https://docs.stripe.com/sdks](https://docs.stripe.com/sdks).*
