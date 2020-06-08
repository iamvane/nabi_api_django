import datetime
import pytz
from operator import itemgetter

from rest_framework import status, views
from rest_framework.response import Response


class TimezoneListView(views.APIView):

    def get(self, request):
        tz_positive_offset = []
        tz_negative_offset = []
        for item in pytz.all_timezones:
            if item[:3] == 'Etc':
                continue
            offset = datetime.datetime.now(pytz.timezone(item)).strftime('%z')
            if offset[0] == '-':
                tz_negative_offset.append({'name': item, 'offset': offset})
            else:
                tz_positive_offset.append({'name': item, 'offset': offset})
        tz_list = sorted(tz_negative_offset, key=itemgetter('offset'), reverse=True)
        tz_list.append(sorted(tz_positive_offset, key=itemgetter('offset')))
        return Response(tz_list, status=status.HTTP_200_OK)
