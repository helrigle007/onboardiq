import type { GuideResponse, GuideSection, SectionEvaluation, DimensionScore } from '../types';

function makeDimensions(scores: Record<string, number>): DimensionScore[] {
  const descriptions: Record<string, { reasoning: string; suggestions: string[] }> = {
    completeness: {
      reasoning: 'Covers the topic thoroughly with relevant subtopics and practical details.',
      suggestions: ['Could expand on edge cases for production environments.'],
    },
    role_relevance: {
      reasoning: 'Content is specifically tailored for security engineering workflows.',
      suggestions: ['Consider adding more threat-modeling perspectives.'],
    },
    actionability: {
      reasoning: 'Provides concrete steps and code examples that can be implemented immediately.',
      suggestions: ['Add more copy-paste ready configuration snippets.'],
    },
    clarity: {
      reasoning: 'Well-structured with clear headings and logical progression.',
      suggestions: ['Some sections could benefit from summary tables.'],
    },
    progressive_complexity: {
      reasoning: 'Builds from foundational concepts to advanced implementation patterns.',
      suggestions: ['The jump between sections 3 and 4 could be smoother.'],
    },
  };

  return Object.entries(scores).map(([dimension, score]) => ({
    dimension,
    score,
    reasoning: descriptions[dimension]?.reasoning ?? '',
    suggestions: descriptions[dimension]?.suggestions ?? [],
  }));
}

function makeSectionEval(sectionNumber: number, overallScore: number, dimScores: Record<string, number>): SectionEvaluation {
  return {
    section_number: sectionNumber,
    overall_score: overallScore,
    dimensions: makeDimensions(dimScores),
    pass_threshold: overallScore >= 0.7,
    needs_regeneration: overallScore < 0.7,
  };
}

const section1: GuideSection = {
  section_number: 1,
  title: 'Platform Overview & Security Architecture',
  summary: 'Understanding Stripe\'s security model, trust boundaries, and how the platform architecture impacts your security posture.',
  content: `## Stripe's Security-First Architecture

Stripe processes hundreds of billions of dollars annually and has built its platform around a defense-in-depth security model. As a security engineer integrating Stripe, understanding the platform's trust boundaries is your first priority.

### Trust Boundaries

Stripe's architecture establishes three distinct trust zones:

1. **Client-side (untrusted)** — Browser or mobile app. Never trust data originating here.
2. **Your server (semi-trusted)** — Your backend communicates with Stripe's API using secret keys.
3. **Stripe's infrastructure (trusted)** — PCI Level 1 certified, handles all sensitive card data.

The critical insight: **your server never needs to touch raw card numbers**. Stripe.js and Elements tokenize card data client-side, sending only tokens to your backend. This dramatically reduces your PCI scope.

### API Communication Model

All communication with Stripe uses TLS 1.2+ with certificate pinning available for mobile SDKs. The API enforces mutual authentication via API keys, and every request is logged with full audit trails accessible via the Dashboard.

### Key Security Principles

- **Least privilege**: Use restricted keys scoped to only the permissions each service needs
- **Defense in depth**: Combine API key restrictions, webhook verification, and idempotency keys
- **Zero trust**: Validate all incoming data, even from Stripe webhooks, using signature verification`,
  key_takeaways: [
    'Stripe uses a defense-in-depth model with three distinct trust zones',
    'Client-side tokenization keeps raw card data off your servers',
    'Always use restricted API keys with minimal required permissions',
    'All API communication uses TLS 1.2+ with full audit logging',
  ],
  code_examples: [
    {
      language: 'python',
      code: `import stripe

# Use restricted keys — never your full secret key in production
stripe.api_key = os.environ["STRIPE_RESTRICTED_KEY"]

# Verify the key has limited permissions
try:
    stripe.Account.retrieve()
except stripe.error.PermissionError:
    print("Key is properly restricted — cannot access account details")`,
      description: 'Configuring Stripe with a restricted API key and verifying permissions',
    },
    {
      language: 'typescript',
      code: `// Client-side: Use Stripe Elements to tokenize card data
// The raw card number NEVER touches your server
const { error, paymentMethod } = await stripe.createPaymentMethod({
  type: 'card',
  card: cardElement,  // Stripe Element — not raw card data
  billing_details: { name: 'Security Engineer' },
});

if (error) {
  console.error('Tokenization failed:', error.message);
} else {
  // Send only the token ID to your backend
  await fetch('/api/payment', {
    method: 'POST',
    body: JSON.stringify({ payment_method_id: paymentMethod.id }),
  });
}`,
      description: 'Client-side tokenization with Stripe Elements — card data never reaches your server',
    },
  ],
  warnings: [
    'Never log or store raw API keys in source code — use environment variables or a secrets manager.',
  ],
  citations: [
    {
      source_url: 'https://docs.stripe.com/security',
      source_title: 'Stripe Security Overview',
      chunk_id: 'stripe-security-overview-001',
      relevance_score: 0.95,
    },
    {
      source_url: 'https://docs.stripe.com/keys',
      source_title: 'API Keys - Stripe Documentation',
      chunk_id: 'stripe-api-keys-002',
      relevance_score: 0.91,
    },
  ],
  estimated_time_minutes: 15,
  prerequisites: [],
};

