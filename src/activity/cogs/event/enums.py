from __future__ import annotations
import enum

from enum_properties import EnumProperties, p, s
from activity.models import AttendanceType


class EmojiEnum:

    @classmethod
    def to_dict(cls):
        """Returns a dictionary representation of the enum."""
        return {e.name: e.value for e in cls}

    @classmethod
    def keys(cls):
        """Returns a list of all the enum keys."""
        return cls._member_names_

    @classmethod
    def values(cls):
        """Returns a list of all the enum values."""
        return list(cls._value2member_map_.keys())

    @classmethod
    def emojis(cls):
        """Returns a list of all the enum emojis."""
        return list([e.emoji for e in cls])

    @classmethod
    def types(cls):
        """Returns a list of all the enum emojis."""
        return list([e.type for e in cls])


class MemberReactions(EmojiEnum, EnumProperties, s('emoji'), s('attend_type', case_fold=True)):
    FULL = enum.auto(), "✅", AttendanceType.FULL
    PARTIAL = enum.auto(), "⏲️", AttendanceType.PARTIAL


class ModeratorReactions(EmojiEnum, EnumProperties, s('emoji')):
    IS_MILITARY = enum.auto(), "⚔️"
    IS_OVERNIGHT = enum.auto(), "🌃"
