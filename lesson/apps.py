from django.apps import AppConfig


class LessonConfig(AppConfig):
    name = 'lesson'

    def ready(self):
        from . import signals
