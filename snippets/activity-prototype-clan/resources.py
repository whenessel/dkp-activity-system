from django.db.models import *
from django.contrib.postgres.aggregates import *
from import_export import resources, widgets, fields
from collections import namedtuple
from activity.models import *


def convert(dictionary):
    return namedtuple("GenericDict", dictionary.keys())(**dictionary)


class CommonEventAttendanceResource(resources.ModelResource):
    member_id = fields.Field(
        attribute="member_id", column_name="member_id", widget=widgets.IntegerWidget()
    )
    member_names = fields.Field(attribute="member_names", column_name="member_names")
    server_one = fields.Field(
        attribute="server_one", column_name="server_one", widget=widgets.IntegerWidget()
    )
    server_two = fields.Field(
        attribute="server_two", column_name="server_two", widget=widgets.IntegerWidget()
    )
    server_three = fields.Field(
        attribute="server_three",
        column_name="server_three",
        widget=widgets.IntegerWidget(),
    )
    server_four = fields.Field(
        attribute="server_four",
        column_name="server_four",
        widget=widgets.IntegerWidget(),
    )
    server_five = fields.Field(
        attribute="server_five",
        column_name="server_five",
        widget=widgets.IntegerWidget(),
    )
    server_six = fields.Field(
        attribute="server_six", column_name="server_six", widget=widgets.IntegerWidget()
    )

    class Meta:
        model = EventAttendance
        fields = (
            "member_id",
            "member_names",
            "server_one",
            "server_two",
            "server_three",
            "server_four",
            "server_five",
            "server_six",
        )
        export_order = (
            "member_id",
            "member_names",
            "server_one",
            "server_two",
            "server_three",
            "server_four",
            "server_five",
            "server_six",
        )

    def export(self, queryset=None, *args, **kwargs):
        if queryset is None:
            queryset = self.get_queryset()

        queryset = (
            queryset.values("member_id")
            .order_by("member_id")
            .annotate(member_names=StringAgg("member_display_name", ",", distinct=True))
            .values("member_id", "member_names")
            .annotate(
                server_one=Count(
                    "event_id",
                    distinct=True,
                    filter=Q(server=AttendanceServer.ONE.value),
                ),
                server_two=Count(
                    "event_id",
                    distinct=True,
                    filter=Q(server=AttendanceServer.TWO.value),
                ),
                server_three=Count(
                    "event_id",
                    distinct=True,
                    filter=Q(server=AttendanceServer.THREE.value),
                ),
                server_four=Count(
                    "event_id",
                    distinct=True,
                    filter=Q(server=AttendanceServer.FOUR.value),
                ),
                server_five=Count(
                    "event_id",
                    distinct=True,
                    filter=Q(server=AttendanceServer.FIVE.value),
                ),
                server_six=Count(
                    "event_id",
                    distinct=True,
                    filter=Q(server=AttendanceServer.SIX.value),
                ),
            )
            .values(
                "member_id",
                "member_names",
                "server_one",
                "server_two",
                "server_three",
                "server_four",
                "server_five",
                "server_six",
            )
        )

        queryset = list(map(convert, queryset))
        return super().export(queryset=queryset)

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(event__status=EventStatus.FINISHED)
        return queryset
