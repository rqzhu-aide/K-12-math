# Connect Ailleo speech-to-text and D3 to the public website

Prepared 2026-11-16 for the desktop programmer. This is the remaining integration work after the online tutor settings update. It builds on `DESKTOP-BACKEND-STATUS-v2.md`; that report describes local tests, not a working public endpoint.

## What the website needs

The public frontend is **https://math-practice.ailleo.net/** on GitHub Pages. The existing Squarespace website at **https://ailleo.net/** must keep working.

The desktop supplies only these optional, free services:

- Speech-to-text: audio becomes a transcript the learner can review and edit.
- D3: the original transcript is assessed for confidence, reasoning clarity, and engagement. These are model observations, not a mathematics grade or a psychological diagnosis.

The math tutor is separate. The learner uses their own provider URL/API key, or their own ChatGPT account through a helper on their own computer. **Do not add a tutor proxy to the operator gateway. Do not receive or store tutor API keys, account tokens, tutor prompts, or tutor replies.** The learner's ChatGPT helper is not your desktop gateway.

```text
Browser at math-practice.ailleo.net
  |
  +-- Math tutor --> learner's own API provider
  |              or learner's local ChatGPT helper --> OpenAI
  |
  +-- Optional speech / D3 --> public HTTPS API hostname
                               --> Cloudflare Tunnel
                               --> gateway on desktop, localhost:8878
                                    +-- speech, localhost:9934
                                    +-- D3, localhost:9951
```

The online tutor update does not activate speech/D3. The site continues to show these services as **Not connected** until the public gateway and the separate frontend adapter pass the checks below. Adding a DNS record alone will not activate them.

## 1. Publish the gateway, preserving the current websites

Proposed API hostname: **api.math-practice.ailleo.net**. This is a proposal, not a hostname already configured or tested. Return the actual hostname you deploy.

1. Run a named Cloudflare Tunnel on the always-on desktop. Route only the chosen API hostname to `http://127.0.0.1:8878`, with a final catch-all 404 route. Keep the raw model ports private. No router port forwarding is needed for this tunnel design.
2. Configure the hostname in a Cloudflare-managed DNS zone. A `*.cfargotunnel.com` CNAME alone in an unrelated Squarespace DNS zone does not complete a public Tunnel setup. If `ailleo.net` moves to Cloudflare DNS, the owner must first review a complete copy of its existing DNS records, then change the nameservers at Squarespace. Preserve the Squarespace apex and `www` records, email records, verification records, and `math-practice -> rqzhu-aide.github.io`. The registrar and Squarespace hosting can remain unchanged.
3. Keep the website's GitHub Pages CNAME DNS-only while retaining its current HTTPS setup. The new API route uses Cloudflare Tunnel. Do not change the frontend hostname or serve the whole Squarespace website through the gateway.
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

`turnstile_token` is the requested public-deployment addition to v2's empty-body issuance. Return the existing opaque `token`, `session_id`, `scopes`, `issued_at`, `expires_at`, and `renew_after_seconds`. Accept the current bearer token for renewal and document whether renewal also requires a fresh challenge. The frontend will serialize renewal so concurrent requests do not race token rotation. Never put a token in a URL or log.

For public issuance, validate Turnstile on the server using Siteverify. Check `success`, hostname `math-practice.ailleo.net`, and an agreed action, proposed `math_practice_session`. Return the public site key to the frontend programmer; keep the secret key on the desktop. Invalid, missing, expired, or replayed challenges must not issue a session. Publish stable error codes for these cases.

Keep rate limits on issuance and service use, plus an overall model concurrency/queue limit. Return `429` with `Retry-After`; bound the queue and request duration. Trust forwarded client IP headers only from the tunnel connector. CORS and Turnstile reduce misuse; they do not prove a person's identity or guarantee that all callers use the UI.

Reference: [Turnstile server-side validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/).

## 3. Keep processing permission separate from retention

Preserve `POST /api/consent` with independent `transcription`, `d3`, and `collection` choices, plus `notice_version`. Return the server-recorded consent state and `effective_collection`. Declining collection must still allow permitted processing.

