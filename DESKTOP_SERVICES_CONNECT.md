# Connect Ailleo speech-to-text and D3 to the public website

Updated 2026-11-17 for the desktop programmer. The website is connected and the protected browser flow passed with real Turnstile, synthetic speech, D3, and fresh-challenge renewal. Collection remains OFF. Follow [the current handoff](DESKTOP_PUBLIC_CONNECTION_NEXT.md) for evidence, the temporary DNS mapping used in the successful test, remaining DNS propagation checks, and DNSSEC timing. The revised backend source/tests have not been independently inspected. Do not repeat the migration or recreate the working tunnel.

## What the website needs

The public frontend is **https://math-practice.ailleo.net/** on GitHub Pages. The owner has never had an actual Squarespace website: apex **https://ailleo.net/** and `www` are placeholders. Preserve their existing behavior; no Squarespace site needs to be created or reconnected. Domain registration remains with Squarespace.

The desktop supplies only these optional, free services:

- Speech-to-text: audio becomes a transcript the learner can review and edit.
- D3: the original transcript is assessed for confidence, reasoning clarity, and engagement. These are model observations, not a mathematics grade or a psychological diagnosis.

The math tutor is separate. The current website connects directly to the learner's own API provider using their URL, API key, and model. ChatGPT account sign-in is marked **Forthcoming** and is unavailable online in this release. **Do not add a tutor proxy to the operator gateway. Do not receive or store tutor API keys, account tokens, tutor prompts, or tutor replies.**

```text
Browser at math-practice.ailleo.net
  |
  +-- Math tutor --> learner's own API provider
  |
  +-- Optional speech / D3 --> public HTTPS API hostname
                               --> Cloudflare Tunnel
                               --> gateway on desktop, localhost:8878
                                    +-- speech, localhost:9934
                                    +-- D3, localhost:9951
```

The settings now provide a processing acknowledgement and separate speech/D3 choices. They show **Waiting for server connection** until the public gateway and challenge integration are configured. The browser adapter is implemented against the v2 fixtures, but real public inference remains unverified. Adding a DNS record alone will not activate the services.

## 1. Publish the gateway, preserving the current websites

Published API hostname: **api.ailleo.net**, gateway 0.4.3. HTTPS, public configuration, both health responses, browser preflight, missing-challenge rejection, and real protected browser inference have been independently checked. Preserve the deployed route and keep Turnstile enabled. The live browser test and its DNS qualification are recorded in the current handoff. See [Cloudflare certificate coverage](https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/).

1. Run a named Cloudflare Tunnel on the always-on desktop. Route only the chosen API hostname to `http://127.0.0.1:8878`, with a final catch-all 404 route. Keep the raw model ports private. No router port forwarding is needed for this tunnel design.
2. Add the API tunnel route in the existing Cloudflare-managed `ailleo.net` zone. The parent already delegates to `candy.ns.cloudflare.com` and `elliott.ns.cloudflare.com`; do not change nameservers again. Preserve the eleven verified existing record values in the next-step handoff and respect its DNSSEC waiting window.
3. Keep the existing apex, `www`, domain-connect, and GitHub Pages records DNS-only while retaining their current HTTPS behavior. The new API route uses Cloudflare Tunnel. Do not change the frontend hostname or send placeholder/site traffic through the gateway.
4. Make the connector and gateway restart automatically after failure and reboot. Verify this with an actual restart and reboot test.
5. Test the API from a device outside the desktop's network and outside Tailscale. Website visitors must not need Tailscale, a Cloudflare Access login, an invitation, or an account.

Reference: [Cloudflare Tunnel DNS records](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/dns/).

## 2. Browser access and anonymous sessions

Allow the exact frontend origin `https://math-practice.ailleo.net`. Do not use `*` or merely match any hostname ending in `ailleo.net`.

Support browser preflight (`OPTIONS`) for the public routes, `GET`/`POST`, `Authorization`, and `Content-Type`. Return matching CORS headers on errors as well as success, and `Vary: Origin`. The frontend uses bearer tokens with `credentials: omit`, so cookies are unnecessary. Session, consent, transcript, and D3 responses should use `Cache-Control: no-store`.

Keep the v2 anonymous session contract:

```http
POST /api/session
Content-Type: application/json
```

```json
{"turnstile_token":"<fresh challenge token>"}
```

`turnstile_token` is the public-deployment addition to v2's empty-body issuance. Return the existing opaque `token`, `session_id`, `scopes`, `issued_at`, `expires_at`, and `renew_after_seconds`. Accept the current bearer token for renewal; both issuance and renewal require a fresh challenge. The frontend will serialize renewal so concurrent requests do not race token rotation. Never put a token in a URL or log.

