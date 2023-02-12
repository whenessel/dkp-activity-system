import os
import sys
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'system.settings')
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'True')
import django
django.setup()

from django.db.models import *
from django.contrib.postgres.aggregates import *
from import_export import resources, widgets, fields
from collections import namedtuple
from activity.models import *
from activity.resources import *


qs = EventAttendance.objects.filter(event__created__gt=datetime.now() - timedelta(hours=3))
res = EventAttendanceResource().export(queryset=qs)
print(res.csv)
# f = open("./export3.xlsx", "wb+")
# f.write(res.xlsx)
# f.close()