const section2: GuideSection = {
  section_number: 2,
  title: 'API Authentication & Key Management',
  summary: 'Best practices for managing Stripe API keys, implementing key rotation, and securing service-to-service authentication.',
  content: `## API Key Hierarchy

Stripe provides several types of API keys, each with different security implications:

### Key Types

| Key Type | Prefix | Use Case | Risk Level |
|----------|--------|----------|------------|
| Publishable | \`pk_\` | Client-side tokenization | Low — safe to expose |
| Secret | \`sk_\` | Server-side API calls | **Critical** — never expose |
| Restricted | \`rk_\` | Scoped server operations | Medium — limited blast radius |

### Restricted Keys (Recommended)

Restricted keys are the gold standard for production. Create keys that can only access the specific resources each service needs:

- **Payment service**: \`charges:write\`, \`payment_intents:write\`
- **Reporting service**: \`charges:read\`, \`balance:read\`
- **Webhook processor**: \`events:read\`

### Key Rotation Strategy

Implement automated key rotation on a 90-day cycle. Stripe supports multiple active keys, enabling zero-downtime rotation:

1. Generate new restricted key in Dashboard
2. Deploy new key to your secrets manager
3. Gradually roll out to services (canary → full)
4. Verify no traffic on old key via Stripe Dashboard logs
5. Revoke old key

### Secrets Management

Never store keys in environment variables on shared systems. Use a proper secrets manager:

- **AWS**: Secrets Manager or Parameter Store (SecureString)
- **GCP**: Secret Manager with IAM-scoped access
- **Self-hosted**: HashiCorp Vault with dynamic secrets`,
  key_takeaways: [
    'Use restricted keys in production — never raw secret keys',
    'Implement 90-day automated key rotation with zero-downtime rollover',
    'Store keys in a secrets manager, not environment variables on shared systems',
    'Each service should have its own restricted key with minimal permissions',
  ],
  code_examples: [
    {
      language: 'python',
      code: `import boto3
import stripe
from functools import lru_cache

def get_stripe_key() -> str:
    """Retrieve Stripe key from AWS Secrets Manager with caching."""
    client = boto3.client("secretsmanager", region_name="us-east-1")
    response = client.get_secret_value(SecretId="stripe/restricted-key/payments")
    return response["SecretString"]

# Initialize with secrets manager
stripe.api_key = get_stripe_key()`,
      description: 'Retrieving Stripe keys from AWS Secrets Manager instead of environment variables',
    },
    {
      language: 'python',
      code: `# Key rotation script — run via scheduled job
import stripe
from datetime import datetime, timedelta

def rotate_stripe_key(old_key_id: str) -> dict:
    """Rotate a restricted API key with zero downtime."""
    # Step 1: Create new key with same permissions
    new_key = stripe.api_keys.create(
        name=f"payments-service-{datetime.now().strftime('%Y%m%d')}",
        permissions={"charges": "write", "payment_intents": "write"},
    )

    # Step 2: Update secrets manager
    update_secret("stripe/restricted-key/payments", new_key.secret)

    # Step 3: Schedule old key revocation (48h grace period)
    schedule_revocation(old_key_id, datetime.now() + timedelta(hours=48))

    return {"new_key_id": new_key.id, "revocation_scheduled": True}`,
      description: 'Automated key rotation with zero-downtime grace period',
    },
    {
      language: 'bash',
      code: `# Scan your codebase for accidentally committed keys
# Add this to your CI/CD pipeline
grep -rn "sk_live_\\|sk_test_\\|rk_live_\\|rk_test_" \\
  --include="*.py" --include="*.ts" --include="*.js" \\
  --include="*.env" --include="*.yaml" --include="*.json" \\
  . && echo "FAIL: API keys found in source!" && exit 1 \\
  || echo "PASS: No API keys in source"`,
      description: 'CI pipeline check to prevent API key leaks in source code',
    },
  ],
  warnings: [
    'A leaked secret key (sk_live_*) gives full access to your Stripe account. Rotate immediately if compromised.',
    'Publishable keys (pk_*) are safe to include in client-side code but should NOT be used in server-side API calls.',
  ],
  citations: [
    {
      source_url: 'https://docs.stripe.com/keys#limit-access',
      source_title: 'Restricted API Keys - Stripe Docs',
      chunk_id: 'stripe-restricted-keys-003',
      relevance_score: 0.94,
    },
    {
      source_url: 'https://docs.stripe.com/security/guide',
      source_title: 'Integration Security Guide',
      chunk_id: 'stripe-security-guide-004',
      relevance_score: 0.87,
    },
  ],
  estimated_time_minutes: 20,
  prerequisites: ['Basic understanding of Stripe API structure'],
};

