from django.test import TestCase, override_settings
from unittest import mock

from apps.attendance.email_utils import send_leave_approval_emails
from apps.attendance.models import LeaveApplication
from apps.settings_management.models import LeaveApprover
from apps.shared.models import Hospital
from apps.staff.models import StaffProfile
from django.contrib.auth import get_user_model


class LeaveApprovalEmailTests(TestCase):
    @override_settings(
        EMAIL_HOST="smtp.test.local",
        EMAIL_PORT=587,
        EMAIL_USE_SSL=False,
        EMAIL_USE_TLS=True,
        EMAIL_HOST_USER="noreply@test.local",
        EMAIL_HOST_PASSWORD="secret",
        DEFAULT_FROM_EMAIL="noreply@test.local",
        SITE_BASE_URL="http://testserver",
    )
    @mock.patch("apps.attendance.email_utils.smtplib.SMTP")
    @mock.patch("apps.attendance.email_utils.smtplib.SMTP_SSL")
    def test_send_leave_approval_emails_uses_same_smtp_pattern_as_staff(
        self, mock_smtp_ssl, mock_smtp
    ):
        """
        Ensure send_leave_approval_emails builds and sends an EmailMessage using
        the same SMTP pattern as staff creation (no crashes, one send call).
        """
        User = get_user_model()
        hospital = Hospital.objects.create(name="Test Hosp", slug="test-hosp")
        approver_user = User.objects.create_user(
            email="approver@test.local", password="x"
        )
        staff_user = User.objects.create_user(email="staff@test.local", password="x")
        staff = StaffProfile.objects.create(hospital=hospital, user=staff_user)

        LeaveApprover.objects.create(
            hospital=hospital,
            user=approver_user,
            is_active=True,
            notes="Test approver",
        )

        app = LeaveApplication.objects.create(
            hospital=hospital,
            staff=staff,
            leave_type=LeaveApplication.LeaveType.EARNED,
            start_date="2026-04-01",
            end_date="2026-04-01",
            total_days=1,
            reason="Test leave",
        )

        # Arrange SMTP mock context manager
        smtp_instance = mock_smtp.return_value.__enter__.return_value

        sent = send_leave_approval_emails(app)

        self.assertEqual(sent, 1)
        mock_smtp.assert_called_once_with("smtp.test.local", 587)
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("noreply@test.local", "secret")
        smtp_instance.send_message.assert_called_once()
