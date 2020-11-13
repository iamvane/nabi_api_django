from django.utils import timezone

from lesson.utils import get_date_time_from_datetime_timezone


def get_end_time_lesson(begin_time):
    """Return end_time for a lesson, calculating from begin_time
    :type begin_time: string, format HH:MM
    :return : string, format HH:MM"""
    hour, minutes = begin_time.split(':')
    dt = timezone.datetime(2020, 1, 1, int(hour), int(minutes), 0) + timezone.timedelta(minutes=30)
    return dt.strftime('%H:%M')


def compose_schedule_data(orig_data, lessons_qs, time_zone, this_date_str):
    res_data = {'available': []}
    if orig_data:
        # first, order received schedule data
        av_list = sorted(orig_data, key=lambda item: item.get('beginTime'))
    else:
        av_list = []
    res_data['lessons'] = []
    for item in lessons_qs.all():
        date_str, time_str = get_date_time_from_datetime_timezone(item.get('scheduled_datetime'), time_zone)
        if date_str != this_date_str:
            continue
        else:
            res_data['lessons'].append({'id': item.get('id'), 'time': time_str})
    lesson_ind = 0
    qty_lesson = len(res_data['lessons'])
    for item in av_list:
        begin_time = item.get('beginTime')
        end_time = item.get('endTime')
        if lesson_ind < qty_lesson:
            lesson_begin_time = res_data['lessons'][lesson_ind].get('time')
            lesson_end_time = get_end_time_lesson(lesson_begin_time)
        else:
            res_data['available'].append({'beginTime': begin_time, 'endTime': end_time})
            continue

        # walk on lessons until reach one with some hour coincidence; case 1 in documentation
        while lesson_ind < qty_lesson and lesson_end_time <= begin_time:
            lesson_ind += 1
            if lesson_ind < qty_lesson:
                lesson_begin_time = res_data['lessons'][lesson_ind].get('time')
                lesson_end_time = get_end_time_lesson(lesson_begin_time)
        if lesson_ind == qty_lesson:
            res_data['available'].append({'beginTime': begin_time, 'endTime': end_time})
            continue

        # Here, there is some lesson to analyze
        # cases where lesson ends before availability end; cases 2, 3, 4 in documentation
        while lesson_ind < qty_lesson and lesson_end_time < end_time:
            if lesson_begin_time > begin_time:   # case 4 in documentation
                res_data['available'].append({'beginTime': begin_time, 'endTime': lesson_begin_time})
            begin_time = lesson_end_time
            lesson_ind += 1
            if lesson_ind < qty_lesson:
                lesson_begin_time = res_data['lessons'][lesson_ind].get('time')
                lesson_end_time = get_end_time_lesson(lesson_begin_time)

        if lesson_ind < qty_lesson:
            if lesson_end_time == end_time and lesson_begin_time <= begin_time:   # case 9 in documentation
                lesson_ind += 1   # get begin, end times of lesson is made at cycle beginning
            elif lesson_end_time > end_time and lesson_begin_time <= begin_time:   # case 8 in documentation
                pass
            elif lesson_begin_time < end_time:   # cases 5, 6 in documentation
                res_data['available'].append({'beginTime': begin_time, 'endTime': lesson_begin_time})
                if lesson_end_time == end_time:   # case 5 in documentation
                    lesson_ind += 1   # get begin, end times of lesson is made at cycle beginning
            else:   # case 7 in documentation
                res_data['available'].append({'beginTime': begin_time, 'endTime': end_time})
        else:
            res_data['available'].append({'beginTime': begin_time, 'endTime': end_time})
    return res_data
