"""Advancement triggers (D4): exactly four, 1 XP each, once per character per scene."""

from enum import StrEnum

from new_vesper.rules.errors import parse_enum


class Trigger(StrEnum):
    PROTECT_SOMEONE = "protect_someone"
    MAKE_A_SACRIFICE = "make_a_sacrifice"
    KEEP_A_HARD_PROMISE = "keep_a_hard_promise"
    RAISE_LIGHT = "raise_light"


XP_PER_TRIGGER = 1


def parse_trigger(value: object) -> Trigger:
    return parse_enum(Trigger, value, "trigger")
