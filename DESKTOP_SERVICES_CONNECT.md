# Maintain the Ailleo Math Practice Service

The public Math Practice website runs on GitHub Pages. Its optional speech-to-text, Sentiment Check and practice recommendations use the Ailleo gateway on Tez. The online Math Tutor LLM sends requests directly from the browser to the learner’s own API provider. The desktop app ZIP from `main` uses a separate local Python server and the model connections configured by its user. [Published website build](https://math-practice.ailleo.net/build-info.json) · [Online and desktop setup](math-practice/README.md)

## Deployment settings

- Keep the existing Cloudflare Tunnel for `api.ailleo.net` pointed at the gateway at `http://127.0.0.1:8878`. Keep model ports and the private recommendation endpoint on the desktop. Keep the public website and other domain records on their existing routes.
- Allow the exact browser origin `https://math-practice.ailleo.net`. Preserve CORS on responses and preflight support for `GET`, `POST`, `Authorization` and `Content-Type`. Keep bearer-authenticated responses out of caches.
- Require a fresh Turnstile challenge for anonymous session issuance and renewal. The gateway verifies the website hostname and the `math_practice_session` action. Keep the Turnstile secret and tunnel credentials on the desktop. The public site key and agreement version are in the [published service configuration](https://math-practice.ailleo.net/hosted-config.js).
- The November 25 deployment record reports gateway 0.4.7. Its private recommendation target is set in `recommendation.upstream_url`. For deployment, rollback and policy updates, use `desktop-service/TEZ-CUTOVER.md` and `desktop-service/PRIVATE-RECOMMENDER.md` in the release source checkout. Confirm the running gateway version before a change. [Gateway health](https://api.ailleo.net/api/health)

## Public endpoints

| Endpoint | What it does |
| --- | --- |
| `GET /api/health`, `GET /api/config` | Public gateway version and service configuration |
| `GET /api/status/speech`, `GET /api/status/decision` | Speech and sentiment upstream status, without a session |
| `POST /api/session` | Anonymous bearer session with `transcribe`, `d3` and `recommendation` scopes |
| `POST /api/consent` | Record the processing choice for the current agreement and session |
| `POST /api/transcription` | Process a WAV recording and return an editable transcript |
| `POST /api/learning-signals` | Process the original transcript with the displayed question and choices |
| `POST /api/practice/recommendation` | Use the current question or topic and bounded scored history to suggest a follow-up |

The website uses one optional processing choice for all three services, independently of the Math Tutor LLM. Keep practice data collection for model training off and preserve the existing consent records. The browser sends `collection: false` and expects `effective_collection: false`. Successful inference replies report `recorded: false` and `record_id: null`. Keep recordings, transcripts, sentiment results, and recommendation payloads and replies out of retained content and logs. [Privacy and use agreement](https://math-practice.ailleo.net/agreement.html#experimentalAgreement)

## Verify a change

1. Check the deployed build record, gateway health and public configuration. Confirm the expected version, exact origin, Turnstile settings and collection-off state. Check both upstream status routes.
2. In an external browser on the published website, have the responsible adult accept the use agreement and enable the service in **Settings → Ailleo Math Practice Service**. Complete a real Turnstile challenge in that browser and use synthetic reasoning to exercise speech-to-text and sentiment feedback. Exercise session renewal with a fresh challenge when checking session changes.
3. Submit a scored practice answer from the Chinese curriculum or AMC bank. Use **Suggest my next problem** and open the suggested question. Check that its bank and question load correctly.
4. Turn off the optional service. Verify that its requests stop and the browser clears recommendation history while ordinary practice remains available. Confirm that test content was not retained and record the outcome without including credentials or request bodies.

Health checks report reachability and upstream status. Use the browser checks to verify consent and inference after a deployment.
