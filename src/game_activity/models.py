from django.db import models


class GameEventType(models.TextChoices):
    CHAIN = 'CHAIN'
    ONCE = 'ONCE'
    AWAKENED = 'AWAKENED'
    TOI = 'TOI'
    VEORA = 'VEORA'
    SIEGE = 'SIEGE'
    INTERCLUSTER = 'INTERCLUSTER'
    CLAN = 'CLAN'
    ALLY = 'ALLY'


class GameEventCapacityUnit(models.TextChoices):
    MINUTE = 'MINUTE'
    THING = 'THING'
    VISIT = 'VISIT'


class GameEventState(models.TextChoices):
    STARTED = 'STARTED'
    FINISHED = 'FINISHED'
    CANCELED = 'CANCELED'


class GameEventUserState(models.TextChoices):
    FULL = 'FULL'
    LATE = 'LATE'
    NONE = 'NONE'


class GameEventTemplate(models.Model):
    label = models.CharField(max_length=64, blank=False, unique=True)
    title = models.CharField(max_length=64, blank=False)
    description = models.CharField(max_length=255, default='', blank=True)
    event_type = models.CharField(max_length=32, choices=GameEventType.choices)
    cost = models.IntegerField(default=0)
    capacity = models.IntegerField(default=0)
    capacity_unit = models.CharField(max_length=32, choices=GameEventCapacityUnit.choices)

    lateness_percent = models.IntegerField(default=80)
    nightly_percent = models.IntegerField(default=25)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class GameEvent(models.Model):

    guild_id = models.BigIntegerField(null=True)
    channel_id = models.BigIntegerField(null=True)

    message_id = models.BigIntegerField(unique=True)

    author_id = models.BigIntegerField()
    author_name = models.CharField(max_length=255, blank=True)
    author_display_name = models.CharField(max_length=255, blank=True)

    state = models.CharField(max_length=32, choices=GameEventState.choices, default=GameEventState.STARTED)

    title = models.CharField(max_length=64, blank=False)
    description = models.CharField(max_length=255, default='', blank=True)

    event_type = models.CharField(max_length=32, choices=GameEventType.choices)

    cost = models.IntegerField(default=0)
    capacity = models.IntegerField(default=0)
    capacity_unit = models.CharField(max_length=32, choices=GameEventCapacityUnit.choices)

    lateness_percent = models.IntegerField(default=80)
    nightly_percent = models.IntegerField(default=25)

    quantity = models.IntegerField(default=None, null=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class GameEventUser(models.Model):

    event = models.ForeignKey(GameEvent, on_delete=models.CASCADE, related_name="users")

    user_id = models.BigIntegerField()
    user_name = models.CharField(max_length=255, blank=True)
    user_display_name = models.CharField(max_length=255, blank=True)

    state = models.CharField(max_length=32, choices=GameEventUserState.choices, default=GameEventUserState.NONE)

    reward = models.IntegerField(default=0)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
