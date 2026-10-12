from django.contrib import admin

from apps.rentals.models import RentCollection, RentShop


@admin.register(RentShop)
class RentShopAdmin(admin.ModelAdmin):
    list_display = ("shop_name", "shop_number", "owner_name", "monthly_rent", "hospital", "is_active")
    search_fields = ("shop_name", "shop_number", "owner_name", "owner_phone")


@admin.register(RentCollection)
class RentCollectionAdmin(admin.ModelAdmin):
    list_display = ("receipt_no", "shop", "rent_month", "collected_at", "amount", "payment_mode", "voided")
    list_filter = ("payment_mode", "voided")
    search_fields = ("receipt_no", "shop__shop_name", "shop__owner_name")
