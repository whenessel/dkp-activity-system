from django.contrib import admin

from .models import *

# from import_export.admin import ExportActionModelAdmin
# from .resources import CommonEventAttendanceResource


@admin.register(EventChannel)
class EventChannelAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "guild_id",
        "channel_id",
        "created",
    ]


@admin.register(EventModerator)
class EventModeratorAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "guild_id",
        "member_id",
        "created",
    ]


@admin.register(EventTemplate)
class EventTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "type",
        "title",
        "cost",
        "capacity",
        "unit",
        "quantity",
        "penalty",
        "military",
        "overnight",
        "created",
    ]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "type",
        "title",
        "cost",
        "capacity",
        "unit",
        "quantity",
        "penalty",
        "military",
        "overnight",
        "member_display_name",
        "status",
        "is_military",
        "is_overnight",
        "created",
    ]
    list_filter = ["type", "status", "is_military", "is_overnight"]
    date_hierarchy = "created"


@admin.register(EventAttendance)
class EventAttendanceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "event_id",
        "member_id",
        "member_display_name",
        "type",
        "reward",
        "created",
    ]
    list_filter = [
        "event__type",
        "event__status",
        "event__is_military",
        "event__is_overnight",
    ]
    date_hierarchy = "created"

    # TODO: Tmp disable
    # admin view class - ExportActionModelAdmin
    # resource_classes = [CommonEventAttendanceResource]
