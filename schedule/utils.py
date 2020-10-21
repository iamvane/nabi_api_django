from django.utils import timezone


def compose_schedule_data(instructor, this_date, orig_data):
    if orig_data:
        # first, order received schedule data
        data = sorted(orig_data, key=lambda item: item.get('beginTime'))
    else:
        data = [{'beginTime': '08:00', 'endTime': '20:00', 'available': False}]
    return data
