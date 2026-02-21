import time

SIMPLE_MODEL = "llama-3.1-8b-instant"
COMPLEX_MODEL = "llama-3.3-70b-versatile"


def route_query(query: str) -> dict:
    """
    Deterministic rule-based router to decide whether a query is simple or complex.
    Reasons to route to complex:
    1. Query > 20 words (long contexts often need more reasoning).
    2. Specific keyword presence: "compare", "why", "issue", "error", "difference", "troubleshoot", "complaint", "multiple".
    3. Has multiple questions (>1 question mark).
    """
    is_complex = False
    reasons = []

    words = query.strip().split()
    query_lower = query.lower()

    # Rule 1: Length
    if len(words) > 20:
        is_complex = True
        reasons.append("Length > 20 words")

    # Rule 2: Keyword presence
    complex_keywords = [
        "compare",
        "why",
        "issue",
        "error",
        "difference",
        "troubleshoot",
        "complaint",
        "multiple",
        "explain",
        "how come",  # Words that demand reasoning
    ]
    found_keywords = [kw for kw in complex_keywords if kw in query_lower]
    if found_keywords:
        is_complex = True
        reasons.append(f"Contains complex keywords: {found_keywords}")

    # Rule 3: Multiple Questions
    num_questions = query.count("?")
    if num_questions > 1:
        is_complex = True
        reasons.append("Contains multiple questions")

    # Final decision
    model = COMPLEX_MODEL if is_complex else SIMPLE_MODEL
    decision = "Complex" if is_complex else "Simple"

    return {"model": model, "classification": decision, "reasons": reasons}


def log_routing_decision(
    query, classification, model_used, tokens_input, tokens_output, latency_ms
):
    """
    Format specified by the prompt: { query, classification, model_used, tokens_input, tokens_output, latency_ms }
    """
    log_entry = {
        "query": query,
        "classification": classification,
        "model_used": model_used,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "latency_ms": latency_ms,
    }

    # Simple JSON lines logging
    import json

    with open("routing_logs.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return log_entry
