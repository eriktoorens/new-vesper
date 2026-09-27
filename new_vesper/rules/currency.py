"""Currency (D18): 1 glamour = 10 glims = 100 glitter. Amounts are whole glitter."""

from new_vesper.rules.errors import RulesError, require_int

GLITTER_PER_GLIM = 10
GLIMS_PER_GLAMOUR = 10
GLITTER_PER_GLAMOUR = GLITTER_PER_GLIM * GLIMS_PER_GLAMOUR
# New characters start with 5 glims.
STARTING_GLITTER = 5 * GLITTER_PER_GLIM


def format_glitter(amount: int) -> str:
    """Show an amount in denominations, largest first: '1 glamour, 2 glims, 5 glitter'."""
    total = require_int(amount, "amount")
    if total < 0:
        raise RulesError("an amount of currency cannot be negative")
    glamour, rest = divmod(total, GLITTER_PER_GLAMOUR)
    glims, glitter = divmod(rest, GLITTER_PER_GLIM)
    parts = [
        f"{glamour} glamour" if glamour else "",
        f"{glims} glim{'s' if glims != 1 else ''}" if glims else "",
        f"{glitter} glitter" if glitter else "",
    ]
    return ", ".join(p for p in parts if p) or "0 glitter"
