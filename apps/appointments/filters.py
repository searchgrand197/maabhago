import django_filters

from apps.appointments.models import Appointment


class AppointmentFilterSet(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    consultation_type = django_filters.CharFilter(field_name="consultation_type")
    doctor_id = django_filters.UUIDFilter(field_name="doctor_id")
    patient_uhid = django_filters.CharFilter(field_name="patient__uhid", lookup_expr="iexact")
    date_from = django_filters.DateFilter(field_name="appointment_datetime", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="appointment_datetime", lookup_expr="date__lte")

    class Meta:
        model = Appointment
        fields = ["status", "consultation_type", "doctor_id", "patient_uhid", "date_from", "date_to"]

