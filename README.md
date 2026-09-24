# Nostr Command Interface

Self-hosted Nostr identity & DVM manager with Lightning payment gating via NWC — a reference implementation for paid NIP-90 AI jobs.

Run and manage multiple Nostr bot identities, post and reply, and operate a Data Vending Machine (DVM) that accepts NIP-90 job requests, charges a real Lightning invoice for the work, and only runs (and gets paid for) the job once that invoice is settled.

## Features

- **Multi-identity manager** — create and run several Nostr bot keypairs from one interface (compose, reply, feed, mentions)
- **DVM Hub** — scans relays for NIP-90 job requests (kind 5050 text-synthesis jobs) and can process them automatically
- **Payment-gated jobs** — quotes a job from its bid/amount tags, generates a Lightning invoice, and requires settlement before running the job or publishing a result
- **Wallet tab** — connect a personal Lightning wallet via Nostr Wallet Connect (NWC) to check balance and generate invoices directly, independent of the job-payment flow
- **Autopilot** — configurable automated behavior for bot accounts
- **Relay management, event log, history, and themeable UI** — all persisted locally in the browser

## How a paid job works

1. A NIP-90 job request (kind 5050) arrives on a watched relay
2. The app reads the job's `bid`/`amount` tag to quote a price in sats
3. It requests a Lightning invoice from the local payment engine
4. It publishes a kind 7000 feedback event (`status: payment-required`) containing the invoice
5. It polls the payment engine until the invoice is settled (or times out)
6. Once paid, it runs the job through the configured LLM and publishes the result as a kind 6050 event



## Requirements

- A modern browser (Chrome, Firefox, or Edge — the app uses native ES modules and dynamic `import()`, so no build step or server is needed for the frontend)
- Python 3.9+ for the payment engine
- Accounts/keys, all free to create:
  - **[Coinos](https://coinos.io)** account + API token — used by the payment engine to generate and check DVM job invoices
  - **[Alby](https://getalby.com)** wallet + a Nostr Wallet Connect (NWC) connection string — used by the in-app Wallet tab for personal balance checks and invoice creation
  - A **Gemini API key** (from [Google AI Studio](https://aistudio.google.com)) — powers the LLM synthesis that answers DVM jobs

## Setup

### 1. Start the payment engine

```bash
pip install fastapi uvicorn httpx pydantic
python paymentengine.py
```

This starts the API on `http://127.0.0.1:5000` and must be left running while the app is in use. (You can also run it with `uvicorn paymentengine:app --host 127.0.0.1 --port 5000` directly.)

### 2. Open the app

Just open `index.html` in your browser — there's nothing to build or install for the frontend itself.

### 3. First-run configuration

- **LLM API key**: enter your Gemini key under the API settings panel and click **Secure API Key**.
- **Lightning wallet (optional, for the Wallet tab)**: open the **Wallet** tab, paste your `nostr+walletconnect://...` connection string, and click **Save Connection**, then **Test / Connect**.
- **Coinos token (for DVM job payments)**: the app will prompt for this automatically the first time it needs to generate a job invoice, and remembers it after that.

## Security notes

This is designed for personal, single-user, self-hosted use — not multi-tenant deployment:

- API keys and wallet connection strings are stored **unencrypted** in the browser's local storage.
- The payment engine binds to `127.0.0.1` only, so it isn't reachable from your network by default. Don't expose it publicly without adding authentication.
- A Nostr Wallet Connect string grants real wallet access. Only use one on a device you trust, and scope its permissions in Alby to just what this app needs (`get_balance`, `make_invoice`).

## Roadmap

ANostr Command Interface & DVM Infrastructure Roadmap
Phase 1: Core Protocol & DVM Integration (Months 1–2)
NIP-90 & NWC Standard Compliance: Solidify native Data Vending Machine (NIP-90) job request/response handlers with Nostr Wallet Connect (NWC) for automated payload settlement and micro-payments.

Autonomous Telemetry & Event Ingestion: Expand real-time relay telemetry parsing (network event tracking, relay topology monitoring, and status feedback) into structured DVM inputs.

Persona Engine Refinement: Harden local LLM provider integration (Gemini/Claude) with structured prompt-injection middleware for consistent, deterministic persona execution across network feeds.

Open Source Release & Documentation: License core repo under MIT/Apache-2.0, publish standard setup guides, and document DVM job-kind handling for public contributors.

Phase 2: Client Optimization & Multi-Platform Deployment (Months 3–4)
Offline-First State & Storage: Implement local event caching and persistent state indexed DB storage to eliminate latency during high-volume relay polling.

Desktop & PWA Native Packaging: Bundle client application via Electron and standalone PWA manifests for cross-platform desktop execution (Linux, macOS, Windows, ChromeOS).

Multi-Relay Fallback Architecture: Build automatic relay failover, reconnection backoffs, and NWC connection pooling to preserve uptime during network partitions.

Developer Tooling & CLI Utilities: Release standalone terminal/headless runners for autonomous DVM node operators.

Phase 3: Network Hardening & Ecosystem Scaling (Months 5–6)
Encrypted Event & File Payload Workflows: Integrate NIP-44/NIP-94 compliant payload handling for secure file sharing and end-to-end encrypted DVM job dispatch.

DVM Marketplace & Dynamic Task Routing: Enable dynamic task discovery where client nodes automatically broadcast, discover, and bid on active DVM jobs across open relays.

Community Security Audits & Benchmarking: Conduct public stress testing on persona context pipelines and publish performance benchmarks for DVM job completion.

Public Documentation & Educational Content: Produce comprehensive developer tutorials, API specs, and integration guides to onboard third-party DVM service providers.

## Protocols

- [NIP-90](https://github.com/nostr-protocol/nips/blob/master/90.md) — Data Vending Machines
- [NIP-47](https://github.com/nostr-protocol/nips/blob/master/47.md) — Nostr Wallet Connect

## License

MIT — see [LICENSE](LICENSE).
