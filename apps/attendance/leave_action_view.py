"""
One-click leave approve / deny view — no login required.

The URL carries a short-lived signed token that encodes:
  - leave_id   (UUID)
  - approver_id (user pk)
  - action      ("approve" | "deny")

The view validates the token, performs the action via the existing service,
and returns a self-contained HTML page (no template files needed).
"""

from __future__ import annotations

from django.core import signing
from django.http import HttpResponse
from django.views import View

from apps.attendance.email_utils import load_leave_action_token
from apps.attendance.models import LeaveApplication
from apps.attendance.services import approve_leave_application


def _page(title: str, emoji: str, heading: str, body: str, color: str = "#1e40af") -> HttpResponse:
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Arial, sans-serif; background: #f4f6f8;
            display: flex; align-items: center; justify-content: center;
            min-height: 100vh; }}
    .card {{ background: #fff; border-radius: 12px; padding: 48px 40px;
             max-width: 480px; width: 100%; text-align: center;
             box-shadow: 0 4px 20px rgba(0,0,0,.10); }}
    .icon {{ font-size: 56px; margin-bottom: 16px; }}
    h1 {{ font-size: 22px; color: {color}; margin-bottom: 12px; }}
    p  {{ font-size: 15px; color: #4b5563; line-height: 1.6; }}
    .badge {{ display: inline-block; margin-top: 20px; padding: 6px 18px;
              border-radius: 999px; font-size: 13px; font-weight: 700;
              background: {color}20; color: {color}; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{emoji}</div>
    <h1>{heading}</h1>
    <p>{body}</p>
    <span class="badge">{title}</span>
  </div>
</body>
</html>"""
    return HttpResponse(html)


class LeaveActionView(View):
    """
    GET /leave/action/<token>/

    Validates the signed token and approves or denies the leave application.
    Renders a self-contained HTML result page — works directly from an email client.
    """

    def get(self, request, token: str) -> HttpResponse:
        # ── 1. Decode token ────────────────────────────────────────────────
        try:
            payload = load_leave_action_token(token)
        except signing.SignatureExpired:
            return _page(
                "Link Expired", "⏰",
                "This link has expired",
                "Leave approval links are valid for 7 days. Please log in to the HMS dashboard to take action.",
                color="#d97706",
            )
        except signing.BadSignature:
            return _page(
                "Invalid Link", "🚫",
                "Invalid or tampered link",
                "This link is not valid. Please use the link from the original notification email.",
                color="#dc2626",
            )

        leave_id = payload.get("leave_id")
        approver_id = payload.get("approver_id")
        action = payload.get("action")  # "approve" or "deny"

        # ── 2. Load leave application ──────────────────────────────────────
        try:
            application = LeaveApplication.objects.select_related(
                "staff", "hospital"
            ).get(pk=leave_id)
        except LeaveApplication.DoesNotExist:
            return _page(
                "Not Found", "❓",
                "Leave application not found",
                "The leave request linked in this email no longer exists.",
                color="#6b7280",
            )

        # ── 3. Check if already actioned ──────────────────────────────────
        if application.status != LeaveApplication.Status.PENDING:
            status_label = application.status.replace("_", " ").title()
            return _page(
                "Already Actioned", "ℹ️",
                f"Leave already {status_label}",
                f"This leave request was already <strong>{status_label}</strong>. No further action is needed.",
                color="#6b7280",
            )

        # ── 4. Load approver user ──────────────────────────────────────────
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            approver = User.objects.get(pk=approver_id)
        except User.DoesNotExist:
            return _page(
                "Approver Not Found", "🚫",
                "Approver account not found",
                "The approver account associated with this link no longer exists.",
                color="#dc2626",
            )

        # ── 5. Perform the action ──────────────────────────────────────────
        approve = (action == "approve")
        staff = application.staff
        staff_name = (
            f"{getattr(staff, 'first_name', '')} {getattr(staff, 'last_name', '')}".strip()
            or str(staff)
        )
        leave_type = application.leave_type.replace("_", " ").title()
        days = application.total_days

        try:
            approve_leave_application(
                application=application,
                approver=approver,
                approve=approve,
                rejection_notes="Actioned via email link." if not approve else "",
            )
        except ValueError as e:
            return _page(
                "Action Failed", "⚠️",
                "Could not process this action",
                str(e),
                color="#d97706",
            )

        if approve:
            return _page(
                "Leave Approved", "✅",
                "Leave Approved",
                f"You have <strong>approved</strong> {staff_name}'s {leave_type} leave "
                f"({days} day(s): {application.start_date} → {application.end_date}).<br/><br/>"
                "The staff member will be notified.",
                color="#16a34a",
            )
        else:
            return _page(
                "Leave Denied", "❌",
                "Leave Denied",
                f"You have <strong>denied</strong> {staff_name}'s {leave_type} leave request "
                f"({days} day(s): {application.start_date} → {application.end_date}).",
                color="#dc2626",
            )