The owner has supplied public site key `0x4AAAAAAGEo8zkmtESutYxk`, and the public endpoint now reports Turnstile enabled with that key. Keep its secret private on the desktop. For issuance and renewal, validate Siteverify `success`, hostname `math-practice.ailleo.net`, and action `math_practice_session`. V3 reports this binding is implemented; verify the revised source and real widget flow. Invalid, missing, expired, or replayed challenges must not issue a session. Publish stable error codes for these cases. Never send the secret key to the frontend or include it in the handoff.

Keep rate limits on issuance and service use, plus an overall model concurrency/queue limit. Return `429` with `Retry-After`; bound the queue and request duration. Trust forwarded client IP headers only from the tunnel connector. CORS and Turnstile reduce misuse; they do not prove a person's identity or guarantee that all callers use the UI.

Reference: [Turnstile server-side validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/).

## 3. Keep processing permission separate from retention

Preserve `POST /api/consent` for independent `transcription` and `d3` permissions and the processing `notice_version`. The browser sends `collection: false` and the server returns `effective_collection: false` on this route. Declining sharing still allows permitted processing.

Keep the operator collection switch **OFF**. The proposed submission routes and separate opt-in are documented in the [current collection handoff](DESKTOP_PUBLIC_CONNECTION_NEXT.md#next-change-prepare-optional-sharing-of-submitted-thinking).

Audio, original transcripts, and D3 inputs and results are processing-only, even after submission sharing is enabled. Verify cleanup on success, failure, timeout, cancellation, and worker restart, including gateway and upstream temporary files and logs.

## 4. Finish and share the exact API contract

Send an OpenAPI document or equivalent complete request/response fixtures. Include the source revision, deployed image digest, sanitized configuration example, and tests. Do not send credentials, real learner records, or raw recordings.

| Route | Required behavior |
| --- | --- |
| `POST /api/session` | Anonymous issuance and renewal, including Turnstile policy |
| `POST /api/consent` | Independent speech and D3 processing choices. Validate the processing notice and keep collection off. |
| `GET /api/status/speech` | Proposed frontend status route; confirm or supply the existing exact route |
| `GET /api/status/decision` | Proposed D3 status route; confirm or supply the existing exact route |
| `POST /api/transcription` | Raw WAV plus question metadata, bearer token and processing permission |
| `POST /api/learning-signals` | Original transcript plus question context, bearer token and D3 permission |

Status may retain `{ "available": true, "checked": "upstream-health", "model": "..." }`. Document whether status requires a session. The UI will distinguish upstream health from a successful inference test.

### Transcription

The existing recorder already produces one mono, 16 kHz, 16-bit PCM WAV, at most 60 seconds. Accept it as `Content-Type: audio/wav`; no WebM conversion or browser chunking is needed.

Use `question_id`, `bank`, and `release` query metadata. Real frontend IDs use values such as `question_id=1989_AMC_8_Q02` and `bank=amc`; do not require the illustrative `amc8-1989-p02` / `amc8` strings in the v2 report. Agree on one explicit release identifier; it is not necessarily the contest year.

Preserve the v2 response fields `text`, `text_chars`, `latency_ms`, `chunks`, `session_id`, `question_id`, `recorded`, and `record_id`. Always return `recorded: false` and `record_id: null`. Do not log audio bodies or transcript text.

### D3

The frontend will send the original transcript, not the learner's later edited reasoning:

```json
{
  "transcript": "<original speech transcript>",
  "question": {
    "id": "1989_AMC_8_Q02",
    "bank": "amc",
    "release": "<agreed bank release>",
    "text": "<displayed problem>",
    "choices": {"A": "<choice text>", "B": "<choice text>"}
  },
  "site_release": "<frontend build identifier>"
}
```

Confirm support for a keyed choices object. This preserves the actual choice labels; the v2 report used an illustrative array. Open-response questions use `{}`.

**Verify the reported context correction:** the existing local D3 implementation includes the displayed question and choices as context, while excluding the reference answer and solution. V2 omitted the question and choices; v3 reports that they have been restored with keyed choices. Check the revised source/tests and a representative request before integration. Do not send reference answers or solutions upstream to D3.

Preserve the canonical rubrics from `student_assessment.py`: confidence has 3 choices, reasoning has 4, engagement has 3. Return `question_id`, the exact analyzed `transcript`, `rubric_version`, `answers`, full letter-to-code/label `rubrics`, timing, session ID, `recorded: false`, and `record_id: null`. Validate complete, finite probabilities in range with the documented normalization tolerance. The frontend will display the probability of the selected choice; it must not mistake an upstream margin named `confidence` for that probability.

For every non-2xx response, retain:

```json
{"error":{"code":"consent_required","message":"<safe explanation>"},"request_id":"<identifier>"}
```

Document all existing v2 error codes plus the new challenge errors. Never return traceback, tokens, upstream authorization headers, or raw request bodies.

## 5. Frontend work after your handoff

The frontend programmer will:

1. Completed: the hosted build connects to `https://api.ailleo.net` and loads Turnstile only when a consented request needs verification. The public site key is published; the private secret remains on the desktop.
2. Verify the implemented EN/CN notice, processing choices, session issuance/renewal, and error recovery against the deployed gateway. Keep collection off initially.
3. Verify the deployed speech and D3 paths. Verify the proposed submission routes against the current handoff before enabling sharing. Tutor traffic and credentials must stay on the learner's independent connection.
4. Verify the implemented status/rubric adapter and recorder against real responses, including stale results after question or transcript changes.
5. Enable the services only after the real browser tests below pass.

## Completion evidence to return

- Public API base URL and exact allowed frontend origin.
- Turnstile public site key, action, issuance/renewal policy, and error fixtures. No secret key.
- Complete API fixtures, canonical rubric version, notice version, and collection-off status.
- Source revision, image digest, startup instructions, and reproducible contract test command/results.
- An external-browser run from `https://math-practice.ailleo.net`: preflight, session, consent, one synthetic WAV transcript, one D3 result, and token renewal.
- Failures exercised: wrong origin, invalid/reused challenge, expired token, no consent, oversized/invalid WAV, upstream outage, rate limit, timeout, and restart.
- Evidence that no raw audio was retained and no tutor request reached this gateway.
- Confirmation that `ailleo.net`, `www.ailleo.net`, and `math-practice.ailleo.net` still work after DNS changes.

Use synthetic data for these checks. Local curl/model tests are useful, but public readiness requires the actual website-to-gateway browser path.

## Historical review of gateway-0499a02669b3.tar.gz

Read-only review on November 16, 2026. The source declares gateway version 0.3.0, while parts of README still describe older versions. Treat the archive as implementation evidence, not proof of the current deployed image or configuration. No archive scripts or tests were executed during this review.

Confirmed from source and fixtures: `/api/status/speech` and `/api/status/decision` are unauthenticated health routes; bearer session issuance/renewal fields match the browser adapter; the consent and processing responses support collection OFF; raw WAV and transcription fields match; the D3 response includes the canonical 3/4/3 rubric mapping. When Turnstile is enabled, both initial session issuance and renewal require a fresh challenge.

The following were findings in the original archive. V3 reports all three corrected; verify the revised package and deployment before public activation:

1. **Turnstile website/action binding.** `gateway.py:287-306` accepts Siteverify's `success` without checking the returned `hostname` or `action`. Require `math-practice.ailleo.net` and the agreed action, proposed `math_practice_session`, as already specified above. Test otherwise-successful tokens with the wrong hostname or action. Update the test verifier at `tests/test_gateway.py:563-566` to return those fields. Enable Turnstile in the actual public deployment; example configuration and `fixtures/01b-config.json` currently show it disabled with no site key. [Official validation guidance](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/).
2. **D3 question context.** `gateway.py:682-691` still omits the displayed question and choices from the D3 model state, and `tests/test_gateway.py:275-299` explicitly requires that omission. This is the behavior mismatch documented in section 4. Restore the displayed question and keyed choices while excluding reference answers/solutions, or present the behavior change for explicit review. Use a representative current frontend request, for example question ID `1989_AMC_8_Q02`, bank `amc`, and a keyed choice object, rather than only the old illustrative fixture.
3. **Correct the consent-error fixture.** `fixtures/08-error-consent-required.json` and its manifest entry actually contain HTTP 400 `bad_request` for a missing transcript. Regenerate a valid transcript request with no processing consent so the fixture demonstrates HTTP 403 `consent_required`. The existing tests cover the permission gate, but the fixture does not.

Return the revised source/tests, confirmed public URL, deployed Turnstile key/action, deployed revision/image identity, accepted notice and release metadata, and actual website-to-gateway test evidence listed above. Keep collection OFF. Current DNS status and the remaining deployment steps are in [DESKTOP_PUBLIC_CONNECTION_NEXT.md](DESKTOP_PUBLIC_CONNECTION_NEXT.md).
