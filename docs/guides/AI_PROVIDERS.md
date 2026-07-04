# AI Provider API Keys Guide

This guide explains how to obtain and configure API keys for the supported AI models in Folio: **Google Gemini**, **OpenAI ChatGPT**, and **Anthropic Claude**.

---

## 1. Google Gemini (AI Studio)

Google Gemini is the default provider for Folio. Google offers a generous free tier for Gemini models in Google AI Studio.

### How to Get Your API Key:
1. Go to the [Google AI Studio](https://aistudio.google.com/) website.
2. Sign in with your Google account.
3. Click on the **Get API Key** button in the top left or center.
4. Click **Create API Key**.
5. Select a project (or create a new one) and click **Create API Key in Existing Project** (or **Create API Key in New Project**).
6. Copy the generated key (it starts with `AIzaSy`).

### Configuration in Folio:
- **Environment Variable**: Add `GEMINI_API_KEY=your_key_here` to your `.env` file.
- **Settings UI**: Under **Settings** -> **AI Provider**, select **Google Gemini**, paste the key, and click **Save Profile Settings**.

---

## 2. OpenAI ChatGPT

OpenAI's ChatGPT models (such as `gpt-4o` and `gpt-4o-mini`) can be used for chat assistance and report commentary. Note that OpenAI requires a paid API developer account (prepaid credits).

### How to Get Your API Key:
1. Go to the [OpenAI Platform](https://platform.openai.com/).
2. Sign in or create a developer account.
3. Make sure you have added a credit balance (under **Settings** -> **Billing**). OpenAI API does not use your ChatGPT Plus subscription.
4. Navigate to **API Keys** in the left sidebar.
5. Click **Create new secret key**.
6. Name the key (e.g., `Folio Dashboard`) and click **Create secret key**.
7. Copy the key immediately (starts with `sk-proj-`). It will not be shown again.

### Configuration in Folio:
- **Environment Variable**: Add `OPENAI_API_KEY=your_key_here` to your `.env` file.
- **Settings UI**: Under **Settings** -> **AI Provider**, select **OpenAI (ChatGPT)**, paste the key, and click **Save Profile Settings**.

---

## 3. Anthropic Claude

Anthropic's Claude models (such as `claude-3-5-sonnet` and `claude-3-5-haiku`) provide high-quality structural commentary and trends analysis. Like OpenAI, Anthropic requires prepaid API developer credits.

### How to Get Your API Key:
1. Go to the [Anthropic Console](https://console.anthropic.com/).
2. Sign in or create an account.
3. Navigate to **Billing** and fund your account. Anthropic API usage is independent of your Claude Pro subscription.
4. Go to **API Keys** in the navigation bar.
5. Click **Create Key**.
6. Name the key (e.g., `Folio Dashboard`) and click **Create**.
7. Copy the key immediately (starts with `sk-ant-`).

### Configuration in Folio:
- **Environment Variable**: Add `ANTHROPIC_API_KEY=your_key_here` to your `.env` file.
- **Settings UI**: Under **Settings** -> **AI Provider**, select **Anthropic (Claude)**, paste the key, and click **Save Profile Settings**.

---

## ⚡ Testing Your Key Connection

Once you have pasted your key in the **Settings** page:
1. Click the **Test Connection** button next to the API key field.
2. Folio will run a quick, tiny test query using the selected provider.
3. If successful, you will see a green checkmark check and the response from the model.
4. If it fails, you will see a red error message detailing the reason (e.g. invalid key, out of quota, or network timeout).
