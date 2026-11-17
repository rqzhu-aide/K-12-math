# Next step: connect the desktop services to the website

Updated November 17, 2026 after publishing the service connection and testing real browser inference. The public website is https://math-practice.ailleo.net/.

## Next change: prepare recommendation-model collection

The owner now requests preparation for collection. Approved scope: speech transcripts, decision model results, and related question metadata, used to train and improve Ailleo's internal question recommendation model. Retain for **up to 90 days (about 3 months)**. Deletion/privacy contact: **rqzhu-aide@qq.com**. Never retain raw audio. The public interface calls the service **Decision model**; D3 remains an internal implementation name.

The prepared website release, `simpler-service-consent-2026-11-17`, uses one explicit **Agree and enable** action per feature. This permits processing only. Its revised EN/CN agreement and settings notice disclose the planned recommendation use, retention, and contact, while clearly stating that collection is not yet enabled. Accepting that agreement or enabling a feature is not advance consent to future collection.

The desktop programmer should complete these steps before a coordinated collection release:

1. Implement and test enforced `collection.retention_days: 90`, covering active records, spool/archive, derived indexes and backups. Expired/deleted records must not reappear when rebuilding indexes.
2. Implement deletion requests through the supplied email. Provide a workable way for an anonymous user to identify and establish control of their records after a session expires; an exposed session ID alone is not proof. An operator-run deletion procedure is sufficient if tested.
3. Allow collection only with the operator switch ON, the current notice, an explicit collection choice, valid retention, and participant eligibility. Preserve processing when collection is declined. Resolve the eligibility and applicable parent/guardian consent procedure before collecting children's data; the existing supervision checkbox is only an acknowledgement.
4. Return the updated contract and source/tests. Coordinate a new service notice version with the frontend. The current gateway expects **2026-11-16**; do not change only one side. The general agreement has its own new version, **2026-11-17.1**.
5. In the coordinated frontend update, add a separate collection choice defaulting to off. Send that choice with consent, validate `effective_collection`, and validate inference `recorded`/`record_id` against that effective state. Current production deliberately sends `collection: false` and rejects retained inference replies. Merely switching the backend on or changing one boolean is insufficient.
6. Verify opt-out still permits speech/decision processing, operator OFF never retains content even after a user opt-in, eligibility/current consent are enforced, raw audio is removed on success/failure, 90-day expiry works, and an authorized deletion removes all affected copies. Keep tutor requests, credentials, and provider history outside the dataset.

The 0.3.0 archive has only historical collection shapes; status v3 says expiry and authorized deletion were not implemented, and public report 0.4.3 still reports collection OFF. Return current implementation evidence before enabling it. No backend switch was changed by this website preparation.

Consent should describe each purpose clearly and use a deliberate choice; see [ICO consent guidance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/consent/how-should-we-obtain-record-and-manage-consent/). The children's eligibility/parental-consent step follows the applicable requirements described in the [FTC COPPA guidance](https://www.ftc.gov/business-guidance/resources/complying-coppa-frequently-asked-questions), not a claim that this checkbox-based app already meets them.

## Public API: website connected, protected browser flow passed

The API at `https://api.ailleo.net` is now published. On November 17, direct HTTPS requests with certificate validation confirmed gateway 0.4.3, the expected public Turnstile site key with `enabled: true`, both upstream health checks available, browser preflight returning 204 with the exact allowed origin, and a session request without a challenge returning `403 turnstile_required`. The checks used a current Cloudflare IP because this computer's normal hostname lookup was still failing; both authoritative nameservers and public resolvers returned the new API address.

The frontend is now deployed at Pages commit `c1fbac6b6d495d51e44a66c66db5eaf89eeecc52`, release `owner-services-2026-11-17`. At 2026-11-17 06:57 UTC, a fresh Chrome profile successfully exercised processing opt-in, both health checks, recording synthetic speech, real Turnstile verification, session issuance, consent, transcription, D3 display, and session renewal with a second fresh challenge. Both consent replies confirmed `effective_collection: false`; all inference replies returned `recorded: false` and `record_id: null`. No personal voice, student input, tutor key, or tutor request was used. The recording came from a generated WAV through Chrome's synthetic microphone. The agreement was preaccepted as a test fixture; service processing acknowledgement was exercised through settings.

The client's renewal threshold was advanced for the test instead of waiting two hours. The server still received a valid bearer and a fresh real Turnstile token. Turnstile was never disabled or mocked. Afterward `/api/config` still reported it enabled and a request without a challenge still returned `403 turnstile_required`.

