import enum

from django.db import models

__all__ = ("EventStatus", "AttendanceServer")


class EventStatus(models.TextChoices):
    PENDING = "PENDING", "подготовка"
    STARTED = "STARTED", "запущено"
    FINISHED = "FINISHED", "завершено"
    CANCELED = "CANCELED", "остановлено"
    DELETED = "DELETED", "удалено"


class AttendanceServer(models.TextChoices):
    ONE = "Server 1", "Сервер 1"
    TWO = "Server 2", "Сервер 2"
    THREE = "Server 3", "Сервер 3"
    FOUR = "Server 4", "Сервер 4"
    FIVE = "Server 5", "Сервер 5"
    SIX = "Server 6", "Сервер 6"
