from django.db import models

from .choices import AttendanceServer, EventStatus
from .managers import EventManager


class EventChannel(models.Model):
    guild_id = models.BigIntegerField()
    role_id = models.BigIntegerField(null=True)
    channel_id = models.BigIntegerField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "-id",
        ]


class EventModerator(models.Model):
    guild_id = models.BigIntegerField()
    role_id = models.BigIntegerField(null=True)
    channel_id = models.BigIntegerField(null=True)
    member_id = models.BigIntegerField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "-id",
        ]


class Event(models.Model):
    guild_id = models.BigIntegerField()
    role_id = models.BigIntegerField(null=True)
    channel_id = models.BigIntegerField(null=True)
    message_id = models.BigIntegerField(null=True)

    member_id = models.BigIntegerField()
    member_name = models.CharField(max_length=255, default="", blank=True)
    member_display_name = models.CharField(max_length=255, default="", blank=True)

    title = models.CharField(max_length=64, blank=False)
    description = models.TextField(default="", blank=True)

    status = models.CharField(
        max_length=32, choices=EventStatus.choices, default=EventStatus.PENDING
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = EventManager()

    class Meta:
        ordering = [
            "-id",
        ]


class EventAttendance(models.Model):
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="event_attendances"
    )

    member_id = models.BigIntegerField()
    member_name = models.CharField(max_length=255, blank=True)
    member_display_name = models.CharField(max_length=255, blank=True)

    server = models.CharField(max_length=32, choices=AttendanceServer.choices)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "-id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["event", "member_id"], name="event-attendance-member"
            ),
        ]
