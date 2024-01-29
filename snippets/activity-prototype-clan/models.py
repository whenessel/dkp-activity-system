import typing as t

from django.db import models

from .choices import *


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


class EventTemplate(models.Model):
    type = models.CharField(max_length=32, choices=EventType.choices)
    unit = models.CharField(max_length=32, choices=CapacityUnit.choices)
    capacity = models.IntegerField(default=0)
    cost = models.IntegerField(default=0)
    penalty = models.IntegerField(default=50)
    military = models.IntegerField(default=20)
    overnight = models.IntegerField(default=25)

    quantity = models.IntegerField(default=0)

    title = models.CharField(max_length=64, blank=False)
    description = models.TextField(default="", blank=True)

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

    type = models.CharField(max_length=32, choices=EventType.choices)
    unit = models.CharField(max_length=32, choices=CapacityUnit.choices)
    capacity = models.IntegerField(default=0)
    cost = models.IntegerField(default=0)
    penalty = models.IntegerField(default=0)
    military = models.IntegerField(default=0)
    overnight = models.IntegerField(default=0)

    title = models.CharField(max_length=64, blank=False)
    description = models.TextField(default="", blank=True)

    quantity = models.IntegerField(default=0)
    status = models.CharField(
        max_length=32, choices=EventStatus.choices, default=EventStatus.PENDING
    )

    is_military = models.BooleanField(default=False)
    is_overnight = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "-id",
        ]

    def _reward(self, attend_type: AttendanceType) -> int:
        reward = self.cost * float(self.quantity) / float(self.capacity)
        extra = float(0)
        if self.is_military:
            extra += float(self.military * reward) / 100
        if self.is_overnight:
            extra += float(self.overnight * reward) / 100
        reward += extra
        if attend_type == AttendanceType.PARTIAL:
            reward = reward * float(self.penalty / 100)
        reward = int(round(reward, 1))
        return reward

    @property
    def full_reward(self):
        return self._reward(attend_type=AttendanceType.FULL)

    @property
    def partial_reward(self):
        return self._reward(attend_type=AttendanceType.PARTIAL)


class EventAttendance(models.Model):
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="event_attendances"
    )

    member_id = models.BigIntegerField()
    member_name = models.CharField(max_length=255, blank=True)
    member_display_name = models.CharField(max_length=255, blank=True)

    reward = models.IntegerField(default=0)
    type = models.CharField(
        max_length=32, choices=AttendanceType.choices, default=AttendanceType.ABSENT
    )

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

    def compute_reward(self, partial_save=False) -> int:
        if self.type == AttendanceType.FULL:
            self.reward = self.event.full_reward
        if self.type == AttendanceType.PARTIAL:
            self.reward = self.event.partial_reward
        if partial_save:
            self.save(
                update_fields=[
                    "reward",
                ]
            )
        return self.reward
