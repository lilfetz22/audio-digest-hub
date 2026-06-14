# GitHub Actions — Secrets Setup

Go to your repository on GitHub → **Settings → Secrets and variables → Actions → New repository secret** and add each of the following.

---

## Required secrets

| Secret name | Value |
|---|---|
| `CONFIG_INI` | Paste the full contents of `src/audiobooks/config.ini` |
| `GOOGLE_CREDENTIALS_JSON` | Paste the full contents of `src/audiobooks/credentials.json` |
| `GOOGLE_TOKEN_JSON` | Paste the full contents of `src/audiobooks/token.json` |
| `GH_PAT` | A GitHub Personal Access Token with **`repo`** scope (see below) |

### How to create GH_PAT

1. GitHub → your profile picture → **Settings**
2. **Developer settings → Personal access tokens → Tokens (classic)**
3. Click **Generate new token (classic)**
4. Give it a name like `audio-digest-hub-actions`
5. Select the **`repo`** scope (top-level checkbox)
6. Click **Generate token** and copy the value
7. Paste it as the `GH_PAT` secret in your repository

`GH_PAT` is needed so the workflow can write the refreshed Google OAuth token
back into `GOOGLE_TOKEN_JSON` after each run. Without it, the token will expire
and Gmail authentication will break within a few hours.

---

## What each secret does at runtime

```
CONFIG_INI              → recreates src/audiobooks/config.ini  (Supabase / Gemini keys)
GOOGLE_CREDENTIALS_JSON → recreates src/audiobooks/credentials.json  (OAuth client id/secret)
GOOGLE_TOKEN_JSON       → recreates src/audiobooks/token.json  (OAuth access + refresh token)
GH_PAT                  → lets the workflow call `gh secret set` to save the refreshed token
```

---

## Manual trigger

Once the secrets are in place you can also trigger a run immediately without
waiting for 8:15 AM UTC:

**Repository → Actions → Daily Audio Digest → Run workflow**

An optional "Skip Friday cleanup step" toggle is available on manual runs.
