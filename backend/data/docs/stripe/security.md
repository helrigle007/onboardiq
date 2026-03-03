<!--
title: Security
url: https://docs.stripe.com/security
topic: security
complexity: advanced
-->

# Security at Stripe

Stripe handles billions of dollars in transactions every year. Security is not an afterthought -- it is foundational to everything we build. This guide covers Stripe's security infrastructure, your responsibilities as an integrator, and the tools available to protect your business and your customers.

## PCI Compliance

### Overview

The Payment Card Industry Data Security Standard (PCI DSS) is a set of security requirements designed to ensure that all companies that accept, process, store, or transmit credit card information maintain a secure environment. Stripe is a **PCI Level 1 Service Provider**, the most stringent level of certification available in the payments industry.

### PCI Compliance Levels

| Level | Transaction Volume | Requirements |
|-------|-------------------|--------------|
| Level 1 | Over 6 million transactions/year | Annual on-site audit by QSA, quarterly network scans |
| Level 2 | 1-6 million transactions/year | Annual self-assessment questionnaire, quarterly network scans |
| Level 3 | 20,000-1 million e-commerce transactions/year | Annual self-assessment questionnaire, quarterly network scans |
| Level 4 | Fewer than 20,000 e-commerce transactions/year | Annual self-assessment questionnaire, quarterly network scans (recommended) |

### Your PCI Obligations

When you use Stripe, the scope of your PCI compliance obligations depends on how you integrate.

**Using Stripe.js and Elements (recommended):** Card data never touches your servers. You qualify for **SAQ A**, the simplest self-assessment questionnaire. This is the approach we strongly recommend for all integrations.

**Using direct API calls with raw card numbers:** Card data passes through your servers. You must comply with **SAQ D**, which includes over 300 security requirements. This approach is only available to users who have been explicitly approved.

> **Warning:** Handling raw card numbers directly significantly increases your PCI compliance burden and exposes you to substantial liability. Always prefer Stripe.js and Elements unless you have a specific, justified reason to handle card data directly.

### PCI Compliance Validation

Stripe provides a PCI compliance dashboard in the Stripe Dashboard under **Settings > Compliance > PCI compliance**. You can:

- View your current PCI compliance status
- Complete your Self-Assessment Questionnaire (SAQ)
- Download your Attestation of Compliance (AOC)

```
GET /v1/accounts/{account_id}/compliance/pci
```

Response:

```json
{
  "object": "pci_compliance",
  "status": "compliant",
  "saq_type": "A",
  "last_validated": "2025-11-15T00:00:00Z",
  "next_validation_due": "2026-11-15T00:00:00Z"
}
```

## Data Security and Encryption

### Encryption in Transit

All communications with the Stripe API and Dashboard are encrypted using **TLS 1.2 or higher**. Stripe does not support older protocols such as TLS 1.0 or TLS 1.1. All API endpoints enforce HTTPS -- plaintext HTTP requests are rejected.

Stripe's TLS configuration supports the following cipher suites:

- `TLS_AES_256_GCM_SHA384`
- `TLS_CHACHA20_POLY1305_SHA256`
- `TLS_AES_128_GCM_SHA256`
- `ECDHE-RSA-AES256-GCM-SHA384`
- `ECDHE-RSA-AES128-GCM-SHA256`

You can verify Stripe's TLS configuration at any time:

```bash
openssl s_client -connect api.stripe.com:443 -tls1_2
```

### Encryption at Rest

All sensitive data stored on Stripe's servers is encrypted at rest using **AES-256** encryption. This includes:

- Card numbers (PANs)
- Bank account numbers
- Personal identification data
- Authentication credentials

Encryption keys are managed through a hardware security module (HSM) infrastructure with strict access controls and automatic key rotation.

### Key Management

Stripe uses a hierarchical key management system:

1. **Master keys** are stored in FIPS 140-2 Level 3 certified HSMs
2. **Data encryption keys (DEKs)** are generated per-record and encrypted by key-encrypting keys (KEKs)
3. **Key rotation** occurs automatically -- DEKs are rotated on each write, KEKs are rotated quarterly

