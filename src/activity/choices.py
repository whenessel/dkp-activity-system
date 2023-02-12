import enum

from django.db import models


__all__ = ('EventType', 'CapacityUnit', 'EventStatus', 'AttendanceType')


class EventType(models.TextChoices):
    CHAIN = 'CHAIN', 'чейн'
    ONCE = 'ONCE', 'разовый'
    AWAKENED = 'AWAKENED', 'пробужденный'
    TOI = 'TOI', 'ТОИ'
    VEORA = 'VEORA', 'веора'
    SIEGE = 'SIEGE', 'осада'
    CLUSTER = 'CLUSTER', 'кластер'
    CLAN = 'CLAN', 'клан'
    ALLIANCE = 'ALLIANCE', 'альянс'


class CapacityUnit(models.TextChoices):
    TIME = 'TIME', 'за минут(а)'
    THING = 'THING', 'за штук(а)'
    VISIT = 'VISIT', 'за визит(ы)'


class EventStatus(models.TextChoices):
    PENDING = 'PENDING', 'подготовка'
    STARTED = 'STARTED', 'запущено'
    FINISHED = 'FINISHED', 'завершено'
    CANCELED = 'CANCELED', 'остановлено'


class AttendanceType(models.TextChoices):
    FULL = 'FULL', 'присутствовал'
    PARTIAL = 'PARTIAL', 'опоздал'
    ABSENT = 'ABSENT', 'отсутствовал'
