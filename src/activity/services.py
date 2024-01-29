import datetime
import io
import typing as t

import discord
from django.utils import timezone

from .choices import EventStatus
from .models import EventAttendance
from .resources import CommonEventAttendanceResource


class ActivityStatisticService(object):
    @staticmethod
    def get_statistics_by_date_range(
        start_date: datetime.datetime, end_date: datetime.datetime
    ) -> discord.File:
        event_filter = {
            "event__created__gte": timezone.make_aware(start_date),
            "event__created__lte": timezone.make_aware(end_date),
            "event__status": EventStatus.FINISHED,
        }

        filename = f"report_by_date_range_{start_date.date()}_{end_date.date()}.xlsx"

        queryset = EventAttendance.objects.filter(**event_filter)
        resource = CommonEventAttendanceResource()
        result = resource.export(queryset=queryset)
        statistic_content = io.BytesIO(result.xlsx)
        statistic_file = discord.File(
            statistic_content,
            filename=filename,
            description=f"Статистика за период "
            f"с {start_date.date()} по {end_date.date()}",
        )
        return statistic_file

    @staticmethod
    def get_statistics_by_event_range(start_id: int, end_id: int) -> discord.File:
        event_filter = {
            "event__id__gte": start_id,
            "event__id__lte": end_id,
            "event__status": EventStatus.FINISHED,
        }

        filename = f"report_by_event_range_{start_id}_{end_id}.xlsx"

        queryset = EventAttendance.objects.filter(**event_filter)
        resource = CommonEventAttendanceResource()
        result = resource.export(queryset=queryset)
        statistic_content = io.BytesIO(result.xlsx)
        statistic_file = discord.File(
            statistic_content,
            filename=filename,
            description=f"Статистика за события с {start_id} по {end_id}",
        )
        return statistic_file

    @staticmethod
    def get_statistics_by_event_list(event_ids: t.List[int]) -> discord.File:
        event_filter = {
            "event__id__in": event_ids,
            "event__status": EventStatus.FINISHED,
        }
        event_ids_str = "_".join([str(x) for x in event_ids])
        filename = f"report_by_event_list_{event_ids_str}.xlsx"

        queryset = EventAttendance.objects.filter(**event_filter)
        resource = CommonEventAttendanceResource()
        result = resource.export(queryset=queryset)
        statistic_content = io.BytesIO(result.xlsx)
        statistic_file = discord.File(
            statistic_content,
            filename=filename,
            description=f"Статистика по событиям с {event_ids_str}",
        )
        return statistic_file