No Stripe employee has access to plaintext encryption keys. All key operations are audited and require multi-party authorization.

## Tokenization and Secure Card Handling

### How Tokenization Works

When a customer enters their card information through Stripe.js or Elements, the card data is sent directly to Stripe's servers, bypassing your infrastructure entirely. Stripe returns a **token** (a `tok_` or `pm_` prefixed string) that represents the card. You use this token in subsequent API calls.

```javascript
// Client-side: Create a token from card details
const { token, error } = await stripe.createToken(cardElement);

if (error) {
  console.error(error.message);
} else {
  // Send token.id to your server
  // token.id looks like: "tok_1NkBG2Jx9cFp8LRcKr4VwXIS"
  await fetch('/api/charge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token: token.id }),
  });
}
```

```python
# Server-side: Use the token to create a charge
import stripe
stripe.api_key = "sk_live_..."

charge = stripe.Charge.create(
    amount=2000,
    currency="usd",
    source=token_id,  # "tok_1NkBG2Jx9cFp8LRcKr4VwXIS"
    description="Payment for order #1234",
)
```

### Token Properties

| Property | Description |
|----------|-------------|
| Single-use | Each token can only be used once for a charge or to attach to a customer |
| Expiry | Tokens expire after 10 minutes if unused |
| Non-reversible | A token cannot be converted back to the original card number |
| Scoped | Tokens are scoped to your Stripe account and cannot be used by other accounts |

### Payment Methods vs Tokens

For new integrations, Stripe recommends using **PaymentMethods** (`pm_`) instead of tokens (`tok_`). PaymentMethods are the modern approach and support a wider range of payment types.

```python
# Creating a PaymentIntent with a PaymentMethod
payment_intent = stripe.PaymentIntent.create(
    amount=2000,
    currency="usd",
    payment_method="pm_1NkBG2Jx9cFp8LRcKr4VwXIS",
    confirm=True,
    return_url="https://example.com/return",
)
```

## Stripe.js and Elements

### Why Use Stripe.js

Stripe.js is a JavaScript library that you load on your payment pages. It communicates directly with Stripe's servers, ensuring that sensitive card data never passes through your backend. Using Stripe.js is the single most impactful step you can take to reduce your PCI scope.

### Loading Stripe.js

Always load Stripe.js from `js.stripe.com`. Never bundle it with your application code or host it on your own servers.

```html
<script src="https://js.stripe.com/v3/"></script>
```

Or using the npm package:

```bash
npm install @stripe/stripe-js
```

```javascript
import { loadStripe } from '@stripe/stripe-js';

const stripe = await loadStripe('pk_live_...');
```

### Elements Integration

Stripe Elements provides pre-built, customizable UI components for collecting payment details.

```javascript
const elements = stripe.elements({
  clientSecret: 'pi_3NkBG2Jx9cFp8LRc_secret_abc123',
  appearance: {
    theme: 'stripe',
    variables: {
      colorPrimary: '#0570de',
      colorBackground: '#ffffff',
      colorText: '#30313d',
      fontFamily: 'Ideal Sans, system-ui, sans-serif',
    },
  },
});

const paymentElement = elements.create('payment');
paymentElement.mount('#payment-element');
```

> **Important:** Never log or store the `clientSecret` on your server beyond the scope of a single request. It grants the ability to confirm a PaymentIntent, which could allow unauthorized charges.

## Fraud Prevention with Stripe Radar

### Overview

Stripe Radar is a suite of machine learning-powered fraud detection tools built directly into Stripe's payment processing pipeline. Radar evaluates every transaction using data from millions of companies across the Stripe network.

### How Radar Scores Transactions

Every payment processed through Stripe receives a **risk score** from 0 to 99. The score represents the estimated probability that the payment is fraudulent.

| Risk Level | Score Range | Default Action |
|------------|------------|----------------|
| Normal | 0-19 | Allow |
| Elevated | 20-64 | Allow (review recommended) |
| High | 65-74 | Place in review |
| Highest | 75-99 | Block |

