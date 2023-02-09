import enum

from django.db import models


__all__ = ("EventType", "CapacityUnit", "EventStatus", "AttendanceType")


class EventType(models.TextChoices):
    CHAIN = "CHAIN", "чейн"
    ONCE = "ONCE", "разовый"
    AWAKENED = "AWAKENED", "пробужденный"
    TOI = "TOI", "ТОИ"
    VEORA = "VEORA", "веора"
    SIEGE = "SIEGE", 'осада'
    CLUSTER = "CLUSTER", "кластер"
    CLAN = "CLAN", "клан"
    ALLIANCE = "ALLIANCE", "альянс"
    UNKNOWN = "UNKNOWN", "не известно"


class CapacityUnit(models.TextChoices):
    TIME = "TIME", "за минут(а)"
    THING = "THING", "за штук(а)"
    VISIT = "VISIT", "за визит(ы)"
    UNKNOWN = "UNKNOWN", "не известно"


class EventStatus(models.TextChoices):
    PENDING = "PENDING", "подготовка"
    STARTED = "STARTED", "запущено"
    FINISHED = "FINISHED", "завершено"
    CANCELED = "CANCELED", "остановлено"
    UNKNOWN = "UNKNOWN", "не известно"


class AttendanceType(models.TextChoices):
    FULL = "FULL", "присутствовал"
    PARTIAL = "PARTIAL", "опоздал"
    ABSENT = "ABSENT", "отсутствовал"
    UNKNOWN = "UNKNOWN", "не известно"