This computer's ordinary DNS lookup remains intermittent and also failed after flushing its temporary cache. Public resolvers return the current address. The successful browser run used a process-local mapping of `api.ailleo.net` to verified Cloudflare address `104.21.12.205`, preserving the real hostname, HTTPS certificate validation, and all server protections. This proves the application and protected inference flow, not DNS propagation for every visitor. No system DNS settings or domain records were changed. Recheck ordinary visitor access after migration propagation. Reboot recovery and desktop filesystem retention remain outside this browser test.

Local test evidence: `.local/public-services-20261117/browser-evidence.json`, `browser-ui.json`, `transcription-d3-success.png`, and `turnstile-live.png`. These contain synthetic data and no bearer/challenge tokens. Earlier failed test runs are retained separately. Focused checks passed: 54 JavaScript tests and 8 export tests.

The report mentions that a private widget secret was shared in chat. If this was an actual secret rather than the public site key, rotate it privately in Cloudflare and update the desktop secret file before the final browser test. The public site key in this document is intended to be shared.

Use the desktop report's later DNSSEC checkpoint: **November 18, 2026 at 23:51 America/Chicago**, followed by successful propagation and website checks. Frontend API, widget, and release metadata are now configured. Production bank releases are `amc-c0f86768d5bda9d1` and `cn-math-17ca82e5a091f397`, derived from the exported question content.

## Current state: DNS has already moved

**Do not start the migration again.** The owner has already changed the nameservers. Domain registration and renewal remain with Squarespace. The owner clarified that there has never been an actual Squarespace website: apex and `www` are placeholders; Math Practice on GitHub Pages is the only website. No Squarespace site needs to be created or reconnected.

- At **2026-11-16 23:16 America/Chicago**, direct parent-zone checks observed `candy.ns.cloudflare.com` and `elliott.ns.cloudflare.com`, and no DS record on two `.net` servers.
- The eleven known record values below have been verified in Cloudflare/public DNS: four apex A records, apex HTTPS type 65, three CNAMEs, and three TXT records. The original HTTPS value was restored. Existing A/CNAME records are **DNS only**, with Auto TTL; keep them that way.
- The owner switched before waiting out the old DS cache. The previously measured DS TTL was 86400 seconds (24 hours), and parent delegation TTL was 172800 seconds (48 hours). Cached old records may still cause failures. Keep the current nameservers and **do not re-enable DNSSEC or publish Cloudflare's DS until at least 2026-11-18 23:51 America/Chicago**, then only after delegation, record, and website checks pass. This uses the later observation in the desktop report, not a claim of global propagation.
- Normal HTTPS requests from this machine returned HTTP 200: apex and `www` titled **Coming Soon**, and Math Practice titled **Math Practice**. The API's earlier NXDOMAIN state has been superseded by the public endpoint checks above.

The owner has created the Turnstile widget and supplied this **public site key**:

```text
0x4AAAAAAGEo8zkmtESutYxk
```

Backend status v3 reports fixes for Turnstile hostname/action binding, D3 question context, the consent fixture, and DNS verification. Its updated source package and reported tests have not been independently verified. The earlier findings below are historical, not instructions to repeat the cutover.

## Desktop deployment requirements and remaining verification

The public endpoint report says items 1 and 2 are now deployed. Preserve that setup; do not recreate the tunnel. Complete the secret check, remaining source handoff, and coordinated browser/recovery verification.

1. Preserve the deployed Turnstile configuration: `enabled: true`, the public site key above, `expected_hostname: math-practice.ailleo.net`, and `expected_action: math_practice_session`. Validate Siteverify success, hostname, and action. Both session issuance and renewal require a fresh challenge. Rotate the private secret if it was shared, as described above; never send it in the handoff or frontend configuration.
2. Preserve the deployed named Cloudflare Tunnel for **`api.ailleo.net`**, routed to `http://127.0.0.1:8878`, with a catch-all 404. Keep speech/D3 ports private, existing website records DNS-only, and router ports closed. The report records successful process recovery; recovery after a real desktop reboot remains to be verified.
3. Allow exactly `https://math-practice.ailleo.net`, including CORS on preflight and errors. Keep anonymous access with Turnstile and rate limits. Visitors should not need Tailscale or Cloudflare Access. Keep collection **OFF**, retain no raw audio, and keep tutor traffic and tutor credentials outside this gateway.
4. Return the revised source/configuration and sanitized fixtures for the v3 fixes, with deployed revision/image identity and reproducible test results. Confirm displayed question text and keyed choices reach D3 while reference answers and solutions do not.
5. The frontend browser issuance/renewal, consent, synthetic recording, transcription, and D3 checks now passed as recorded above. Remaining desktop verification is restart/reboot recovery and audio cleanup. Recheck ordinary DNS access after propagation. A browser response does not inspect files on the desktop.