const section3: GuideSection = {
  section_number: 3,
  title: 'Webhook Security & Signature Verification',
  summary: 'Implementing cryptographically secure webhook handling with signature verification, replay protection, and idempotent processing.',
  content: `## Why Webhook Security Matters

Webhooks are Stripe's primary mechanism for notifying your application about events — successful payments, disputes, subscription changes, etc. An attacker who can forge webhook events could trick your application into:

- Granting access to unpaid services
- Processing fraudulent refunds
- Corrupting your financial records

### Signature Verification

Every Stripe webhook includes a \`Stripe-Signature\` header containing an HMAC-SHA256 signature. **Always verify this signature** before processing any event.

The signature scheme includes:
- **Timestamp** (\`t\`): When Stripe sent the event (for replay protection)
- **Signature** (\`v1\`): HMAC-SHA256 of \`{timestamp}.{payload}\` using your webhook signing secret

### Replay Attack Prevention

Even with valid signatures, an attacker could capture and replay legitimate webhook events. Protect against this by:

1. **Timestamp tolerance**: Reject events older than 5 minutes (Stripe SDK default: 300 seconds)
2. **Idempotency**: Track processed event IDs to prevent duplicate processing
3. **Event verification**: Optionally re-fetch the event from Stripe's API for critical operations

### Endpoint Hardening

- Use HTTPS exclusively (Stripe enforces this in production)
- Implement rate limiting on your webhook endpoint
- Return 200 quickly, then process asynchronously
- Use a queue (Redis, SQS) for reliable processing with retries`,
  key_takeaways: [
    'Always verify webhook signatures — never process unverified events',
    'Implement replay protection with timestamp checks and idempotent processing',
    'Return 200 immediately and process events asynchronously via a queue',
    'Store processed event IDs to prevent duplicate processing',
  ],
  code_examples: [
    {
      language: 'python',
      code: `from fastapi import FastAPI, Request, HTTPException
import stripe

app = FastAPI()
WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]

@app.post("/webhooks/stripe")
async def handle_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Verify signature — this checks HMAC and timestamp
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Check for duplicate processing (idempotency)
    if await is_event_processed(event.id):
        return {"status": "already_processed"}

    # Process asynchronously via task queue
    await enqueue_event(event)
    await mark_event_processed(event.id)

    return {"status": "received"}`,
      description: 'Secure webhook endpoint with signature verification and idempotent processing',
    },
    {
      language: 'python',
      code: `import redis
from datetime import timedelta

redis_client = redis.Redis()

async def is_event_processed(event_id: str) -> bool:
    """Check if webhook event was already processed."""
    return redis_client.exists(f"webhook:processed:{event_id}")

async def mark_event_processed(event_id: str) -> None:
    """Mark event as processed with 72h TTL for cleanup."""
    redis_client.setex(
        f"webhook:processed:{event_id}",
        timedelta(hours=72),
        "1"
    )`,
      description: 'Redis-based idempotency tracking for webhook events',
    },
  ],
  warnings: [
    'Never process webhook events without verifying the Stripe-Signature header. This is your primary defense against forged events.',
    'The webhook signing secret (whsec_*) is different from your API key. Each endpoint has its own secret.',
  ],
  citations: [
    {
      source_url: 'https://docs.stripe.com/webhooks/signatures',
      source_title: 'Webhook Signature Verification',
      chunk_id: 'stripe-webhook-sig-005',
      relevance_score: 0.97,
    },
    {
      source_url: 'https://docs.stripe.com/webhooks/best-practices',
      source_title: 'Webhook Best Practices',
      chunk_id: 'stripe-webhook-bp-006',
      relevance_score: 0.89,
    },
  ],
  estimated_time_minutes: 25,
  prerequisites: ['Understanding of HMAC signatures', 'Familiarity with async task queues'],
};

