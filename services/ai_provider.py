# services/ai_provider.py
"""
services/ai_provider.py
=======================
Unified provider gateway for AI content generation and chat completions.
Supports Gemini, OpenAI (ChatGPT), and Anthropic (Claude).
"""

import logging
import os

from data.settings_repository import get_setting

logger = logging.getLogger(__name__)


def _get_api_key(provider: str) -> str | None:
    """Retrieves the API key for the selected provider from environment variables."""
    if provider == "gemini":
        return os.getenv("GEMINI_API_KEY")
    elif provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    elif provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY")
    return None


def _resolve_model(provider: str, model: str | None, default_model: str = "") -> str:
    """Ensures the selected model matches the provider, falling back to a default if not."""
    provider = provider.lower().strip()
    model_lower = (model or "").lower().strip()

    if provider == "gemini":
        if not model or "gemini" not in model_lower:
            return default_model or "gemini-2.5-flash"
        return model
    elif provider == "openai":
        if not model or "gpt" not in model_lower:
            return default_model or "gpt-4o-mini"
        return model
    elif provider == "anthropic":
        if not model or "claude" not in model_lower:
            return default_model or "claude-3-5-haiku-latest"
        return model
    return model or default_model


def generate_content(
    prompt: str,
    system_prompt: str = "",
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    """Generates single-turn text completion using the configured AI provider.

    Returns the raw response text, or a user-friendly error message on failure.
    """
    provider = get_setting("ai_provider", "gemini") or "gemini"
    provider = provider.lower().strip()

    api_key = _get_api_key(provider)
    if not api_key:
        logger.warning(f"API key missing for provider: {provider}")
        return f"API key is not configured for {provider.capitalize()}. Please add it in Settings."

    # 1. Google Gemini
    if provider == "gemini":
        try:
            import google.genai as genai

            from config.settings import GEMINI_FLASH_MODEL

            target_model = _resolve_model(provider, model, GEMINI_FLASH_MODEL)
            client = genai.Client(api_key=api_key)

            config = genai.types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            if system_prompt:
                config.system_instruction = system_prompt

            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )
            if response and getattr(response, "text", None):
                return response.text.strip()
            return "Error: Gemini returned an empty response."
        except Exception as e:
            logger.error(f"Gemini generate_content failed: {e}")
            return f"Error: Failed to generate content via Gemini. {e}"

    # 2. OpenAI (ChatGPT)
    elif provider == "openai":
        try:
            import openai

            target_model = _resolve_model(provider, model, "gpt-4o-mini")
            client = openai.OpenAI(api_key=api_key)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            return "Error: OpenAI returned an empty response."
        except Exception as e:
            logger.error(f"OpenAI generate_content failed: {e}")
            return f"Error: Failed to generate content via OpenAI. {e}"

    # 3. Anthropic (Claude)
    elif provider == "anthropic":
        try:
            import anthropic

            target_model = _resolve_model(provider, model, "claude-3-5-haiku-latest")
            client = anthropic.Anthropic(api_key=api_key)

            message_kwargs = {
                "model": target_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                message_kwargs["system"] = system_prompt

            response = client.messages.create(**message_kwargs)
            if response.content and len(response.content) > 0:
                # Content blocks can contain text or other types; retrieve text
                return response.content[0].text.strip()
            return "Error: Anthropic returned an empty response."
        except Exception as e:
            logger.error(f"Anthropic generate_content failed: {e}")
            return f"Error: Failed to generate content via Anthropic. {e}"

    return f"Error: Unsupported provider '{provider}'."


def chat_completion(
    history: list[dict],
    system_prompt: str = "",
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    """Generates multi-turn chat response using the configured AI provider.

    Expects history as a list of dicts: [{'role': 'user'|'assistant', 'content': '...'}]
    """
    provider = get_setting("ai_provider", "gemini") or "gemini"
    provider = provider.lower().strip()

    api_key = _get_api_key(provider)
    if not api_key:
        logger.warning(f"API key missing for provider: {provider}")
        return f"API key is not configured for {provider.capitalize()}. Please add it in Settings."

    # 1. Google Gemini
    if provider == "gemini":
        try:
            import google.genai as genai

            from config.settings import GEMINI_FLASH_MODEL

            target_model = _resolve_model(provider, model, GEMINI_FLASH_MODEL)
            client = genai.Client(api_key=api_key)

            # Separate current user message from past turns
            if not history:
                return "No message history provided."

            past_turns = history[:-1]
            current_message = history[-1]["content"]

            chat_history: list[genai.types.ContentOrDict] = []
            for msg in past_turns:
                role = "model" if msg["role"] == "assistant" else "user"
                chat_history.append(
                    genai.types.Content(role=role, parts=[genai.types.Part(text=msg["content"])])
                )

            config = genai.types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
            if system_prompt:
                config.system_instruction = system_prompt

            chat = client.chats.create(
                model=target_model,
                history=chat_history,
                config=config,
            )
            response = chat.send_message(current_message)
            if response and getattr(response, "text", None):
                return response.text.strip()
            return "Error: Gemini returned an empty chat response."
        except Exception as e:
            logger.error(f"Gemini chat_completion failed: {e}")
            return f"Error: Chat failed via Gemini. {e}"

    # 2. OpenAI (ChatGPT)
    elif provider == "openai":
        try:
            import openai

            target_model = _resolve_model(provider, model, "gpt-4o-mini")
            client = openai.OpenAI(api_key=api_key)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            for msg in history:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})

            response = client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            return "Error: OpenAI returned an empty chat response."
        except Exception as e:
            logger.error(f"OpenAI chat_completion failed: {e}")
            return f"Error: Chat failed via OpenAI. {e}"

    # 3. Anthropic (Claude)
    elif provider == "anthropic":
        try:
            import anthropic

            target_model = _resolve_model(provider, model, "claude-3-5-haiku-latest")
            client = anthropic.Anthropic(api_key=api_key)

            messages = []
            for msg in history:
                role = "assistant" if msg["role"] == "assistant" else "user"
                messages.append({"role": role, "content": msg["content"]})

            message_kwargs = {
                "model": target_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }
            if system_prompt:
                message_kwargs["system"] = system_prompt

            response = client.messages.create(**message_kwargs)
            if response.content and len(response.content) > 0:
                return response.content[0].text.strip()
            return "Error: Anthropic returned an empty chat response."
        except Exception as e:
            logger.error(f"Anthropic chat_completion failed: {e}")
            return f"Error: Chat failed via Anthropic. {e}"

    return f"Error: Unsupported provider '{provider}'."
