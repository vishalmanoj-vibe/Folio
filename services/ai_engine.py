import os
import json
import hashlib
import logging
import re
import google.genai as genai
from core.cache import get_cache, set_cache

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a conservative long-term investment analyst.
STRICT RULES:
- Do NOT suggest buying or selling.
- Do NOT override the signal.
- Only explain and critique.

Return ONLY valid JSON in this exact format:
{
  "TICKER": {
    "explanation": "...",
    "risks": ["...", "..."],
    "verdict": "Reasonable" 
  }
}
"""

VERDICT_MAP = {
    "Reasonable": "Confident",
    "Weak": "Mixed",
    "Conflicting": "Risk flagged",
    "Mixed": "Mixed",  # explicit passthrough — do not rely on .get() default
}

TONE_MAP = {
    "you should buy": "this may indicate a positive signal",
    "strong buy": "strong bullish indication",
    "sell immediately": "downside risk present",
    "buy this stock": "this stock shows positive indicators",
    "sell this stock": "this stock shows negative indicators",
    "good time to buy": "favorable entry point structurally",
    "good time to sell": "favorable exit point structurally"
}

def _safe_parse(response_text: str) -> dict:
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError("Failed to parse AI response into JSON")

def _sanitize_tone(text: str) -> str:
    if not text:
        return text
    text_lower = text.lower()
    for bad_phrase, good_phrase in TONE_MAP.items():
        if bad_phrase in text_lower:
            pattern = re.compile(re.escape(bad_phrase), re.IGNORECASE)
            text = pattern.sub(good_phrase, text)
    return text

def _normalize_ai_response(ai_dict: dict) -> dict:
    normalized = {}
    for ticker, data in ai_dict.items():
        if not isinstance(data, dict):
            continue
            
        verdict = data.get("verdict", "Mixed")
        if verdict not in VERDICT_MAP:
            verdict = "Mixed"
            
        exp = _sanitize_tone(data.get("explanation", ""))
        risks = [_sanitize_tone(r) for r in data.get("risks", [])]
        
        normalized[ticker] = {
            "explanation": exp,
            "risks": risks,
            "verdict": VERDICT_MAP.get(verdict, "Mixed")
        }
    return normalized

def analyze_signals(signals_dict: dict) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY missing for ai_engine.")
        return {
            ticker: {"explanation": "API key missing", "risks": [], "verdict": "Mixed"}
            for ticker in signals_dict
        }

    filtered_signals = {}
    ai_insights = {}
    
    for ticker, sig_data in signals_dict.items():
        score = sig_data.get("score", 0.0)
        is_forced = sig_data.get("hysteresis_forced", False)
        
        if is_forced:
            ai_insights[ticker] = {
                "explanation": "Signal held due to hysteresis to prevent flip-flopping.",
                "risks": ["Signal is held mechanically, underlying indicators may be shifting."],
                "verdict": "Mixed"
            }
            continue
            
        if abs(score) < 0.4:
            ai_insights[ticker] = {
                "explanation": "No AI analysis (low conviction signal).",
                "risks": [],
                "verdict": "Mixed"
            }
            continue
            
        clean_signal = {
            "signal": sig_data.get("signal"),
            "score": sig_data.get("score"),
            "indicators": sig_data.get("indicators", {})
        }
        filtered_signals[ticker] = clean_signal
        
    if not filtered_signals:
        return ai_insights
        
    filtered_signals = dict(sorted(filtered_signals.items()))
    normalized_json = json.dumps(filtered_signals, sort_keys=True)
    cache_key = "ai_signal_" + hashlib.md5(normalized_json.encode()).hexdigest()
    
    cached = get_cache(cache_key)
    if cached:
        ai_insights.update(cached)
        return ai_insights
        
    client = genai.Client(api_key=api_key)
    prompt = f"""
You are a conservative long-term investment analyst.
STRICT RULES:
- Do NOT suggest buying or selling.
- Do NOT override the signal.
- Only explain and critique.

Input:
{json.dumps(filtered_signals, indent=2)}

Task:
For EACH ticker:
1. Explain WHY the signal was generated
2. List 2-3 risks
3. Give verdict: Reasonable, Weak, or Conflicting

Return ONLY valid JSON in this format:
{{
  "TICKER": {{
    "explanation": "...",
    "risks": ["...", "..."],
    "verdict": "Reasonable"
  }}
}}
"""
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                response_mime_type="application/json",
            ),
            request_options={"timeout": 10}
        )
        
        if not response or not response.text:
            raise ValueError("Empty AI response")
            
        raw_output = _safe_parse(response.text)
        normalized_output = _normalize_ai_response(raw_output)
        
        set_cache(cache_key, normalized_output, ttl=86400)
        
        ai_insights.update(normalized_output)
        
    except Exception as e:
        logger.error(f"Failed to analyze signals via AI: {e}")
        for ticker in filtered_signals:
            if ticker not in ai_insights:
                ai_insights[ticker] = {
                    "explanation": "AI analysis unavailable",
                    "risks": [],
                    "verdict": "Mixed"
                }
            
    return ai_insights