const section4: GuideSection = {
  section_number: 4,
  title: 'PCI Compliance & Data Handling',
  summary: 'Navigating PCI DSS requirements when integrating Stripe, minimizing your compliance scope, and implementing proper data handling.',
  content: `## PCI DSS and Stripe

The Payment Card Industry Data Security Standard (PCI DSS) applies to anyone who stores, processes, or transmits cardholder data. Stripe significantly reduces your PCI burden, but doesn't eliminate it entirely.

### Your PCI Scope with Stripe

Using Stripe Elements or Checkout, your PCI scope is minimal (**SAQ A** or **SAQ A-EP**):

| Integration Method | PCI Level | Your Responsibility |
|-------------------|-----------|-------------------|
| Stripe Checkout (hosted) | SAQ A | Almost nothing — Stripe hosts the payment page |
| Stripe Elements | SAQ A-EP | Secure your page that embeds Elements |
| Direct API (raw card numbers) | SAQ D | **Full PCI compliance** — avoid this |

### Data Classification

Classify all Stripe-related data in your system:

- **Prohibited**: Raw card numbers (PAN), CVV, full magnetic stripe data
- **Sensitive**: Customer IDs, Payment Intent IDs, bank account tokens
- **Internal**: Charge amounts, subscription metadata, invoice data
- **Public**: Publishable API keys, product catalog info

### Secure Data Handling Practices

Even though Stripe handles the most sensitive data, your application must still:

1. **Never log payment identifiers** at DEBUG level — use structured logging with redaction
2. **Encrypt at rest** any Stripe customer or payment IDs stored in your database
3. **Implement access controls** — not every service or team member needs access to payment data
4. **Audit trail** — log all access to payment-related endpoints with user identity`,
  key_takeaways: [
    'Use Stripe Elements or Checkout to minimize PCI scope to SAQ A / SAQ A-EP',
    'Never handle raw card numbers — this triggers full PCI DSS compliance (SAQ D)',
    'Classify all Stripe data and apply appropriate security controls per classification',
    'Implement structured logging with automatic redaction of sensitive fields',
  ],
  code_examples: [
    {
      language: 'python',
      code: `import logging
import re

class StripeRedactingFilter(logging.Filter):
    """Redact sensitive Stripe data from logs."""
    PATTERNS = [
        (re.compile(r'sk_(live|test)_[a-zA-Z0-9]+'), 'sk_***REDACTED***'),
        (re.compile(r'pi_[a-zA-Z0-9]+'), 'pi_***'),
        (re.compile(r'cus_[a-zA-Z0-9]+'), 'cus_***'),
        (re.compile(r'\\b\\d{13,19}\\b'), '****CARD****'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        for pattern, replacement in self.PATTERNS:
            msg = pattern.sub(replacement, msg)
        record.msg = msg
        record.args = ()
        return True

# Apply to all loggers
logging.getLogger().addFilter(StripeRedactingFilter())`,
      description: 'Automatic redaction filter to prevent sensitive Stripe data from appearing in logs',
    },
    {
      language: 'python',
      code: `from cryptography.fernet import Fernet
from sqlalchemy import Column, String, TypeDecorator

class EncryptedString(TypeDecorator):
    """SQLAlchemy type that encrypts Stripe IDs at rest."""
    impl = String
    cache_ok = True

    def __init__(self, key: bytes):
        super().__init__()
        self.fernet = Fernet(key)

    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.fernet.encrypt(value.encode()).decode()
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.fernet.decrypt(value.encode()).decode()
        return value`,
      description: 'SQLAlchemy encrypted column type for storing Stripe customer and payment IDs at rest',
    },
  ],
  warnings: [
    'Handling raw card numbers (PAN) in your backend requires full PCI DSS compliance (SAQ D) — a costly and complex certification process. Use Stripe Elements instead.',
  ],
  citations: [
    {
      source_url: 'https://docs.stripe.com/security/guide#pci-compliance',
      source_title: 'PCI Compliance - Stripe Security Guide',
      chunk_id: 'stripe-pci-007',
      relevance_score: 0.93,
    },
    {
      source_url: 'https://docs.stripe.com/security#encryption',
      source_title: 'Encryption at Stripe',
      chunk_id: 'stripe-encryption-008',
      relevance_score: 0.84,
    },
  ],
  estimated_time_minutes: 20,
  prerequisites: ['Section 1: Platform Overview', 'Basic understanding of PCI DSS'],
};

