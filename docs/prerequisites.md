# Prerequisites

Hermes Anvil (the harness) picks up only after these are done. They're interactive, human, browser-based steps that Google requires: nothing here can be automated on your behalf. Please complete all of these before you start, ideally the day before rather than right when you sit down to run the setup.

## 1. Get a Google account

Use a personal Google account (e.g. Gmail). Note: the $300 free-trial credit below is voided if the account has ever been a paying customer of Google Cloud, Firebase, or Google Maps Platform, or has previously claimed the GCP free trial.

## 2. Activate the GCP free trial

1. Go to [console.cloud.google.com](https://console.cloud.google.com).
2. Walk through the billing signup flow.
3. Add a credit or debit card. This is for identity verification only. Google will not charge it during the 90-day trial period.

You'll get **$300 in credit, usable for about 90 days**. Do this well ahead of time: card verification can occasionally take time or hit friction, and you don't want to be stuck on it right when you're ready to go.

## 3. Get a model-provider API key

Hermes Agent needs a key from one of: **[OpenRouter](https://openrouter.ai) (recommended)**, Nous Portal, or OpenAI.

- OpenRouter is free to start, no card required, and their `:free`-suffixed models cost $0 per token. A one-time $10 top-up (the credit never expires) raises your daily free-request cap from 50 to 1,000, at 20 requests/minute, which is more than enough for regular use.
- Get the key ahead of time and store it somewhere safe (a password manager, ideally).
- **Don't paste it anywhere until the harness explicitly prompts you for it.** The harness will store it securely (Google Secret Manager) rather than have you type it into a general terminal.

## 4. Verify Cloud Shell access

1. Open [shell.cloud.google.com](https://shell.cloud.google.com).
2. Run `gcloud auth list` and confirm it shows the Google account you set up billing with.

## 5. What to bring / time estimate

- A laptop with a stable internet connection.
- About 15 to 20 minutes for the harness to run, start to finish.

## 6. What *not* to do in advance

Don't manually create your GCP project or a VM yourself. The harness needs to own that step so resource naming, security rules, and IAM stay consistent with what it expects to find.
