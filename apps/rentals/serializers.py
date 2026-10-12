import re
from datetime import date
from decimal import Decimal

from rest_framework import serializers

from apps.rentals.models import RentCollection, RentShop
from apps.rentals.services import month_start


class MonthField(serializers.Field):
    """Accepts ``YYYY-MM`` or ``YYYY-MM-DD`` and stores the first day of that month."""

    default_error_messages = {"invalid": "Use YYYY-MM format."}

    def to_internal_value(self, data):
        match = re.fullmatch(r"(\d{4})-(\d{1,2})(?:-\d{1,2})?", str(data or "").strip())
        if not match:
            self.fail("invalid")
        year, month = int(match.group(1)), int(match.group(2))
        if not 1 <= month <= 12:
            self.fail("invalid")
        return date(year, month, 1)

    def to_representation(self, value):
        return value.strftime("%Y-%m") if value else None


class RentShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentShop
        fields = [
            "id",
            "shop_name",
            "shop_number",
            "owner_name",
            "owner_phone",
            "monthly_rent",
            "due_day",
            "rent_start_date",
            "security_deposit",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_monthly_rent(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Monthly rent must be greater than zero.")
        return value

    def validate_security_deposit(self, value):
        if value < 0:
            raise serializers.ValidationError("Cannot be negative.")
        return value

    def validate(self, attrs):
        for key in ("shop_name", "shop_number", "owner_name", "owner_phone", "notes"):
            if key in attrs:
                attrs[key] = str(attrs[key] or "").strip()
        if "shop_name" in attrs and not attrs["shop_name"]:
            raise serializers.ValidationError({"shop_name": ["Shop name is required."]})
        if "owner_name" in attrs and not attrs["owner_name"]:
            raise serializers.ValidationError({"owner_name": ["Owner name is required."]})

        shop_name = attrs.get("shop_name", getattr(self.instance, "shop_name", ""))
        shop_number = attrs.get("shop_number", getattr(self.instance, "shop_number", ""))
        qs = RentShop.objects.filter(
            hospital_id=self.context["hospital_id"],
            shop_name__iexact=shop_name,
            shop_number__iexact=shop_number,
        )
        if self.instance is not None:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError({"shop_name": ["A shop with this name and number already exists."]})
        return attrs


class RentCollectionSerializer(serializers.ModelSerializer):
    rent_month = MonthField()
    shop_name = serializers.CharField(source="shop.shop_name", read_only=True)
    shop_number = serializers.CharField(source="shop.shop_number", read_only=True)
    owner_name = serializers.CharField(source="shop.owner_name", read_only=True)
    owner_phone = serializers.CharField(source="shop.owner_phone", read_only=True)
    monthly_rent = serializers.DecimalField(
        source="shop.monthly_rent", max_digits=12, decimal_places=2, read_only=True
    )
    collected_by_name = serializers.CharField(source="collected_by.full_name", read_only=True)
    voided_by_name = serializers.CharField(source="voided_by.full_name", read_only=True, default="")

    class Meta:
        model = RentCollection
        fields = [
            "id",
            "receipt_no",
            "shop",
            "shop_name",
            "shop_number",
            "owner_name",
            "owner_phone",
            "monthly_rent",
            "rent_month",
            "collected_at",
            "amount",
            "payment_mode",
            "paid_by",
            "reference_no",
            "remarks",
            "collected_by",
            "collected_by_name",
            "status",
            "voided",
            "void_reason",
            "voided_at",
            "voided_by_name",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "receipt_no",
            "collected_by",
            "status",
            "voided",
            "void_reason",
            "voided_at",
            "created_at",
        ]

    def validate_shop(self, shop):
        if shop.hospital_id != self.context["hospital_id"]:
            raise serializers.ValidationError("Shop not found.")
        if not shop.is_active:
            raise serializers.ValidationError("This shop is inactive.")
        return shop

    def validate_amount(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def validate(self, attrs):
        shop = attrs.get("shop")
        rent_month = attrs.get("rent_month")
        if shop is not None and rent_month is not None and rent_month < month_start(shop.rent_start_date):
            raise serializers.ValidationError(
                {"rent_month": [f"Rent starts from {shop.rent_start_date.strftime('%b %Y')}."]}
            )
        for key in ("paid_by", "reference_no", "remarks"):
            if key in attrs:
                attrs[key] = str(attrs[key] or "").strip()
        if shop is not None and not attrs.get("paid_by"):
            attrs["paid_by"] = shop.owner_name
        return attrs
