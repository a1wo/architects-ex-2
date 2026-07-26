"""
Stage 1 baseline: run the dev questions straight through a bare model with
NO retrieval, producing an answers file the eval harness can score.

    export OPENAI_API_KEY=...  # paste in nebius API key
    export OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1  # Use token factory
    python baseline_runner.py --model deepseek-ai/DeepSeek-V4-Pro
    # then score baseline_answers.jsonl with YOUR evaluation harness (Stage 1)

Calls go through the openai SDK, which natively honors OPENAI_API_KEY and
OPENAI_BASE_URL — set the latter for any OpenAI-compatible endpoint (Token
Factory, a local vLLM server, ...). Try --system-prompt variants and watch
how the failure profile (not just the score) changes.
"""
import argparse
import json
import time

from openai import OpenAI

DEFAULT_SYSTEM = ("You are a customer-support assistant for Harel Insurance (Israel). "
                  "Answer the customer's question in the language it was asked. "
                  "If you cite a source, cite the exact document and page.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="reference_questions.json")
    ap.add_argument("--model", default="deepseek-ai/DeepSeek-V4-Pro")
    ap.add_argument("--system-prompt", default=DEFAULT_SYSTEM)
    ap.add_argument("--out", default="baseline_answers.jsonl")
    args = ap.parse_args()

    client = OpenAI()  # reads OPENAI_API_KEY + OPENAI_BASE_URL from the env

    questions = json.load(open(args.questions, encoding="utf-8"))
    if isinstance(questions, dict):  # staff sets wrap the list in {"questions": [...]}
        questions = questions["questions"]
    with open(args.out, "w", encoding="utf-8") as out:
        for q in questions:
            t0 = time.time()
            resp = client.chat.completions.create(model=args.model, messages=[
                {"role": "system", "content": args.system_prompt},
                {"role": "user", "content": q["question"]}],
                timeout=120)
            rec = {"id": q["id"],
                   "answer": resp.choices[0].message.content,
                   "citations": [],  # the model has no documents -- that's the point
                   "latency_ms": (time.time() - t0) * 1000,
                   "tokens": {"prompt": resp.usage.prompt_tokens,
                              "completion": resp.usage.completion_tokens}}
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"{q['id']}: {rec['answer'][:70]!r}... ({rec['latency_ms']:.0f} ms)")
    print(f"\nwrote {args.out} -- now score it with your evaluation harness")


if __name__ == "__main__":
    main()
