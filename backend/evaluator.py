def evaluate_response(
    response_text: str, context_provided: bool = True
) -> tuple[bool, list[str]]:
    """
    Evaluates the LLM output to flag potentially unreliable outputs.
    Returns (is_passed, list_of_flags)
    """
    response_lower = response_text.lower()
    flags = []

    # Check 1: No-context responses
    # If the LLM generates a response but says it doesn't have enough context, or if no context was provided.
    no_context_phrases = [
        "based on the information provided, i cannot",
        "the provided documents do not contain",
        "i don't have enough information",
        "i don't have enough context",
        "i cannot answer this based on the provided text",
    ]
    if not context_provided:
        # If no RAG chunks were retrieved, but it still answered fully as a chatbot, it's hallucinating.
        flags.append(
            "No context was retrieved for this query, so the response may be hallucinated."
        )

    for phrase in no_context_phrases:
        if phrase in response_lower:
            flags.append("Model indicates lack of context to answer the question.")
            break

    # Check 2: Refusals or non-answers
    refusal_phrases = [
        "i cannot fulfill this request",
        "i'm sorry, but i cannot",
        "as an ai language model",
        "i am an ai language model",
        "i am unable to provide",
    ]
    for phrase in refusal_phrases:
        if phrase in response_lower:
            flags.append("Response contains a refusal or non-answer pattern.")
            break

    # Check 3: Domain-specific check
    # Clearpath is a project management tool. Let's make sure the AI doesn't recommend
    # using competitor products which might be ingrained in its pre-training related to PM tools.
    competitors = ["jira", "asana", "monday.com", "trello", "clickup"]
    for comp in competitors:
        if comp in response_lower:
            flags.append(
                f"Domain Check Failed: Output mentions competitor product '{comp}'."
            )
            break

    # Also, Clearpath does not have real-time human chat support, so if the AI
    # promises "I will transfer you to a human agent", we should flag it as a hallucination.
    if (
        "transfer you to a human" in response_lower
        or "transferring you to an agent" in response_lower
    ):
        flags.append(
            "Domain Check Failed: Pledged human transfer, which is unsupported."
        )

    passed = len(flags) == 0
    return passed, flags
