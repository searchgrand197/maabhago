from rest_framework import serializers

from apps.notifications.models import Notification, WebPushSubscription


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "hospital",
            "recipient",
            "notification_type",
            "title",
            "message",
            "is_read",
            "read_at",
            "reference_type",
            "reference_id",
            "created_at",
        ]
        read_only_fields = ["id", "hospital", "recipient", "created_at"]


class WebPushSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebPushSubscription
        fields = [
            "id",
            "endpoint",
            "p256dh_key",
            "auth_key",
            "is_active",
            "last_seen_at",
        ]
        read_only_fields = ["id", "is_active", "last_seen_at"]


class WebPushSubscriptionCreateSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=2000)
    p256dh_key = serializers.CharField(max_length=255)
    auth_key = serializers.CharField(max_length=255)
