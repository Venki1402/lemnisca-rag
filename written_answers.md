# Written Answers

## Q1 — Routing Logic

**rules:**
my router classifies a query as `Complex` if it meets any of these criteria:

1. validates the existence of over 20+ words in the query.
2. mentions demanding reasoning keywords: "compare," "why," "issue," "error," "difference," "troubleshoot," "complaint," "multiple."
3. mentions multiple queries (more than 1 question mark).
   otherwise, it defaults to `Simple`.

**why:**
I drew boundaries strictly around **heuristics** that require either summarizing multiple documents (length, multi-step issues) or cross-referencing capabilities (compare, difference). Llama 3.1 8B excels at fast knowledge recall, while Llama 3.3 70B's parameter advantage helps untangle multiple conditionals.

**misclassification example:**
a query like, _"what are the names of the three main features?"_ misclassifies as `Simple`. while short, it asks for structured data enumeration. Llama-3.1-8b sometimes misses minor details in lists whereas 70b handles reasoning across paragraphs better. The router focuses purely on syntax, so it misses latent complexity.

**improvement without LLMs:**
I would introduce semantic term-frequency detection (TF-IDF or embedding categorization against a "complex benchmark questions" dataset footprint). I could classify vectors in low-latency using a local tiny-SVM to infer complexity without making LLM calls.

---

## Q2 — Retrieval Failures

**chunking context:**
I used simple overlapping word/character chunking (1000 characters, 200 overlap).

**query:**
"how long does it take for clearpath customer success to respond to a server downtime alert?"

**system behavior:**
the system failed to retrieve the answer chunk or hallucinated wildly.

**why it failed:**
the answer ("20 minutes") was physically found inside an embedded flowchart table at the back of the documentation PDF. PyMuPDF extracts text left-to-right, often garbling table contents into unsearchable strings like `Downtime \n Server \n Alert \n 20 \n Mins`. The dense vectors of "customer success respond" didn't map near these random strings.

**fix:**
implement a layout-aware PDF parser (like llamaParse, unstructured.io, or OCR like tesseract) that preserves tabular relationships. additionally, generating synthetic Q&A pairs for each table and appending those to the index (hypothetical document embeddings - hyde) would vastly improve mapping.

---

## Q3 — Cost and Scale

**scenario:** 5,000 queries/day.
assuming an **85/15** split between simple (`llama-3.1-8b-instant`) and complex (`llama-3.3-70b-versatile`).

- simple average payload: 2,000 input tokens (system + context), 100 output tokens.
- complex average payload: 3,000 input tokens, 300 output tokens.

**daily estimates:**

- simple (4,250 queries): 8.5M input, 425k output.
- complex (750 queries): 2.25M input, 225k output.
  _(groq's 70b token prices are roughly 10x the 8b prices per 1M)_

**biggest cost driver:**
input tokens for the contextual RAG payload. even on simple questions, we are pumping thousands of tokens per query.

**highest-roi change:**
applying a "small-to-big" retrieval approach or context compression. instead of feeding whole chunks to the LLM, use a very cheap model or library like `llmlingua` to compress the chunks and strip filler words.

**what to avoid:**
avoiding strict caching layer optimization for all queries. because chunks change if underlying docs update, caching exact prompt outputs causes stale answers. only cache very low-dimensional queries or embeddings, not direct text completions.

---

## Q4 — What Is Broken

**limitation:**
the single most significant flaw is the absence of **conversational memory (session state)**. currently, the system operates as a zero-shot endpoint. If a user asks "what is clearpath?" and then follows up with "how much does it cost?", the system does not know what "it" refers to because there is no external state management passing history into the prompt construction.

**why i shipped it:**
it fulfilled the explicit minimal requirements of the pipeline. Adding conversation memory significantly blows up token budgets and parsing complexity at Layer 1 and 2, meaning the evaluator would need heavier logic to know what flags depend on previous turn context.

**direct fix:**
use an ongoing session array that retains the user’s last N question-answer pairings. I would pass previous turns through an orchestrator into the Llama input array (`messages=[...]`) and potentially utilize a fast rewrite LLM to rewrite ambiguous pronouns in new queries ("What does _it_ cost?") before searching the FAISS index.

---

## bonus — streaming & structured output

**where does structured output parsing break with streaming?**
parsing structured outputs (like json) breaks heavily during streaming because the payload is incomplete at almost any given moment while tokens generate. For example, if a model is streaming `{"status": "success", "reason": "all good"}`, standard validation libraries like pydantic or `json.loads` will instantly crash if they receive fragments like `{"status": "suc` due to trailing commas and unclosed brackets.

in order to evaluate structured outputs mid-stream, developers must use lenient, partial json parsers (like `jitter` or `stream-json`) to rebuild the structure as it arrives. Similarly, our custom string-matching evaluator technically "breaks" mid-stream; it cannot flag phrases like "i cannot help" until the entire sequence of those 3 words has finished printing. Thus, the safety flags logic and metadata counting must wait and execute only during the _final_ chunk of the stream!


## bonus - deploy