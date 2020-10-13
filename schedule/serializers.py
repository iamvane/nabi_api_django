from rest_framework import serializers

from core.utils import DayChoices


class InstructorAvailabilitySerializer(serializers.Serializer):
    dates = serializers.ListField(child=serializers.DateField(format='%Y-%m-%d'), required=False)
    weekDays = serializers.ListField(child=serializers.ChoiceField(choices=list(DayChoices.labels.keys())), required=False)
    intervals = serializers.ListField(child=serializers.DictField())

    def validate_intervals(self, value_list):
        for item in value_list:
            if item.get('beginTime') is None:
                raise serializers.ValidationError('intervals list must include beginTime value')
            if item.get('endTime') is None:
                raise serializers.ValidationError('intervals list must include endTime value')
            if item.get('available') is None:
                raise serializers.ValidationError('intervals list must include available value')
            if item.get('endTime') < item.get('beginTime'):
                raise serializers.ValidationError('beginTime value cannot be previous to endTime value')
        return value_list

    def validate(self, attrs):
        if not attrs.get('dates') and not attrs.get('weekDays'):
            raise serializers.ValidationError('dates or weekDays value must be provided')
        return attrs
