"""Starting languages (D37, D41): Registry Standard, the origin's language, one more."""

from new_vesper.content.loader import Content
from new_vesper.content.model import COMMON_TONGUE, ContentError


def origin_language_options(content: Content, origin_id: str) -> tuple[str, ...]:
    """The language an origin gives, or the ones a player picks from for it."""
    origin = content.origins[origin_id]
    return (origin.language,) if origin.language else origin.language_choices


def extra_language_options(content: Content, taken: tuple[str, ...]) -> tuple[str, ...]:
    """Any language not already spoken."""
    return tuple(lang for lang in content.languages if lang not in taken)


def starting_languages(
    content: Content, origin_id: str, origin_pick: str, extra: str
) -> tuple[str, ...]:
    """Check a new character's languages and return them in order."""
    if origin_id not in content.origins:
        raise ContentError(f"unknown origin {origin_id!r}")
    if origin_pick not in origin_language_options(content, origin_id):
        raise ContentError(f"{origin_pick!r} is not a language this origin gives")
    chosen = (COMMON_TONGUE, origin_pick)
    if extra not in extra_language_options(content, chosen):
        raise ContentError(f"{extra!r} is not an extra language this character can take")
    return (*chosen, extra)