Access risk evaluations through the API:

```
GET /v1/charges/{charge_id}
```

```json
{
  "id": "ch_3NkBG2Jx9cFp8LRc",
  "outcome": {
    "network_status": "approved_by_network",
    "risk_level": "normal",
    "risk_score": 12,
    "seller_message": "Payment complete.",
    "type": "authorized"
  }
}
```

### Radar Rules

Radar for Fraud Teams (available on Stripe's advanced pricing plan) lets you write custom rules to fine-tune fraud detection for your business.

Rules use a domain-specific language that evaluates transaction attributes:

```
# Block transactions from high-risk countries
Block if :card_country: in ('XX', 'YY', 'ZZ')

# Require review for large transactions from new customers
Review if :amount_in_usd: > 500 AND :customer_transactions: < 3

# Allow transactions from known good customers
Allow if :customer_email_domain: = 'trusted-partner.com'

# Block if the CVC check fails
Block if :cvc_check: = 'fail'

# Block disposable email addresses
Block if :is_disposable_email: = true
```

Available rule attributes include:

| Attribute | Type | Description |
|-----------|------|-------------|
| `:amount_in_usd:` | number | Transaction amount converted to USD |
| `:card_country:` | string | Two-letter ISO country code of the card issuer |
| `:customer_transactions:` | number | Number of previous transactions by this customer |
| `:cvc_check:` | string | Result of the CVC verification (`pass`, `fail`, `unavailable`) |
| `:is_disposable_email:` | boolean | Whether the email address is from a disposable email provider |
| `:ip_country:` | string | Country of the customer's IP address |
| `:card_bin:` | string | First six digits of the card number |
| `:risk_score:` | number | Radar's machine learning risk score |
| `:is_3d_secure:` | boolean | Whether 3D Secure authentication was performed |

### Machine Learning Fraud Detection

Radar's machine learning models are trained on data from across the entire Stripe network. The models evaluate hundreds of signals per transaction, including:

- **Behavioral signals:** Typing speed, mouse movements, session duration
- **Device signals:** Device fingerprint, screen resolution, browser configuration
- **Network signals:** IP geolocation, proxy/VPN detection, ISP information
- **Transaction signals:** Amount, currency, time of day, velocity
- **Historical signals:** Previous chargebacks, disputes, refunds across the network

Radar's models are continuously retrained as new fraud patterns emerge. You do not need to configure or maintain the models -- they improve automatically.

## 3D Secure Authentication

### What is 3D Secure

3D Secure (3DS) adds an additional authentication step during the payment process. The cardholder's bank may prompt them to verify their identity through a one-time password, biometric, or app-based confirmation. 3DS version 2 provides a frictionless flow for low-risk transactions while still authenticating high-risk ones.

### When to Use 3D Secure

- **Regulatory requirement:** Strong Customer Authentication (SCA) under PSD2 in the European Economic Area requires 3DS for most card-present and online transactions.
- **Liability shift:** Successfully authenticated 3DS transactions shift chargeback liability from you to the card issuer.
- **Fraud reduction:** 3DS authentication significantly reduces fraudulent transactions.

### Implementing 3D Secure

When using PaymentIntents, 3D Secure is triggered automatically when required by the card issuer or configured in your Radar rules.

```python
payment_intent = stripe.PaymentIntent.create(
    amount=2000,
    currency="eur",
    payment_method="pm_card_threeDSecure2Required",
    payment_method_options={
        "card": {
            "request_three_d_secure": "automatic"  # or "any" to always request
        }
    },
    confirm=True,
    return_url="https://example.com/return",
)
```

3D Secure outcomes are recorded on the PaymentIntent:

```json
{
  "id": "pi_3NkBG2Jx9cFp8LRc",
  "status": "succeeded",
  "payment_method_options": {
    "card": {
      "three_d_secure": {
        "authentication_flow": "challenge",
        "result": "authenticated",
        "version": "2.2.0"
      }
    }
  }
}
```

## Content Security Policy (CSP)

If your site enforces Content Security Policy headers, you must include the following directives to allow Stripe.js and Elements to function correctly:

```
Content-Security-Policy:
  script-src 'self' https://js.stripe.com https://maps.googleapis.com;
  frame-src 'self' https://js.stripe.com https://hooks.stripe.com;
  connect-src 'self' https://api.stripe.com https://maps.googleapis.com;
  img-src 'self' https://*.stripe.com;
```

> **Warning:** Omitting these CSP directives will cause Stripe.js to fail silently or produce errors in the browser console. Always test your CSP configuration in a staging environment before deploying to production.

### Subresource Integrity (SRI)

Because Stripe.js is hosted on Stripe's CDN and updated regularly, SRI hashes are **not supported**. This is intentional -- Stripe needs to be able to deploy security patches immediately. The tradeoff is controlled: Stripe.js is served over HTTPS from Stripe-owned infrastructure with strict access controls.

## Audit Logging and Access Controls

### Audit Logs

Stripe maintains comprehensive audit logs of all actions taken in your account. These logs are available through the Dashboard under **Settings > Team and security > Audit log** and through the API.

```
GET /v1/events?type=account.*&created[gte]=1700000000&limit=100
```

Audit log events include:

| Event Type | Description |
|------------|-------------|
| `account.updated` | Account settings were changed |
| `api_key.created` | A new API key was created |
| `api_key.deleted` | An API key was revoked |
| `team_member.invited` | A team member was invited |
| `team_member.removed` | A team member was removed |
| `team_member.role_changed` | A team member's role was changed |
| `payout.manual` | A manual payout was initiated |
| `webhook_endpoint.created` | A webhook endpoint was configured |

### API Key Security

Stripe provides two types of API keys:

- **Publishable keys** (`pk_live_`, `pk_test_`): Safe to include in client-side code. Can only create tokens and confirm PaymentIntents.
- **Secret keys** (`sk_live_`, `sk_test_`): Must be kept on your server. Full API access.

Best practices for API key management:

1. **Never commit secret keys to version control.** Use environment variables or a secrets manager.
2. **Use restricted keys** with specific permissions when possible.
3. **Rotate keys periodically.** You can create new keys and revoke old ones with zero downtime.
4. **Use test mode keys** (`sk_test_`, `pk_test_`) for development and testing.

```bash
# Good: load from environment
export STRIPE_SECRET_KEY="sk_live_..."

# Bad: hardcoded in source code
stripe.api_key = "sk_live_..."  # NEVER DO THIS
```

### Restricted API Keys

For applications that only need access to specific API resources, create restricted keys:

```
POST /v1/api_keys
{
  "name": "Inventory service key",
  "permissions": {
    "products": "write",
    "prices": "write",
    "charges": "none",
    "customers": "read"
  }
}
```

## Team Member Permissions and Roles

Stripe supports role-based access control for team members. Assign the minimum permissions required for each team member's responsibilities.

### Built-in Roles

| Role | Permissions |
|------|-------------|
| Administrator | Full access to all settings, data, and operations |
| Developer | API keys, webhooks, logs. No access to financial operations |
| Analyst | Read-only access to all data. No settings changes |
| Support specialist | Customer and charge data. Can issue refunds |
| View only | Read-only access to the Dashboard |

### Custom Roles

You can create custom roles with granular permissions:

```
POST /v1/accounts/{account_id}/roles
{
  "name": "Refund manager",
  "permissions": [
    "charges.read",
    "charges.refund",
    "customers.read",
    "disputes.read",
    "disputes.respond"
  ]
}
```

### Two-Factor Authentication

Stripe strongly recommends enabling two-factor authentication (2FA) for all team members. You can enforce 2FA across your organization:

**Dashboard:** Settings > Team and security > Authentication > Require two-step authentication

When 2FA is enforced, team members who have not configured it will be required to set it up on their next login.

## Data Residency and Privacy

### GDPR Compliance

Stripe is a data processor under the General Data Protection Regulation (GDPR). Stripe provides:

- A **Data Processing Agreement (DPA)** for all users, available in the Dashboard
- Tools to fulfill **data subject access requests (DSARs)**
- **Data deletion** capabilities for customer records
- **Data portability** through the API and Dashboard exports

### Responding to Data Requests

Use the API to retrieve all data associated with a customer:

```python
# Retrieve all data for a customer (DSAR)
customer = stripe.Customer.retrieve(
    "cus_NkBG2Jx9cFp8LRc",
    expand=["sources", "subscriptions", "charges"],
)

# Delete a customer and all associated data
stripe.Customer.delete("cus_NkBG2Jx9cFp8LRc")
```

> **Important:** Deleting a customer is irreversible. Stripe retains certain data as required by financial regulations and legal obligations even after deletion. See Stripe's privacy policy for details on retention periods.

### Data Residency

Stripe processes and stores data primarily in the United States. For businesses with data residency requirements, Stripe offers:

- **Stripe Data Pipeline** for exporting data to your own infrastructure
- **Regional processing** options for certain payment methods
- Contractual commitments through Standard Contractual Clauses (SCCs) for EU-US data transfers

## Security Best Practices Checklist

Use this checklist to verify that your Stripe integration follows security best practices:

- [ ] **Use Stripe.js or Elements** for all payment form fields -- never collect card data on your own servers
- [ ] **Serve your payment pages over HTTPS** -- Stripe.js requires a secure context
- [ ] **Store secret API keys securely** -- use environment variables or a secrets manager, never commit to source control
- [ ] **Use restricted API keys** -- grant only the permissions each service requires
- [ ] **Enable Stripe Radar** -- active by default, but review and customize your rules
- [ ] **Implement 3D Secure** -- required for SCA compliance in the EEA, recommended globally
- [ ] **Configure CSP headers** -- whitelist Stripe's domains if you use Content Security Policy
- [ ] **Enable 2FA for all team members** -- enforce it organization-wide if possible
- [ ] **Review audit logs regularly** -- check for unauthorized access or suspicious activity
- [ ] **Use webhook signature verification** -- always verify the `Stripe-Signature` header on incoming webhooks
- [ ] **Keep your SDK up to date** -- security patches are released regularly
- [ ] **Use idempotency keys** -- prevent duplicate charges from network retries
- [ ] **Set up alerts** -- configure email or Slack alerts for high-risk events (large charges, disputes, failed payments)

### Webhook Signature Verification

Always verify webhook signatures to ensure events are genuinely from Stripe:

```python
import stripe

endpoint_secret = "whsec_..."

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Process the event
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        handle_successful_payment(payment_intent)

    return {"status": "success"}
```

## Reporting Security Vulnerabilities

Stripe takes security vulnerabilities seriously. If you discover a potential security issue, report it through Stripe's responsible disclosure program.

### How to Report

1. **Email:** Send a detailed report to `security@stripe.com`
2. **Bug bounty:** Stripe participates in a bug bounty program through HackerOne at `https://hackerone.com/stripe`

### Disclosure Guidelines

- Provide a detailed description of the vulnerability, including steps to reproduce
- Allow reasonable time for Stripe to investigate and address the issue before public disclosure
- Do not access, modify, or delete data belonging to other Stripe users
- Do not degrade Stripe's services or disrupt other users

### Scope

The following are in scope for vulnerability reports:

- `api.stripe.com`
- `js.stripe.com`
- `dashboard.stripe.com`
- `connect.stripe.com`
- Stripe's open-source libraries (stripe-node, stripe-python, etc.)
- Stripe mobile SDKs (stripe-ios, stripe-android)

### Recognition

Stripe acknowledges security researchers who responsibly disclose valid vulnerabilities. Depending on the severity and impact of the finding, Stripe may offer monetary rewards through the HackerOne bug bounty program.

---

*Last updated: February 2026. For the latest security documentation, visit [https://docs.stripe.com/security](https://docs.stripe.com/security).*
