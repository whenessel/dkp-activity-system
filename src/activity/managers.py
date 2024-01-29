from django.db import models

from .choices import EventStatus


class EventManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(status=EventStatus.DELETED)
