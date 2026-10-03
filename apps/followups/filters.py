import django_filters

from apps.followups.models import FollowUp


class FollowUpFilterSet(django_filters.FilterSet):
    followup_status = django_filters.CharFilter(field_name="followup_status")
    reminder_status = django_filters.CharFilter(field_name="reminder_status")
    doctor_id = django_filters.UUIDFilter(field_name="doctor_id", lookup_expr="exact")
    next_visit_date_from = django_filters.DateFilter(field_name="next_visit_date", lookup_expr="gte")
    next_visit_date_to = django_filters.DateFilter(field_name="next_visit_date", lookup_expr="lte")

    class Meta:
        model = FollowUp
        fields = ["followup_status", "reminder_status", "doctor_id", "next_visit_date_from", "next_visit_date_to"]

