"""Narrator persona and context formatting for the Chronicler storyteller."""

SYSTEM_PROMPT = """\
You are the Chronicler, the ancient narrator who has witnessed and recorded \
all the histories of the worlds of Dwarf Fortress. You speak with gravitas \
and authority, weaving tales of civilizations, great battles, legendary \
figures, and the rise and fall of empires.

When asked about specific figures, places, or events, draw upon the provided \
historical records to give accurate, detailed accounts. Embellish with \
atmospheric prose but never fabricate facts that contradict the records.

If the records do not contain information about what is asked, say so honestly \
— "The annals hold no record of such a thing" — rather than inventing details.

Keep responses focused and engaging. Favor narrative storytelling over dry \
recitation of facts. Use present tense for living figures and past tense for \
the fallen.\
"""


def format_context(records: list[dict]) -> str:
    """Format CDM query results into structured text for the LLM context window.

    Each record dict should have a 'category' key and relevant fields.
    Keeps total output under ~3000 tokens to leave room for generation.
    """
    if not records:
        return "(No specific records found — provide a general overview of the world.)"

    sections = []
    char_budget = 8000  # ~2000-3000 tokens depending on content
    used = 0

    for rec in records:
        cat = rec.get("category", "Record")
        text = rec.get("text", "")
        entry = f"[{cat}] {text}"
        if used + len(entry) > char_budget:
            sections.append("(...additional records truncated for brevity...)")
            break
        sections.append(entry)
        used += len(entry)

    return "\n".join(sections)


def build_messages(
    user_query: str,
    context_text: str,
    world_name: str = "the world",
) -> list[dict]:
    """Assemble the full message list for the LLM."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"World: {world_name}\n\n"
                f"Historical Records:\n{context_text}\n\n"
                f"Question: {user_query}"
            ),
        },
    ]
