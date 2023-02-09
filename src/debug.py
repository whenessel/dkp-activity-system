import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'system.settings')
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'True')
import django
django.setup()



# TODO: EXPORT TO XLSX
# from activity.models import *
# from import_export import resources
# from import_export import widgets
# from import_export import fields
#
#
# class EventAttendanceResource(resources.ModelResource):
#
#     date = fields.Field(
#         attribute="event__created",
#         column_name="created",
#         widget=widgets.DateTimeWidget(format="%Y-%m-%d %H:%M:%S"),
#     )
#     class Meta:
#         model = EventAttendance
#         fields = ('member_id', )
#
#
# res = EventAttendanceResource()
# data = res.export()
#
# print(data.csv)
#
# f = open("./export.xlsx", "wb+")
# f.write(data.xlsx)
# f.close()
# print("...")

from django.db.models import *
from django.db.models.functions import *
#
#
# EventAttendance.objects.all().annotate(member_names=)