const section5: GuideSection = {
  section_number: 5,
  title: 'Fraud Prevention & Risk Management',
  summary: 'Leveraging Stripe Radar for fraud detection, implementing custom rules, and building a layered fraud prevention strategy.',
  content: `## Stripe Radar Overview

Stripe Radar is a machine learning-based fraud detection system that evaluates every transaction using hundreds of signals. As a security engineer, you can augment Radar's built-in intelligence with custom rules tailored to your business.

### Risk Score Analysis

Every charge and payment intent receives a \`risk_score\` from 0-100 and a \`risk_level\`:

- **normal** (0-20): Low risk, auto-approve
- **elevated** (20-65): Higher risk, may warrant manual review
- **highest** (65-100): Very high risk, consider blocking

### Custom Radar Rules

Create rules that combine Stripe's signals with your business logic:

\`\`\`
Block if :risk_score: > 80
Review if :card_country: != :ip_country: AND :amount_in_usd: > 500
Block if :is_disposable_email:
Allow if :customer_lifetime_value: > 10000
\`\`\`

### Layered Fraud Prevention

Don't rely solely on Stripe Radar. Build a multi-layer defense:

1. **Stripe Radar** — ML-based scoring on every transaction
2. **3D Secure** — Shift liability for card-present fraud to card issuers
3. **Velocity checks** — Rate limit transactions per customer/IP/card
4. **Device fingerprinting** — Identify suspicious device patterns
5. **Manual review queue** — Human review for high-value or elevated-risk transactions

### 3D Secure Implementation

3D Secure (3DS) adds an authentication step for card payments. It's required in the EU (SCA/PSD2) and recommended globally for high-value transactions.`,
  key_takeaways: [
    'Stripe Radar provides ML-based fraud scoring on every transaction',
    'Custom Radar rules let you combine Stripe signals with business logic',
    'Implement 3D Secure for high-value transactions and EU compliance (SCA)',
    'Build layered defense: Radar + 3DS + velocity checks + manual review',
  ],
  code_examples: [
    {
      language: 'python',
      code: `import stripe

def create_secure_payment(amount: int, currency: str, customer_id: str) -> dict:
    """Create a payment with 3DS and Radar metadata."""
    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency=currency,
        customer=customer_id,
        payment_method_types=["card"],
        # Request 3D Secure when recommended by Radar
        payment_method_options={
            "card": {
                "request_three_d_secure": "automatic",
            },
        },
        # Pass metadata for custom Radar rules
        metadata={
            "customer_account_age_days": "365",
            "customer_order_count": "12",
            "customer_verified_email": "true",
        },
    )
    return {
        "client_secret": intent.client_secret,
        "risk_level": intent.charges.data[0].outcome.risk_level if intent.charges.data else None,
    }`,
      description: 'Creating a payment with automatic 3D Secure and custom Radar metadata',
    },
    {
      language: 'python',
      code: `from collections import defaultdict
from datetime import datetime, timedelta
import redis

redis_client = redis.Redis()

class VelocityChecker:
    """Rate limit transactions to detect fraud patterns."""

    LIMITS = {
        "card": {"count": 5, "window_minutes": 60},
        "ip": {"count": 10, "window_minutes": 60},
        "email": {"count": 3, "window_minutes": 30},
    }

    def check(self, dimension: str, value: str) -> bool:
        """Returns True if within limits, False if velocity exceeded."""
        key = f"velocity:{dimension}:{value}"
        limit = self.LIMITS[dimension]

        pipe = redis_client.pipeline()
        now = datetime.now().timestamp()
        window_start = now - (limit["window_minutes"] * 60)

        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, limit["window_minutes"] * 60)

        results = pipe.execute()
        current_count = results[2]

        return current_count <= limit["count"]`,
      description: 'Redis-based velocity checker for detecting rapid transaction patterns',
    },
  ],
  warnings: [
    'Overly aggressive fraud rules can block legitimate customers. Monitor your false-positive rate and adjust rules gradually.',
  ],
  citations: [
    {
      source_url: 'https://docs.stripe.com/radar',
      source_title: 'Stripe Radar - Fraud Detection',
      chunk_id: 'stripe-radar-009',
      relevance_score: 0.92,
    },
    {
      source_url: 'https://docs.stripe.com/payments/3d-secure',
      source_title: '3D Secure Authentication',
      chunk_id: 'stripe-3ds-010',
      relevance_score: 0.86,
    },
  ],
  estimated_time_minutes: 25,
  prerequisites: ['Section 2: API Authentication', 'Section 3: Webhook Security'],
};

