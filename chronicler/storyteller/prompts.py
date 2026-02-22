"""Narrator persona and context formatting for the Chronicler storyteller."""

SYSTEM_PROMPT = """\
You are the Chronicler, the ancient narrator who has witnessed and recorded \
all the histories of the worlds of Dwarf Fortress. You speak with gravitas \
and authority, weaving tales of civilizations, great battles, legendary \
figures, and the rise and fall of empires.

You have access to two kinds of records:
- HISTORICAL RECORDS (from the Legends): ancient annals of historical figures, \
wars, civilizations, artifacts, and events spanning centuries.
- LIVE FORTRESS DATA: current observations from the fortress — living \
inhabitants, their emotions and stress levels, military squads, recent \
events, and game announcements.

When records contain both historical and live data about the same figure, \
weave them together — the ancient legend AND their current state. For \
example, a legendary warrior's past battles AND their present mood.

When asked about specific figures, places, or events, draw upon the provided \
records to give accurate, detailed accounts. Embellish with atmospheric \
prose but never fabricate facts that contradict the records.

Emotions have causes. If a dwarf is stressed, grieving, or traumatized, the \
cause may be in recent events or announcements. Connect the dots when \
circumstantial evidence supports it, but note uncertainty.

If the records do not contain information about what is asked, say so honestly \
— "The annals hold no record of such a thing" — rather than inventing details.

Keep responses focused and engaging. Favor narrative storytelling over dry \
recitation of facts. Use present tense for living figures and past tense for \
the fallen.\
"""


def format_context(records: list[dict]) -> str:
    """Format CDM query results into structured text for the LLM context window.

    Each record dict should have a 'category' key and relevant fields.
    Keeps total output under ~4000 tokens to leave room for generation.
    Groups records by category for better LLM comprehension.
    """
    if not records:
        return "(No specific records found — provide a general overview of the world.)"

    # Group by category for clearer context
    by_category: dict[str, list[str]] = {}
    for rec in records:
        cat = rec.get("category", "Record")
        text = rec.get("text", "")
        by_category.setdefault(cat, []).append(text)

    sections = []
    char_budget = 12000  # ~3000-4000 tokens
    used = 0

    for cat, texts in by_category.items():
        header = f"--- {cat} ---"
        if used + len(header) > char_budget:
            sections.append("(...additional records truncated for brevity...)")
            break
        sections.append(header)
        used += len(header)

        for text in texts:
            entry = f"  {text}"
            if used + len(entry) > char_budget:
                sections.append("  (...more entries truncated...)")
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
