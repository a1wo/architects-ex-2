# Exercise 2

[Exercise repo](https://github.com/Apex-IL/architects-ex-2)

Build a Domain-Specific Customer Support Chatbot on Harel Insurance Policies

# 🚀 Overview

This capstone simulates a real-world, high-stakes AI systems challenge: building a production-grade, domain-specific customer support chatbot for Israel's largest insurance provider.

You will design and implement an end-to-end GenAI system that:

- **Ingests and structures** real insurance policy data
- **Answers customer questions** across twelve insurance domains (Car, Life, Travel, Health, Dental, Mortgage, Business, Apartment, Long-Term Care, Personal Accident, Diseases & Disabilities, Loss of Working Ability)
- **Grounds every answer** in official documentation, with explicit citations
- **Outperforms a bare LLM baseline**
- **Works with open-weights models** served via Nebius Token Factory

This is not a toy demo. The final deliverable should resemble a system that could realistically power an insurer's first-line support chatbot.

**Why this challenge matters.** Real-world AI systems fail not because models are weak, but because:

- Data is messy and unstructured
- Knowledge must be grounded and verifiable
- Evaluation is subtle and unforgiving

Modern models are extremely strong — they will answer many insurance questions plausibly from memory alone. That is exactly the trap: *plausible* is not *grounded*, and in insurance, an ungrounded answer is a lawsuit. Your job is to build the system that knows what it knows.

### Timeline & Format

- **Dates:** July 12 - July 26
- **Teams:** 3–4 participants
- **Mentorship:** 3 live office hours with APEX mentors
- **Final Presentations:** August 2nd (last class)

# **🧠** The Challenge

The challenge unfolds in three conceptual stages:

## Stage 1: Model Baseline & Evaluation (Due July 19)

**Goal:** establish a strong baseline and learn to measure progress.

You will:

1. Measure the baseline: Run the provided development question set (`reference_questions.json`) through the **strongest open-weights model on Nebius Token Factory** (e.g. the latest DeepSeek or GLM model) as a bare model — just the question, no documents. Use the provided `baseline_runner.py` with `OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1`. **All teams share one course API key** — make your calls through the provided `tf_client.py`, watch the cost estimate it prints, and play fair with the shared balance.
2. **Build an evaluation harness** — It must score a batch of answers against the dev set's ground truths and report at least:
    - **Answer relevance** — does the answer agree with the ground-truth answer on the asked fact? Use an LLM-as-judge (a Token Factory model works); force structured JSON output and pin the judge model so runs are comparable.
    - **Hallucination rate** — confident answers that *contradict* the ground truth. Decide how your judge treats refusals ("I don't know" is not a hallucination — a system that knows what it doesn't know is worth measuring).
    - **Citation accuracy** — does the cited evidence actually establish the answer? Resolve each cited `{file, page}` to the actual corpus page and use an LLM judge to decide whether the cited pages establish the **ground-truth answer** (fully / partially / not at all). The same fact often appears in several corpus documents — *any* page that truly establishes it earns credit; there is no fixed list of "correct" sources to match against. The `ground_truth_sources` in `reference_questions.json` show where each answer was authored from — useful for debugging your retrieval, but not the scoring target. A citation pointing at a nonexistent file or page counts against you. (For the bare baseline, expect ~zero — the model has nothing to cite.)
    - **Latency** per question.
    Your final grade uses our internal harness (same criteria, plus conversational quality and efficiency), so a harness that tracks these honestly is your compass for the whole exercise. Wire it into your loop from day one.
3. Experiment with at least two prompt strategies (e.g. "answer only if certain", "always cite your source", few-shot-prompting) and observe how the failure profile shifts.

**Questions to answer in your baseline report:**

- Where does the baseline succeed *without* any Harel documents? What does that tell you about what's in its training data?
- When it's wrong, is it wrong *confidently*? Which failure is worse for an insurer — a wrong answer or "I don't know"?
- The judge is itself an LLM. Find one question where you disagree with the judge's verdict. What does that imply about your evaluation at scale?

**Deliverable:** a 1-page baseline report with the metrics table and the three answers above.

## **Stage 2: Retrieval Pipeline (RAG Core) (Due July 26)**

**Goal:** beat the baseline with retrieval + grounding. Same model family, possibly even a *smaller* open-weights model: a model that *reads the right page* should beat a bigger one that *remembers the internet*.

**One rule: you may NOT fine-tune, LoRA, or RL-train any model.** You can add external models (e.g. a document embedding model) as long as you don’t change their weights.

**The corpus is provided:** we scraped Harel's official insurance content for all 12 domains (~570 documents: policy PDFs and web pages, mostly Hebrew). Download it with the provided `get_corpus.py` (public dataset: [`orik/apex-ex2-harel-corpus`](https://huggingface.co/datasets/orik/apex-ex2-harel-corpus)). Your work starts at parsing and structuring the corpus.

**1. Build retrieval**

- Parse the documents, chunk them, and build a search index over the corpus. Preserve structure — sections, tables, and **page numbers**; citations require them.
- Return top-k passages with metadata (file, page, domain).

**Questions to guide your design (worth discussing before coding):**

- What's your chunk size, and why? What breaks with page-sized chunks? With sentence-sized ones?
- Embedding-based search has real failure modes on this corpus. Find them on the dev set. How would you improve retrieval where embeddings alone fall short?
- How do you *know* your retrieval works, independent of generation?
- Is there any additional context or metadata you should supply together with the retrieved text?
- Should you use document embeddings or keyword search (or both?)

**2. Generate grounded answers**

- Answer strictly from retrieved context; attach a citation (file + page) to every factual claim.
- Implement a safe fallback when evidence is missing: "I don't have enough information" beats a confident guess.

**Outcome:** a working RAG system, measurably better than the Stage 1 baseline on relevance, hallucination rate, and citation accuracy.

### **🛠️ Recommended Open-Source Stack**

*(Not mandatory, but strongly encouraged)*

- **Document Processing:** Docling
- **Vector DB:** Qdrant / Chroma / Milvus
- **Embeddings**: sentence-transformers

### Additional Resources

https://sbert.net/

## **Stage 3: Agentic Flow & Systemization (Due Aug 2)**

**Goal:** build a robust, production-style AI system.

You will:

- Design a single- or multi-agent architecture
- Handle ambiguity, cross-domain, and complex questions requiring multi-hop reasoning.
- Package the system behind the **provided FastAPI contract** (`contract.py`) — the final evaluation calls your `/ask` endpoint, so the contract is not optional

**Optional bonus:** voice interface, simple UI.

**Outcome:** a realistic customer-support AI system with clear separation of concerns, suitable for real deployment.

## **🏆 The Competition (Submission by Aug 2)**

You are competing against:

- **GPT-5.2 (baseline)**
- **Other APEX teams**
- …and realistically, against how GenAI systems fail in production 🙂

Your final system will be tested on a **hidden blind question set**.

**Scoring**

- **Relevance (65%)** – Does it correctly answer the question?
- **Citation Accuracy (15%)** – Are sources correct and precise?
- **Efficiency (10%)** – Latency and cost profile
- **Conversational Quality (10%)** – Clarity, tone, flow

**Bonus**

- Voice support: +5%
- UI polish: +5%

**How submission works:** on submission day you receive `blind_questions.json` — the hidden blind set, questions only. You run the provided `submit_runner.py` on your own machine: it asks your local `/ask` endpoint every question, measures latency, and writes one answers JSONL. You send us that file; we score it with our internal harness. At final presentations we re-ask a few blind questions against your live system — the answers should match your submission.

**How you'll be judged:** answer relevance against the ground-truth answers (LLM-as-judge), citation accuracy (LLM-as-judge: do the pages you cite establish the ground-truth answer?), efficiency (latency and cost), and conversational quality — the same criteria your Stage 1 harness tracks, so your dev-set numbers should roughly predict your blind-set numbers.

## 📘 Additional information and materials About Harel Insurance

Harel Insurance is Israel’s largest insurance and financial services group, serving millions of customers across health, life, general insurance, and long-term savings.

In this capstone, Harel serves as a **realistic enterprise customer** with:

- Broad and fragmented product coverage
- Highly regulated, legally precise documentation
- Complex policy structures that vary by product, customer type, and conditions

Your task is to design an AI system capable of operating in this environment where **accuracy, grounding, and trust** are non-negotiable. In this exercise, we’ll focus on **8 key insurance domains**: Car, Life, Travel, Health, Dental, Mortgage, Business, Apartment.

Questions may range from simple eligibility checks to nuanced policy conditions and exclusions.

### Data Provided

All domain knowledge used by your system must be derived **exclusively** from Harel’s official insurance content. You should scrape, ingest, and store the relevant data.

**Dataset characteristics**

- URLs: https://www.harel-group.co.il/insurance/<insurance_type>
- Source types: ASPX web pages and PDFs (do not parse any other document)
- Languages: Hebrew and English (source-dependent)
- Rich structure: tables, bullet lists, conditions, and legal clauses
- Scale: ~350 documents

Every answer must include **document + section/page citation**

To enable iterative development and tuning, you will receive reference questions for a subset of the domains: Travel, Health, Car, Apartment, Life, Business. The final evaluation will be conducted on a **hidden blind question set** covering **all insurance domains in scope**, including unseen domains (Dental, Mortgage, Life).

**What this tests**

- Domain generalization beyond seen examples
- Retrieval robustness across heterogeneous policy structures
- Agent routing and grounding without memorization