const section6: GuideSection = {
  section_number: 6,
  title: 'Monitoring, Logging & Incident Response',
  summary: 'Building comprehensive observability for your Stripe integration with structured logging, alerting, and incident response playbooks.',
  content: `## Observability for Payment Systems

Payment systems demand higher observability standards than typical applications. A missed alert on a payment failure could mean lost revenue; a missed alert on a security anomaly could mean fraud.

### Structured Logging Strategy

Implement structured JSON logging for all Stripe interactions:

- **Request logging**: API call method, endpoint, duration, status code
- **Event logging**: Webhook event type, processing duration, outcome
- **Error logging**: Error type, error code, idempotency key, retry count
- **Audit logging**: Who accessed what payment data, when, and why

### Key Metrics to Track

| Metric | Alert Threshold | Severity |
|--------|----------------|----------|
| Payment success rate | < 95% over 5min | Critical |
| Webhook processing latency | > 30s p95 | Warning |
| API error rate (5xx) | > 1% over 5min | Critical |
| Fraud block rate | > 10% of transactions | Warning |
| Key usage on revoked keys | Any | Critical |

### Incident Response

Build runbooks for common Stripe-related incidents:

1. **Payment processing outage**: Check Stripe Status page → fall back to queuing → notify customers
2. **Webhook delivery failure**: Monitor Stripe Dashboard → check endpoint health → replay missed events
3. **Suspected key compromise**: Rotate keys immediately → audit recent API calls → check for unauthorized charges
4. **Fraud spike**: Tighten Radar rules → enable 3DS for all transactions → investigate pattern

### Dashboard and Alerting

Build a real-time dashboard showing:
- Transaction volume and success rate (5-minute windows)
- Revenue processed (daily rolling)
- Fraud score distribution
- Webhook processing queue depth
- API latency percentiles (p50, p95, p99)`,
  key_takeaways: [
    'Implement structured JSON logging for all Stripe API interactions and webhooks',
    'Track payment success rate, webhook latency, and fraud rates as primary metrics',
    'Build incident response runbooks for common payment system failures',
    'Set up real-time alerting with appropriate severity levels per metric',
  ],
  code_examples: [
    {
      language: 'python',
      code: `import structlog
import time
from functools import wraps

logger = structlog.get_logger()

def log_stripe_call(func):
    """Decorator for structured logging of Stripe API calls."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.monotonic()
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.monotonic() - start) * 1000
            logger.info(
                "stripe_api_call",
                function=func.__name__,
                duration_ms=round(duration_ms, 2),
                status="success",
            )
            return result
        except stripe.error.StripeError as e:
            duration_ms = (time.monotonic() - start) * 1000
            logger.error(
                "stripe_api_call",
                function=func.__name__,
                duration_ms=round(duration_ms, 2),
                status="error",
                error_type=type(e).__name__,
                error_code=e.code,
                http_status=e.http_status,
            )
            raise
    return wrapper`,
      description: 'Structured logging decorator for monitoring Stripe API call performance and errors',
    },
    {
      language: 'python',
      code: `from prometheus_client import Counter, Histogram, Gauge

# Payment metrics
payment_total = Counter(
    "stripe_payments_total",
    "Total payment attempts",
    ["status", "currency"]
)
payment_amount = Histogram(
    "stripe_payment_amount_usd",
    "Payment amounts in USD",
    buckets=[10, 50, 100, 500, 1000, 5000, 10000]
)
webhook_latency = Histogram(
    "stripe_webhook_processing_seconds",
    "Webhook processing duration",
    ["event_type"]
)
fraud_score = Histogram(
    "stripe_radar_risk_score",
    "Distribution of Radar risk scores",
    buckets=[10, 20, 40, 60, 80, 100]
)`,
      description: 'Prometheus metrics for monitoring Stripe payment processing performance',
    },
  ],
  warnings: [
    'Never disable payment alerting for "noisy" metrics — instead tune the thresholds. Silent payment failures directly impact revenue.',
  ],
  citations: [
    {
      source_url: 'https://docs.stripe.com/monitoring',
      source_title: 'Monitoring Your Integration',
      chunk_id: 'stripe-monitoring-011',
      relevance_score: 0.90,
    },
    {
      source_url: 'https://docs.stripe.com/error-handling',
      source_title: 'Error Handling - Stripe',
      chunk_id: 'stripe-errors-012',
      relevance_score: 0.85,
    },
  ],
  estimated_time_minutes: 20,
  prerequisites: ['Section 3: Webhook Security', 'Familiarity with observability tools (Prometheus, Grafana, etc.)'],
};

