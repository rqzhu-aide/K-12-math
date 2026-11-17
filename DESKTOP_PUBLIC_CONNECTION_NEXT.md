# Next step: connect the desktop services to the website

Prepared November 16, 2026. The public website is https://math-practice.ailleo.net/.

## First, prepare the DNS change for the owner to review

The owner wants the existing Squarespace website to stay. Prepare a Cloudflare DNS migration, but **do not switch nameservers until the owner approves the concrete record list**.

Cloudflare's normal free setup requires Cloudflare to manage DNS for `ailleo.net`. This does not require transferring the domain registration or moving the Squarespace website. The owner can continue renewing the domain through Squarespace.

1. Export the existing Squarespace DNS records and current nameservers. Verify all records against the Cloudflare import; do not assume the automatic scan found everything.
2. Preserve the apex and `www` Squarespace records, domain-verification records, all email records, and `math-practice` pointing to `rqzhu-aide.github.io`. Keep existing website records DNS-only for this migration.
3. Give the owner the existing-to-proposed record comparison, Cloudflare-assigned nameservers, DNSSEC handling, and rollback instructions. State which manual step they will perform in Squarespace.
4. After approval and the nameserver change, check the Squarespace homepage, `www`, Math Practice HTTPS, and any email configuration from outside the home network.

If the owner wants to keep Squarespace DNS, explain the alternative before purchasing anything: Cloudflare's partial CNAME setup requires Business or Enterprise. A different domain already using Cloudflare DNS could also host the API; the API hostname need not share the website's domain.

Official references: [Cloudflare full setup](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/), [partial setup](https://developers.cloudflare.com/dns/zone-setups/partial-setup/), and [Squarespace with Cloudflare](https://support.squarespace.com/hc/en-us/articles/213469948-Using-Cloudflare-with-Squarespace).

## Then publish and verify the API gateway

- Prefer `api.ailleo.net`, if unused. This avoids the extra certificate setup needed for the earlier proposal, `api.math-practice.ailleo.net`: Cloudflare's free Universal SSL on a full DNS setup covers the root and first-level subdomains. Confirm HTTPS before reporting the gateway ready. See [certificate coverage](https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/).
- Use a named Cloudflare Tunnel to the gateway on `127.0.0.1:8878`. Keep speech/D3 ports private. No router port forwarding.
- Allow the exact browser origin `https://math-practice.ailleo.net`, including CORS headers on errors and preflight requests.
- Keep anonymous free access for website visitors. Configure server-validated Turnstile and rate limits. Visitors should not need Tailscale, an invitation, or a Cloudflare Access account.
- Keep transcript/result collection OFF for the initial connection. Raw audio must never be retained. Finish the retention/deletion and eligibility requirements before enabling model-improvement collection.
- Test a synthetic recording and D3 request through the public HTTPS address from outside the desktop network. Check restart/reboot recovery.

## Return this information to the frontend programmer

1. Confirmed HTTPS API base URL and the deployed gateway revision.
2. Public Turnstile site key, expected action, and whether token renewal requires another challenge. Keep the secret key and tunnel token on the desktop.
3. Exact session, consent, transcription, D3, and health routes, including whether health routes require a bearer token. Include sanitized request/response fixtures and error codes.
4. The accepted consent notice version and question-bank release identifiers.
5. Confirmed D3 rubric mapping and whether displayed question text/choices reach the model. Resolve the discrepancy described in the detailed handoff.
6. Evidence of the external browser tests and confirmation that collection is OFF and raw audio is cleaned up.

The complete API contract and acceptance requirements are in [DESKTOP_SERVICES_CONNECT.md](DESKTOP_SERVICES_CONNECT.md).

## Frontend status

The settings update adds a processing acknowledgement and separate speech/D3 choices. Choices can be saved while the server is unavailable; this does not make the services operational. Processing permission and model-improvement retention remain separate. The frontend sends `collection: false`.

The browser adapter uses `window.MATH_PRACTICE_HOSTED.services`. Public URL, challenge integration, accepted notice/release metadata, and real gateway behavior still need verification before activating it. A health response alone is not a successful transcription or D3 inference test.
