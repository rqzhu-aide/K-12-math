# Use your ChatGPT account for tutoring

Run this companion on the same computer as your browser. It connects the online Math Practice website to your own ChatGPT account. Tutoring is optional. You can browse questions and practice without this companion.

## Start the companion

1. Extract the downloaded ZIP into a folder.
2. Use a shared user or system installation of Python 3.10 or later. Install the sign-in dependencies once in that installation:

   Windows:

   ```powershell
   py -3 -m pip install --user "PyJWT[crypto]"
   ```

   macOS or Linux:

   ```sh
   python3 -m pip install --user "PyJWT[crypto]"
   ```

   If your operating system manages Python packages, install PyJWT and cryptography through its package manager instead. Use packages shared across your projects.

3. On Windows, double-click `Start Tutor Companion.cmd`. On macOS or Linux, open a terminal in the extracted folder and run:

   ```sh
   sh start-tutor-companion.sh
   ```

4. Keep that window open. Copy its pairing key into the companion connection fields in [Math Practice Settings](https://math-practice.ailleo.net/settings.html). Connect, then choose Continue with ChatGPT. Finish the sign-in and plan permission in your default browser, then return to Settings.
5. Choose an account model and test it. The test sends a small structured mathematics review to OpenAI. A successful test confirms that request completed; it does not guarantee future availability or teaching quality.

The key changes each time you restart the companion. Paste the new key into Settings and connect again. Never share it. It allows this website to make tutor requests using the account you connect.

## Browser permission and connection problems

Your browser may ask whether Math Practice can access your local network. Allow that permission for this site so it can reach the companion running on your computer. If you previously denied it, change the site's local-network permission in your browser settings and try connecting again.

If connection fails, confirm that the companion window is still open, its current key matches Settings, and the browser runs on the same computer. The connection address is fixed:

```text
http://127.0.0.1:8879
```

If the local port is already in use, close the other tutor companion window and restart. A managed browser or computer may block website access to local services. Follow that device's policy or use your own API connection instead.

If sign-in or model testing reports an account restriction or usage limit, follow the message in Settings. An eligible ChatGPT plan and account permission are required. Signing in alone does not establish that a model can complete a tutor request.

## Where your information goes

The companion listens only on this computer's loopback address. It accepts account actions and tutoring requests only from the exact Math Practice site origin with your pairing key. The account credentials stay in the existing protected Math Practice account storage on this computer. The website receives account status and completed tutor text, never account tokens.

Tutor prompts and inline question images travel from your browser to this companion and then directly to OpenAI. They do not pass through the website owner's desktop. The owner's speech recognition and initial assessment services are separate from this companion.

To stop website access, close the companion window or press Ctrl+C. To disconnect your ChatGPT account, use Sign out in Settings while the companion is running. If remote revocation cannot be confirmed, follow the displayed directions to disconnect Math Practice in ChatGPT settings. Local account storage is reused by Math Practice on this device, including its desktop app.

## Local development

Production trusts only `https://math-practice.ailleo.net`. To allow a specific local test website, start the companion with an explicit origin:

```sh
python3 runtime/tutor_companion.py --test-origin http://127.0.0.1:8877
```

The option can be repeated for another exact HTTP localhost or loopback origin. It cannot enable a remote site, a wildcard, or a different listening address. Requests also require the pairing key. Browser preflight requests contain no key and disclose no account information.

The implementation reuses OpenAI's documented [local sign-in flow](https://developers.openai.com/siwc/token-sharing-open-source/sign-in) and [ChatGPT plan inference flow](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference). It does not read Codex or another application's credentials.
