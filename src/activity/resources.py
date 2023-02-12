from django.db.models import *
from django.contrib.postgres.aggregates import *
from import_export import resources, widgets, fields
from collections import namedtuple
from activity.models import *


def convert(dictionary):
    return namedtuple('GenericDict', dictionary.keys())(**dictionary)


class CommonEventAttendanceResource(resources.ModelResource):
    member_id = fields.Field(attribute='member_id', column_name='member_id', widget=widgets.IntegerWidget())
    member_names = fields.Field(attribute='member_names', column_name='member_names')
    total = fields.Field(attribute='total', column_name='total', widget=widgets.IntegerWidget())
    chain = fields.Field(attribute='chain', column_name='chain', widget=widgets.IntegerWidget())
    once = fields.Field(attribute='once', column_name='once', widget=widgets.IntegerWidget())
    awakened = fields.Field(attribute='awakened', column_name='awakened', widget=widgets.IntegerWidget())
    toi = fields.Field(attribute='toi', column_name='toi', widget=widgets.IntegerWidget())
    veora = fields.Field(attribute='veora', column_name='veora', widget=widgets.IntegerWidget())
    siege = fields.Field(attribute='siege', column_name='siege', widget=widgets.IntegerWidget())
    cluster = fields.Field(attribute='cluster', column_name='cluster', widget=widgets.IntegerWidget())
    clan = fields.Field(attribute='clan', column_name='clan', widget=widgets.IntegerWidget())
    alliance = fields.Field(attribute='alliance', column_name='alliance', widget=widgets.IntegerWidget())
    total_reward = fields.Field(attribute='total_reward', column_name='total_reward', widget=widgets.IntegerWidget())
    once_by_qty = fields.Field(attribute='once_by_qty', column_name='once_by_qty', widget=widgets.IntegerWidget())
    awakened_by_qty = fields.Field(attribute='awakened_by_qty', column_name='awakened_by_qty', widget=widgets.IntegerWidget())

    class Meta:
        model = EventAttendance
        fields = ('member_id', 'member_names', 'total',
              'chain', 'once', 'awakened', 'toi',
              'veora', 'siege', 'cluster', 'clan',
              'alliance', 'total_reward', 'once_by_qty', 'awakened_by_qty')
        export_order = ('member_id', 'member_names', 'total',
              'chain', 'once', 'awakened', 'toi',
              'veora', 'siege', 'cluster', 'clan',
              'alliance', 'total_reward', 'once_by_qty', 'awakened_by_qty')

    def export(self, queryset=None, *args, **kwargs):
        if queryset is None:
            queryset = self.get_queryset()

        queryset = queryset \
            .values('member_id') \
            .order_by('member_id') \
            .annotate(member_names=StringAgg('member_display_name', ',', distinct=True)) \
            .values('member_id', 'member_names') \
            .annotate(total=Count('event_id', distinct=True),
                      chain=Count('event_id', distinct=True, filter=Q(event__type=EventType.CHAIN)),
                      once=Count('event_id', distinct=True, filter=Q(event__type=EventType.ONCE)),
                      awakened=Count('event_id', distinct=True, filter=Q(event__type=EventType.AWAKENED)),
                      toi=Count('event_id', distinct=True, filter=Q(event__type=EventType.TOI)),
                      veora=Count('event_id', distinct=True, filter=Q(event__type=EventType.VEORA)),
                      siege=Count('event_id', distinct=True, filter=Q(event__type=EventType.SIEGE)),
                      cluster=Count('event_id', distinct=True, filter=Q(event__type=EventType.CLUSTER)),
                      clan=Count('event_id', distinct=True, filter=Q(event__type=EventType.CLAN)),
                      alliance=Count('event_id', distinct=True, filter=Q(event__type=EventType.ALLIANCE)),
                      total_reward=Sum('reward'),
                      once_by_qty=Sum('event__quantity', filter=Q(event__type=EventType.ONCE), default=0),
                      awakened_by_qty=Sum('event__quantity', filter=Q(event__type=EventType.AWAKENED), default=0),
                      ) \
            .values('member_id', 'member_names', 'total',
                    'chain', 'once', 'awakened', 'toi',
                    'veora', 'siege', 'cluster', 'clan',
                    'alliance', 'total_reward', 'once_by_qty', 'awakened_by_qty')

        queryset = list(map(convert, queryset))
        return super().export(queryset=queryset)

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(event__status=EventStatus.FINISHED)
        return queryset
