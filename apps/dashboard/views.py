from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.billing.models import BillingInvoice
from apps.opd.models import OPDVisit
from apps.shared.response import success_response


class DoctorFinancialAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        
        # Filter finalized invoices attached to this doctor's OPD or IPD cases
        doctor_invoices = BillingInvoice.objects.filter(
            Q(opd_visit__doctor_user=user) | Q(ipd_admission__assigned_doctor=user),
            status=BillingInvoice.Status.FINALIZED,
            invoice_date__gte=thirty_days_ago
        )
        
        total_revenue = doctor_invoices.aggregate(tot=Sum('total_amount'))['tot'] or Decimal('0.00')
        opd_amount = doctor_invoices.filter(encounter_type=BillingInvoice.EncounterType.OPD).aggregate(tot=Sum('total_amount'))['tot'] or Decimal('0.00')
        ipd_amount = doctor_invoices.filter(encounter_type=BillingInvoice.EncounterType.IPD).aggregate(tot=Sum('total_amount'))['tot'] or Decimal('0.00')
        
        total_patients_seen = OPDVisit.objects.filter(
            doctor_user=user, 
            visit_date__gte=thirty_days_ago,
            status='completed'
        ).count()
        
        # Daily revenue vs. patients
        revenue_by_date = doctor_invoices.values('invoice_date').annotate(daily=Sum('total_amount'))
        patient_by_date = OPDVisit.objects.filter(
            doctor_user=user, 
            visit_date__gte=thirty_days_ago, 
            status='completed'
        ).values('visit_date').annotate(count=Count('id'))
        
        chart_data = {}
        for i in range(31):
            d = thirty_days_ago + timedelta(days=i)
            d_str = d.strftime('%Y-%m-%d')
            chart_data[d_str] = {'date': d_str, 'revenue': 0, 'patients': 0}
            
        for row in revenue_by_date:
            d_str = row['invoice_date'].strftime('%Y-%m-%d')
            if d_str in chart_data:
                chart_data[d_str]['revenue'] = float(row['daily'])
            
        for row in patient_by_date:
            d_str = row['visit_date'].strftime('%Y-%m-%d')
            if d_str in chart_data:
                chart_data[d_str]['patients'] = row['count']
            
        ordered_chart_data = [chart_data[k] for k in sorted(chart_data.keys())]

        return success_response({
            "total_revenue": float(total_revenue),
            "opd_revenue": float(opd_amount),
            "ipd_revenue": float(ipd_amount),
            "total_patients": total_patients_seen,
            "chart_data": ordered_chart_data
        })
