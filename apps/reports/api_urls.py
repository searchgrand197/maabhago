from django.urls import path

from apps.reports.views import CaSummaryView, CollectionSummaryView, DoctorRevenueView

urlpatterns = [
    path("collection-summary/", CollectionSummaryView.as_view(), name="reports-collection-summary"),
    path("ca-summary/", CaSummaryView.as_view(), name="reports-ca-summary"),
    path("doctor-revenue/", DoctorRevenueView.as_view(), name="reports-doctor-revenue"),
]
