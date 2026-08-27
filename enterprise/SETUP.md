# Fortified Enterprise Fleet - Setup Guide

Everything below uses genuinely free Google Cloud/Firebase tiers that do
**not** require a billing account or credit card. This is a deliberate
scoping decision: Cloud Run needs billing, so it isn't used here - instead
the enterprise requirements are met with services that are free without a
card, which is honest about what was actually deployed versus what's
documented as a future step.

## What's real infrastructure vs. our own pattern implementation

| Requirement | Implementation | Real GCP service? |
|---|---|---|
| Agent Registry | `enterprise/registry/` | Yes - Firestore |
| Memory Bank | `enterprise/memory/` | Yes - Firestore |
| Agent Identity | IAM service accounts (see below) | Yes - Cloud IAM |
| Agent Gateway | `enterprise/gateway/` | No - our own routing/policy layer |
| Model Armor | `enterprise/guardrail/` | No - our own guardrail layer |
| Agent Observability | `enterprise/observability/` | Partial - OpenTelemetry spans, console-exported; Cloud Trace export requires billing |

The Gateway and Guardrail modules implement the *pattern* Google's managed
products (API Gateway, Model Armor) provide. In a funded production
deployment, their internal logic is what you'd port into a Model Armor
policy or an API Gateway config instead of hand-rolling.

## 1. Firestore (Agent Registry + Memory Bank)

1. Go to **console.firebase.google.com** → sign in with any Google account
2. **Add project** → give it a name (e.g. `manrova`) → you can skip Google
   Analytics for this project → **Create project** (no card requested)
3. In the left sidebar, click **Build → Firestore Database** → **Create
   database** → choose **Start in production mode** → pick a region (e.g.
   `us-central1`) → **Enable**
4. You're now on the **Spark plan** (free) automatically - Firestore's
   free daily quota is generous (50k reads, 20k writes, 1 GiB storage) and
   nothing here will get close to it

### Get a service account key (for Vercel and local use)

1. In the Firebase console: gear icon → **Project settings** → **Service
   accounts** tab
2. Click **Generate new private key** → confirm → a JSON file downloads
3. Open that file, copy its **entire contents**

### Wire it into Vercel

1. Vercel dashboard → your project → **Settings → Environment Variables**
2. Add a new variable:
   - Name: `FIRESTORE_CREDENTIALS_JSON`
   - Value: paste the entire JSON file contents (all of it, including the
     curly braces)
3. Redeploy (Vercel → Deployments → "..." on the latest → Redeploy)

### Seed the Agent Registry

Once `FIRESTORE_CREDENTIALS_JSON` is set locally too (export it in your
Codespace terminal the same way), run:

```bash
export FIRESTORE_CREDENTIALS_JSON="$(cat path/to/your-key.json)"
python -m enterprise.registry.seed_registry
```

This publishes Manrova's five agents (four specialists + the Officer of
the Watch) to Firestore with version and permission metadata. Confirm it
worked by checking the Firestore console - you should see a
`manrova_agent_registry` collection with 5 documents.

### Verify the Memory Bank is writing

Click **Launch Investigation** on the live site a couple of times, then
check the Firestore console for a `manrova_incidents` collection - each
run should add a new document.

## 2. Agent Identity (IAM service accounts)

IAM itself is free - only *running* compute (Cloud Run, GKE, etc.) needs
billing. This lets us set up genuine least-privilege identities per agent
without a card.

1. In the same GCP project (Firebase projects are GCP projects), go to
   **console.cloud.google.com/iam-admin/serviceaccounts**
2. **Create Service Account** for each of the five agents, e.g.
   `nav-integrity-agent@<project-id>.iam.gserviceaccount.com`
3. Grant each one only the roles it actually needs - for the four
   specialists, this typically means no Firestore write access (they
   report evidence, they don't persist it); the Officer of the Watch
   service account gets `Cloud Datastore User` (Firestore read/write) since
   it's the one writing to the Memory Bank
4. This mirrors the zero-trust identity model the track asks for: each
   agent has its own credentials and can be individually revoked or
   audited, rather than one shared key for everything

## 3. What's still a scoped-down / future step

- **Cloud Run deployment**: not done, requires billing. The live Vercel
  site plus this Firestore/IAM setup is the honest substitute - the demo
  video should say this plainly rather than imply full Cloud Run
  deployment happened.
- **Cloud Trace export**: the Observability module is OpenTelemetry-ready
  (`enterprise/observability/observability.py`) and will export real spans
  to Cloud Trace the moment `OTEL_EXPORTER_OTLP_ENDPOINT` points at a
  billing-enabled project - right now it logs to console only.
- **Model Armor / API Gateway (managed products)**: our own
  implementations exist and are wired into the live investigation flow;
  swapping in the real Google-managed products is a config change, not a
  logic change, once billing is available.