The existing tunnel is named `math-practice-desktop`. Its published application route is `api.ailleo.net` with service URL `http://127.0.0.1:8878`. Keep its connector credential private. [Cloudflare's dashboard documentation](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/) is a maintenance reference, not a request to create another tunnel.

References: [Tunnel DNS routing](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/dns/), [Turnstile validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/), and [DNSSEC after propagation](https://developers.cloudflare.com/learning-paths/dns-best-practices/concepts/phase-4/).

## Historical source inventory

Received November 16, 2026 before the cutover. These eight screenshot records plus the three TXT records in the review below form the eleven-record baseline. Values have since been checked in Cloudflare/public DNS. The TTL column records the original Squarespace TTLs; Cloudflare currently uses Auto. The HTTPS record's service priority is part of its value below.

| Type | Name | Data | TTL |
| --- | --- | --- | --- |
| A | `@` | `198.185.159.144` | 4 hours (14400 seconds) |
| A | `@` | `198.185.159.145` | 4 hours (14400 seconds) |
| A | `@` | `198.49.23.144` | 4 hours (14400 seconds) |
| A | `@` | `198.49.23.145` | 4 hours (14400 seconds) |
| CNAME | `www` | `ext-sq.squarespace.com` | 4 hours (14400 seconds) |
| HTTPS | `@` | Full value below | 4 hours (14400 seconds) |
| CNAME | `_domainconnect` | `_domainconnect.domains.squarespace.com` | 1 hour (3600 seconds) |
| CNAME | `math-practice` | `rqzhu-aide.github.io` | 4 hours (14400 seconds) |

Complete HTTPS value, with visual line wrapping removed:

```text
1 . alpn="h2,http/1.1" ipv4hint="198.185.159.144,198.185.159.145,198.49.23.144,198.49.23.145"
```

Preserve the placeholder behavior at both apex and `www`, and Math Practice at its current hostname. The earlier concern about attachment to a Squarespace website no longer applies because the owner has confirmed there is no such website.

### Historical DNSSEC preparation

Before the cutover, the owner confirmed DNSSEC was enabled in Squarespace. The requested sequence was to remove the old parent DS, wait out its cache, change nameservers, then publish Cloudflare's new DS only after delegation propagation and website checks. The owner has since changed nameservers without the first wait. Follow the current-state timing above rather than repeating these preparation steps. Do not reuse the old provider's DS values.

References: [Cloudflare migration sequence](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/#33-turn-off-dnssec), [Cloudflare DNSSEC setup](https://developers.cloudflare.com/dns/dnssec/), and [Squarespace nameserver controls](https://support.squarespace.com/hc/en-us/articles/4404183898125-Review-change-or-reset-your-domain-s-nameservers).

## Historical review of DNS-MIGRATION-PLAN.md and gateway-0499a02669b3.tar.gz

Reviewed November 16, 2026 before the owner's cutover, by reading the supplied files and making read-only public DNS checks. The review itself changed no nameservers, records, DNSSEC settings, or services. Archive scripts and tests were not executed.

The overall architecture and the eight screenshot records match our requirements. Three additional TXT values in the plan were independently confirmed:

| Name | Type | Value |
| --- | --- | --- |
| `@` | TXT | `v=spf1 -all` |
| `_dmarc` | TXT | `v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s` |
| `_domainkey` | TXT | `v=DKIM1; p=` |

Together these give eleven known records to preserve. Public queries cannot prove a complete zone inventory; the full Squarespace panel remains the completeness check.

### Findings from the original review, before the cutover

1. **Add cache-expiry waits to plan section 6 and rollback section 10.** A DS record disappearing from the authoritative parent is necessary, but cached copies can still exist. Our authoritative measurements were DS TTL 86400 seconds (24 hours), parent nameserver delegation TTL 172800 seconds (48 hours), and child NS TTL 21600 seconds (6 hours). Re-measure before execution. With those values, wait at least 24 hours after confirmed parent DS removal before switching nameservers. After confirmed parent delegation replacement, allow the old 48-hour delegation cache window to expire before publishing Cloudflare's DS, with website checks throughout. For rollback after Cloudflare DNSSEC was enabled, remove its DS, keep Cloudflare signing and serving while the old DS cache expires, then revert nameservers; keep both DNS services available through delegation propagation. Remove claims that failures are impossible between steps C and F.
2. **Repair the DNS verification script before relying on its go-ahead.** In archive `scripts/dns-baseline.sh`, `q()` suppresses errors; `dnssec()` and `preflight()` treat empty output as no DS. A timeout or SERVFAIL must stop the check, not approve migration. The script currently queries recursive `1.1.1.1` while labeling its result as authoritative parent state. Query the parent directly, preserve DNS response status and TTL, and track the removal/wait timestamps. Add focused checks for lookup failure, old DS present, confirmed removal with unexpired cache time, and the fully elapsed condition.
3. **Regenerate a correct baseline.** `q()` filters answer type but not the answer's owner name. The bundled baseline therefore incorrectly places GitHub/Squarespace targets' A, AAAA, CAA, and TXT records under the aliases queried. Filter by both owner name and type and preserve TTL evidence. Do not import these target records as additional zone records. `compare` currently exits successfully after differences; return a failure for unexpected differences and distinguish the planned NS/SOA changes. The eleven-row inventory in the plan is more accurate than its raw baseline file.
4. **Squarespace site attachment: no longer applicable.** This finding assumed an existing Squarespace website. The owner subsequently confirmed there has never been one. Preserve the apex and `www` placeholders; do not request a site reconnection or create a new site.

Sources: [Cloudflare DS cache waiting guidance](https://developers.cloudflare.com/learning-paths/dns-best-practices/concepts/phase-2/), [DNSSEC reactivation after nameserver propagation](https://developers.cloudflare.com/learning-paths/dns-best-practices/concepts/phase-4/), [Squarespace effects of custom nameservers](https://support.squarespace.com/hc/en-us/articles/4404183898125-Review-change-or-reset-your-domain-s-nameservers).

### Gateway readiness reported in v3

The original archive supplies the status, anonymous session, consent, WAV transcription, and D3 response formats used for integration. The deployed protected browser path has now passed. The revised backend source package still needs independent verification; this does not change the live-flow result. Historical source findings are in [DESKTOP_SERVICES_CONNECT.md](DESKTOP_SERVICES_CONNECT.md).

## Historical handoff checklist

The API, widget, routes, notice, production release metadata, and protected browser evidence are now available. Keep this checklist for future backend changes; remaining source and desktop retention/recovery evidence are noted above.

1. Confirmed HTTPS API base URL and the deployed gateway revision.
2. Confirmation that the supplied public Turnstile site key is deployed with action `math_practice_session`, and fresh challenges work for both issuance and renewal. Keep the secret key and tunnel token on the desktop.
3. Exact session, consent, transcription, D3, and health routes, including whether health routes require a bearer token. Include sanitized request/response fixtures and error codes.
4. The accepted consent notice version. Coordinate question-bank release identifiers with the frontend programmer; they are not information the owner must supply. Current bank IDs are `amc` and `cn-math`; choices are keyed objects, such as `{"A":"...","B":"..."}`. `amc-2026.1` remains an illustrative release, not an assigned production value.
5. Confirmed D3 rubric mapping and whether displayed question text/choices reach the model. Resolve the discrepancy described in the detailed handoff.
6. Evidence of the external browser tests and confirmation that collection is OFF and raw audio is cleaned up.

The complete API contract and acceptance requirements are in [DESKTOP_SERVICES_CONNECT.md](DESKTOP_SERVICES_CONNECT.md).

## Frontend status

The settings update adds a processing acknowledgement and separate speech/D3 choices. Choices can be saved while the server is unavailable; this does not make the services operational. Processing permission and model-improvement retention remain separate. The frontend sends `collection: false`.

The browser adapter uses `window.MATH_PRACTICE_HOSTED.services`. The public API and lazy Turnstile widget are published with notice version `2026-11-16`; fresh renewal challenges are required. Each learner must acknowledge processing and separately enable speech and/or D3 in Model settings. Opening or saving settings does not issue a session or upload content. The real browser test verified both features and collection OFF. Own-provider math tutoring remains separate.