For the first public connection, keep the operator collection switch **OFF**, and have the frontend send `collection: false`. The current general website agreement is not a replacement for the service-specific notice and choices.

Before enabling collection, finish the owner-approved retention period, deletion contact/process, participant eligibility and guardian-supervision requirements, and versioned EN/CN notice. Enforce eligibility and current consent as well as the operator switch and retention setting. Never present an anonymous session as proof of identity or guardian consent.

The owner chose **transcripts, D3 results, and relevant question metadata only**. Raw recordings are processing-only. Verify audio cleanup on success, failure, timeout, cancellation, and worker restart, including gateway/upstream temporary files and logs. Implement transcript/result expiry and authorized deletion across spool, archive, indexes, and backups before enabling retention.

## 4. Finish and share the exact API contract

Send an OpenAPI document or equivalent complete request/response fixtures. Include the source revision, deployed image digest, sanitized configuration example, and tests. Do not send credentials, real learner records, or raw recordings.

| Route | Required behavior |
| --- | --- |
| `POST /api/session` | Anonymous issuance and renewal, including Turnstile policy |
| `POST /api/consent` | Independent processing and collection choices; reject stale notice |
| `GET /api/status/speech` | Proposed frontend status route; confirm or supply the existing exact route |
| `GET /api/status/decision` | Proposed D3 status route; confirm or supply the existing exact route |
| `POST /api/transcription` | Raw WAV plus question metadata, bearer token and processing permission |
| `POST /api/learning-signals` | Original transcript plus question context, bearer token and D3 permission |

Status may retain `{ "available": true, "checked": "upstream-health", "model": "..." }`. Document whether status requires a session. The UI will distinguish upstream health from a successful inference test.

### Transcription

The existing recorder already produces one mono, 16 kHz, 16-bit PCM WAV, at most 60 seconds. Accept it as `Content-Type: audio/wav`; no WebM conversion or browser chunking is needed.

Use `question_id`, `bank`, and `release` query metadata. Real frontend IDs use values such as `question_id=1989_AMC_8_Q02` and `bank=amc`; do not require the illustrative `amc8-1989-p02` / `amc8` strings in the v2 report. Agree on one explicit release identifier; it is not necessarily the contest year.

Preserve the v2 response fields `text`, `text_chars`, `latency_ms`, `chunks`, `session_id`, `question_id`, `recorded`, and `record_id`. With collection off, `recorded` must be false and `record_id` null. Do not log audio bodies or transcript text.

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

**Resolve one behavior mismatch:** the existing local D3 implementation includes the displayed question and choices as context, while excluding the reference answer and solution. V2 says it excludes the question and choices too. Restore the existing context behavior and update its tests, or document that proposed behavior change for review before integration. Do not send reference answers or solutions upstream to D3.

Preserve the canonical rubrics from `student_assessment.py`: confidence has 3 choices, reasoning has 4, engagement has 3. Return `question_id`, the exact analyzed `transcript`, `rubric_version`, `answers`, full letter-to-code/label `rubrics`, timing, session ID, and collection fields. Validate complete, finite probabilities in range with the documented normalization tolerance. The frontend will display the probability of the selected choice; it must not mistake an upstream margin named `confidence` for that probability.

For every non-2xx response, retain:

```json
{"error":{"code":"consent_required","message":"<safe explanation>"},"request_id":"<identifier>"}
```

Document all existing v2 error codes plus the new challenge errors. Never return traceback, tokens, upstream authorization headers, or raw request bodies.

## 5. Frontend work after your handoff

The frontend programmer will:

1. Add the confirmed HTTPS service base and Turnstile public key to the hosted build. These are public configuration, not secrets. They are not active settings in the current build.
2. Add the optional-service EN/CN notice, processing choices, session issuance/renewal, and error recovery. Keep collection off initially.
3. Route only speech and D3 calls to the gateway. Keep all tutor traffic and tutor credentials on the learner's independent connection.
4. Map gateway status and rubric responses into the existing recorder and learning-signals panel. Reject stale results after question or transcript changes.
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
