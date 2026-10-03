# Security Policy

## Reporting a vulnerability

Do not publish credentials, exploit details or security-sensitive bugs in a public
issue, discussion or pull request. This repository does not currently advertise
a private reporting channel; GitHub private vulnerability reporting was verified
disabled on 2026-10-03. If no private route is available, open an issue containing
only a request for a private security contact, with no vulnerability details.
Wait for the maintainer to provide a channel before sharing sensitive information.
No email address, formal CVE program or response SLA is promised here.

## Secrets

Never commit `.env`, real `GROQ_API_KEY`, `GROQ_API_KEY_FALL_BACK` or
`LOCAL_WORKSPACE_TOKEN` values. Browser-exposed `VITE_*` settings must contain no
secrets. Workspace tokens are dedicated credentials held only in browser memory;
disconnect/reload forgets them. Never reuse a provider credential as a workspace
token. Revoke/rotate an exposed credential with its issuer before reporting it;
do not paste the old value into the report.

## Supported scope

The current `main` branch is the supported scope. Public API routes are not an
authentication boundary; CORS and rate limits do not make them private. Local
workspace capabilities require explicit local mode, loopback peer, exact allowed
Host/Origin and bearer checks. Execution is a separate opt-in capability.
See [architecture](ARCHITECTURE.md) and [setup](README.md#local-setup).
