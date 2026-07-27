"""The regular RAG baseline: embed the question, retrieve the top-K paragraph
chunks from the chosen DB, stuff them into the prompt, ask for a cited JSON
answer. No routing, no reranking, no query rewriting — this is the bar every
fancier strategy has to beat.
"""

import json
import re
import time
from collections import Counter

from .base import Citation, Strategy, StrategyResult
from .llm import chat
from .retrieval import DEFAULT_DB, retrieve

SYSTEM = (
    "You are a customer-support assistant for Harel Insurance (Israel). "
    "Answer ONLY from the numbered source excerpts in the user message — never "
    "from memory. If the excerpts don't contain the answer, say so (in the "
    "question's language) and cite nothing. Answer in the language of the "
    "question (usually Hebrew). Reply with ONLY a JSON object, no prose around "
    "it, no code fences:\n"
    '{"answer": "<answer in the question\'s language>", '
    '"citations": [{"file": "<file exactly as in the excerpt header>", '
    '"page": <page number from the excerpt header>, '
    '"quote": "<short verbatim quote that supports the answer>"}]}\n'
    "Cite only excerpts you actually used.")


class TopKContextStuffing(Strategy):
    name = "topk-context-stuffing"
    description = ("Baseline RAG: retrieve top-K paragraph chunks, stuff them "
                   "into the prompt, answer with citations.")
    params = {
        "k": {"default": 8, "min": 1, "max": 30, "label": "Top-K chunks"},
        "temperature": {"default": 0.2, "min": 0.0, "max": 1.0, "step": 0.1,
                        "label": "Temperature"},
        "reasoning": {"default": "off", "type": "select",
                      "options": ["on", "off"], "label": "Reasoning"},
    }

    def ask(self, question, history=None, k=8, temperature=0.2,
            reasoning="on", db=DEFAULT_DB, model=None, progress=None, **_):
        mark = progress or (lambda stage: None)
        t0 = time.perf_counter()
        mark("retrieve")
        contexts = retrieve(question, db=db, k=k)
        excerpts = "\n\n".join(
            f"[{i + 1}] file: {c.file} | page: {c.page} | domain: {c.domain}\n{c.text}"
            for i, c in enumerate(contexts))
        messages = [{"role": "system", "content": SYSTEM},
                    *[{"role": h["role"], "content": h["content"]}
                      for h in (history or [])],
                    {"role": "user",
                     "content": f"Source excerpts:\n{excerpts}\n\n"
                                f"Customer question: {question}"}]
        mark("generate")
        # UI sends "on"/"off"; older callers may send 1/0 — treat both.
        reply, cost = chat(messages, model=model, temperature=float(temperature),
                           reasoning=str(reasoning) not in ("off", "0"))

        mark("parse")
        m = re.search(r"\{.*\}", reply, re.DOTALL)
        try:
            parsed = json.loads(m.group(0)) if m else {"answer": reply}
        except json.JSONDecodeError:
            parsed = {"answer": reply}
        citations = [Citation(file=c["file"], page=c.get("page"),
                              quote=c.get("quote"))
                     for c in (parsed.get("citations") or [])
                     if isinstance(c, dict) and c.get("file")]
        domain = (Counter(c.domain for c in contexts).most_common(1) or [(None,)])[0][0]
        return StrategyResult(answer=str(parsed.get("answer", "")).strip(),
                              citations=citations, contexts=contexts,
                              domain=domain, model=model, cost_usd=cost,
                              latency_ms=(time.perf_counter() - t0) * 1000)
