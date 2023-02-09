from django.db import models
import enum


class ExtraLabelChoicesMeta(enum.EnumMeta):

    def __new__(metacls, cls, bases, classdict, **kwds):
        cls = super().__new__(metacls, cls, bases, classdict, **kwds)
        cls._emoji_map_ = {}
        for member in cls:
            cls._emoji_map_[member.emoji] = member
        return cls

    def __getitem__(cls, name):
        try_list = [
            (cls._member_map_, KeyError),
            (cls._emoji_map_, KeyError),
        ]
        result = None
        for action, ex in try_list:
            try:
                result = action[name]
                break
            except ex:
                continue
        if not result:
            raise KeyError(name)
        return result

    def __contains__(cls, member):
        if not isinstance(member, enum.Enum):
            # Allow non-enums to match against member values.
            return any(x.value == member for x in cls)
        return super().__contains__(member)

    @property
    def names(cls):
        empty = ["__empty__"] if hasattr(cls, "__empty__") else []
        return empty + [member.name for member in cls]

    @property
    def choices(cls):
        empty = [(None, cls.__empty__)] if hasattr(cls, "__empty__") else []
        return empty + [(member.value, member.label) for member in cls]

    @property
    def labels(cls):
        return [label for _, label in cls.choices]

    @property
    def values(cls):
        return [value for value, _ in cls.choices]

    @property
    def emojis(cls):
        empty = ["__empty__"] if hasattr(cls, "__empty__") else []
        return empty + [member.emoji for member in cls]


class EmojiChoices(str, enum.Enum, metaclass=ExtraLabelChoicesMeta):
    emoji: str

    def __new__(cls, value: str, label: str, emoji: str = ""):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.label = label
        obj.emoji = emoji
        return obj