const sectionEvaluations: SectionEvaluation[] = [
  makeSectionEval(1, 0.92, {
    completeness: 0.90,
    role_relevance: 0.95,
    actionability: 0.88,
    clarity: 0.94,
    progressive_complexity: 0.93,
  }),
  makeSectionEval(2, 0.88, {
    completeness: 0.85,
    role_relevance: 0.92,
    actionability: 0.90,
    clarity: 0.88,
    progressive_complexity: 0.85,
  }),
  makeSectionEval(3, 0.95, {
    completeness: 0.94,
    role_relevance: 0.97,
    actionability: 0.96,
    clarity: 0.93,
    progressive_complexity: 0.95,
  }),
  makeSectionEval(4, 0.78, {
    completeness: 0.75,
    role_relevance: 0.80,
    actionability: 0.72,
    clarity: 0.82,
    progressive_complexity: 0.81,
  }),
  makeSectionEval(5, 0.85, {
    completeness: 0.83,
    role_relevance: 0.88,
    actionability: 0.87,
    clarity: 0.84,
    progressive_complexity: 0.83,
  }),
  makeSectionEval(6, 0.90, {
    completeness: 0.88,
    role_relevance: 0.92,
    actionability: 0.91,
    clarity: 0.90,
    progressive_complexity: 0.89,
  }),
];

