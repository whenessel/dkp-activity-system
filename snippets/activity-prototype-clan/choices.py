import enum

from django.db import models

__all__ = ("EventType", "CapacityUnit", "EventStatus", "AttendanceType")


class EventType(models.TextChoices):
    CHAIN = "CHAIN", "чейн"
    ONCE = "ONCE", "разовый"
    AWAKENED = "AWAKENED", "пробужденный"
    TOI = "TOI", "ТОИ"
    VEORA = "VEORA", "веора"
    SIEGE = "SIEGE", "осада"
    CLUSTER = "CLUSTER", "кластер"
    CLAN = "CLAN", "клан"
    ALLIANCE = "ALLIANCE", "альянс"


class CapacityUnit(models.TextChoices):
    TIME = "TIME", "за минут(а)"
    THING = "THING", "за штук(а)"
    VISIT = "VISIT", "за визит(ы)"


class EventStatus(models.TextChoices):
    PENDING = "PENDING", "подготовка"
    STARTED = "STARTED", "запущено"
    FINISHED = "FINISHED", "завершено"
    CANCELED = "CANCELED", "остановлено"


class AttendanceType(models.TextChoices):
    FULL = "FULL", "присутствовал"
    PARTIAL = "PARTIAL", "опоздал"
    ABSENT = "ABSENT", "отсутствовал"


class AttendanceServer(models.TextChoices):
    ONE = "Server 1", "Сервер 1"
    TWO = "Server 2", "Сервер 2"
    THREE = "Server 3", "Сервер 3"
    FOUR = "Server 4", "Сервер 4"
    FIVE = "Server 5", "Сервер 5"
    SIX = "Server 6", "Сервер 6"


class AttendanceServer(models.TextChoices):
    ONE = "Cluster 1", "Сервер 1"
    TWO = "Cluster 2", "Сервер 2"
    THREE = "Cluster 3", "Сервер 3"
    FOUR = "Cluster 4", "Сервер 4"
    FIVE = "Cluster 5", "Сервер 5"
    SIX = "Cluster 6", "Сервер 6"
