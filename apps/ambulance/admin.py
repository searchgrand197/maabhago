from django.contrib import admin

from apps.ambulance.models import AmbulanceCollection, AmbulanceVehicle


@admin.register(AmbulanceVehicle)
class AmbulanceVehicleAdmin(admin.ModelAdmin):
    list_display = ("vehicle_number", "label", "driver_name", "hospital", "is_active")
    search_fields = ("vehicle_number", "driver_name")


@admin.register(AmbulanceCollection)
class AmbulanceCollectionAdmin(admin.ModelAdmin):
    list_display = ("receipt_no", "vehicle", "collected_at", "amount", "payment_mode", "voided")
    list_filter = ("payment_mode", "voided")
    search_fields = ("receipt_no", "vehicle__vehicle_number", "driver_name")
