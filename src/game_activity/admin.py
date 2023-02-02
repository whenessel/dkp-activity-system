from django.contrib import admin


from .models import *


@admin.register(GameEventTemplate)
class GameEventTemplateAdmin(admin.ModelAdmin):
    list_display = ['id', 'label', 'event_type',
                    'cost', 'capacity', 'capacity_unit',
                    'lateness_percent', 'nightly_percent']


@admin.register(GameEvent)
class GameEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'author_display_name', 'message_id', 'event_type', 'state',
                    'title',  'cost', 'capacity', 'capacity_unit',
                    'quantity', 'lateness_percent', 'nightly_percent']


@admin.register(GameEventUser)
class GameEventUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'event_message_id', 'user_display_name', 'reward', 'state']

    @admin.display(description='Event ID', ordering='event__message_id')
    def event_message_id(self, obj):
        return obj.event.message_id
