from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.notifications.models import Notification, WebPushSubscription
from apps.notifications.serializers import (
    NotificationSerializer,
    WebPushSubscriptionCreateSerializer,
    WebPushSubscriptionSerializer,
)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by("-created_at")

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.mark_read()
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        qs = self.get_queryset().filter(is_read=False)
        count = qs.update(is_read=True)
        return Response({"marked_read": count})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})

    @action(detail=False, methods=["get"], url_path="push/public-key")
    def push_public_key(self, request):
        public_key = getattr(settings, "WEBPUSH_PUBLIC_KEY", "")
        return Response(
            {
                "public_key": public_key,
                "configured": bool(public_key),
            }
        )

    @action(detail=False, methods=["post"], url_path="push/subscribe")
    def push_subscribe(self, request):
        serializer = WebPushSubscriptionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        values = {
            "hospital_id": request.user.hospital_id,
            "user_id": request.user.id,
            "p256dh_key": payload["p256dh_key"],
            "auth_key": payload["auth_key"],
            "user_agent": request.headers.get("User-Agent", "")[:500],
            "is_active": True,
            "last_seen_at": timezone.now(),
        }
        sub, _ = WebPushSubscription.objects.update_or_create(
            endpoint=payload["endpoint"],
            defaults=values,
        )
        return Response(WebPushSubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="push/unsubscribe")
    def push_unsubscribe(self, request):
        endpoint = str(request.data.get("endpoint", "")).strip()
        if not endpoint:
            return Response({"detail": "endpoint is required"}, status=status.HTTP_400_BAD_REQUEST)
        updated = WebPushSubscription.objects.filter(
            user=request.user,
            endpoint=endpoint,
            is_active=True,
        ).update(is_active=False)
        return Response({"unsubscribed": bool(updated)})