const metadata = {
  model: 'claude-sonnet-4-20250514',
  total_tokens_used: 48672,
  total_cost_usd: 0.1847,
  generation_time_seconds: 34.7,
  retrieval_latency_ms: 245,
  chunks_retrieved: 42,
  chunks_after_reranking: 18,
  regeneration_count: 1,
  langsmith_trace_url: 'https://smith.langchain.com/public/abc123/r',
};

export const mockGuide: GuideResponse = {
  id: 'guide_01HXYZ789ABC',
  product: 'stripe',
  role: 'security_engineer',
  title: 'Stripe Security Integration Guide',
  description: 'A comprehensive security-focused guide to integrating Stripe payment processing, covering API security, PCI compliance, fraud prevention, and monitoring best practices.',
  sections: [section1, section2, section3, section4, section5, section6],
  evaluation: {
    guide_id: 'guide_01HXYZ789ABC',
    overall_score: 0.88,
    section_evaluations: sectionEvaluations,
    generation_metadata: metadata,
  },
  metadata,
  created_at: '2026-03-03T12:00:00Z',
};

export const mockSSESequence: Array<{ event: import('../types').SSEEvent; delay: number }> = [
  { event: { type: 'agent_start', agent: 'role_profiler', message: 'Analyzing security engineer role profile...' }, delay: 0 },
  { event: { type: 'agent_complete', agent: 'role_profiler', duration_ms: 1200 }, delay: 1200 },
  { event: { type: 'agent_start', agent: 'content_curator', message: 'Retrieving relevant documentation...' }, delay: 200 },
  { event: { type: 'agent_complete', agent: 'content_curator', duration_ms: 2400 }, delay: 2400 },
  { event: { type: 'agent_start', agent: 'guide_generator', message: 'Generating guide sections...' }, delay: 200 },
  { event: { type: 'section_generated', section: section1, index: 0 }, delay: 1500 },
  { event: { type: 'section_generated', section: section2, index: 1 }, delay: 1200 },
  { event: { type: 'section_generated', section: section3, index: 2 }, delay: 1400 },
  { event: { type: 'section_generated', section: section4, index: 3 }, delay: 1100 },
  { event: { type: 'section_generated', section: section5, index: 4 }, delay: 1300 },
  { event: { type: 'section_generated', section: section6, index: 5 }, delay: 1200 },
  { event: { type: 'agent_complete', agent: 'guide_generator', duration_ms: 7700 }, delay: 200 },
  { event: { type: 'agent_start', agent: 'quality_evaluator', message: 'Evaluating guide quality...' }, delay: 200 },
  { event: { type: 'section_evaluated', evaluation: sectionEvaluations[0], index: 0 }, delay: 800 },
  { event: { type: 'section_evaluated', evaluation: sectionEvaluations[1], index: 1 }, delay: 600 },
  { event: { type: 'section_evaluated', evaluation: sectionEvaluations[2], index: 2 }, delay: 700 },
  { event: { type: 'section_evaluated', evaluation: sectionEvaluations[3], index: 3 }, delay: 600 },
  { event: { type: 'section_evaluated', evaluation: sectionEvaluations[4], index: 4 }, delay: 650 },
  { event: { type: 'section_evaluated', evaluation: sectionEvaluations[5], index: 5 }, delay: 700 },
  { event: { type: 'agent_complete', agent: 'quality_evaluator', duration_ms: 4050 }, delay: 200 },
  { event: { type: 'guide_complete', guide: null as unknown as GuideResponse }, delay: 300 },
];

// Patch the guide_complete event with the full mock guide (avoids circular ref at top level)
mockSSESequence[mockSSESequence.length - 1].event = { type: 'guide_complete', guide: mockGuide };
