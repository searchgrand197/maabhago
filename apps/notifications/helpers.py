from __future__ import annotations
import json
import logging

from django.conf import settings
from django.utils import timezone
from apps.notifications.models import Notification
from apps.notifications.models import WebPushSubscription

logger = logging.getLogger(__name__)


def send_notification(
    hospital_id,
    recipient,
    notification_type: str,
    title: str,
    message: str = "",
    reference_type: str = "",
    reference_id: str = "",
):
    notif = Notification.objects.create(
        hospital_id=hospital_id,
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    send_webpush_to_user(
        user=recipient,
        payload={
            "title": title,
            "body": message or title,
            "tag": f"{notification_type}:{reference_id or ''}",
            "url": "/staff",
        },
    )
    return notif


def _webpush_enabled() -> bool:
    return bool(
        getattr(settings, "WEBPUSH_PUBLIC_KEY", "")
        and getattr(settings, "WEBPUSH_PRIVATE_KEY", "")
        and getattr(settings, "WEBPUSH_SUB_EMAIL", "")
    )


def send_webpush_to_user(user, payload: dict):
    if not _webpush_enabled():
        return
    try:
        from pywebpush import webpush, WebPushException
    except Exception:
        logger.warning("pywebpush not installed, skipping web push send")
        return

    subscriptions = WebPushSubscription.objects.filter(user=user, is_active=True)
    if not subscriptions.exists():
        return

    vapid_claims = {"sub": settings.WEBPUSH_SUB_EMAIL}
    payload_json = json.dumps(payload)

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh_key,
                        "auth": sub.auth_key,
                    },
                },
                data=payload_json,
                vapid_private_key=settings.WEBPUSH_PRIVATE_KEY,
                vapid_claims=vapid_claims,
            )
            sub.last_seen_at = timezone.now()
            sub.save(update_fields=["last_seen_at", "updated_at"])
        except WebPushException:
            sub.is_active = False
            sub.save(update_fields=["is_active", "updated_at"])


def notify_treatment_assigned(hospital_id, recipient, patient_name: str, plan_name: str, plan_id: str):
    return send_notification(
        hospital_id=hospital_id,
        recipient=recipient,
        notification_type=Notification.NType.TREATMENT_ASSIGNED,
        title=f"Treatment Plan assigned: {patient_name}",
        message=f"You have been assigned to treatment plan '{plan_name}' for patient {patient_name}.",
        reference_type="treatment_plan",
        reference_id=str(plan_id),
    )


def notify_treatment_updated(hospital_id, recipient, patient_name: str, plan_name: str, plan_id: str):
    return send_notification(
        hospital_id=hospital_id,
        recipient=recipient,
        notification_type=Notification.NType.TREATMENT_UPDATED,
        title=f"Treatment Plan updated: {patient_name}",
        message=f"Treatment plan '{plan_name}' for patient {patient_name} has been updated.",
        reference_type="treatment_plan",
        reference_id=str(plan_id),
    )


def notify_package_assigned(hospital_id, recipient, patient_name: str, package_name: str, plan_id: str):
    return send_notification(
        hospital_id=hospital_id,
        recipient=recipient,
        notification_type=Notification.NType.PACKAGE_ASSIGNED,
        title=f"Package assigned: {package_name}",
        message=f"Package '{package_name}' assigned to patient {patient_name}.",
        reference_type="treatment_plan",
        reference_id=str(plan_id),
    )
