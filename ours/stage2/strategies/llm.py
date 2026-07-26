"""LLM helper for strategies: same Token Factory route as the root tf_client,
but returns (text, cost_estimate) so strategies can fill StrategyResult.cost_usd.
"""

import os

from openai import OpenAI

BASE_URL = os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")
EST_PRICE = (0.5, 2.0)  # $/1M tokens (in, out) — same estimate as root tf_client


# Reasoning models (e.g. Kimi-K2.6) spend tokens on hidden reasoning_content
# before the visible answer, and hard questions can reason past any tight cap
# (finish_reason=length with content=None). Verified against the live API:
# omitting max_tokens gets the server default of only 8192, so we always send
# an explicit large cap. It must fit inside max_model_len=262144 (prompt +
# completion combined — 1M is rejected), so 128k leaves 128k for the prompt.
# max_tokens is a cap, not a spend, so a huge value costs nothing extra.
# reasoning=False disables thinking via vLLM's chat_template_kwargs — the only
# knob Token Factory accepts (reasoning_effort is silently ignored,
# enable_thinking does nothing; verified against the live API for Kimi-K2.6).
def chat(messages, model, max_tokens=131072, temperature=0.2, reasoning=True,
         **kw):
    key = os.environ.get("NEBIUS_API_KEY")
    if not key:
        raise RuntimeError("NEBIUS_API_KEY not set (put it in .env)")
    if not reasoning:
        kw.setdefault("extra_body", {})["chat_template_kwargs"] = \
            {"thinking": False}
    client = OpenAI(base_url=BASE_URL, api_key=key)
    # untruncated reasoning chains can run past 10 minutes — timeout to match
    resp = client.chat.completions.create(model=model, messages=messages,
                                          max_tokens=max_tokens,
                                          temperature=temperature,
                                          timeout=1800, **kw)
    u = resp.usage
    cost = (u.prompt_tokens * EST_PRICE[0]
            + u.completion_tokens * EST_PRICE[1]) / 1e6
    text = resp.choices[0].message.content or ""
    if not text:
        raise RuntimeError(
            f"model returned empty content (finish_reason="
            f"{resp.choices[0].finish_reason}, {u.completion_tokens} "
            f"completion tokens)")
    return text, cost
