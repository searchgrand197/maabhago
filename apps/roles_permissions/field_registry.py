"""
Registry of logical data fields per HMS module for field-level Create / Read / Update grants.

Codes align with app names used across the API surface where possible.
"""

from typing import TypedDict


class FieldDef(TypedDict):
    key: str
    label: str


MODULE_FIELDS: dict[str, dict[str, str | list[FieldDef]]] = {
    "patients": {
        "name": "Patients",
        "fields": [
            {"key": "patient_name", "label": "Patient name"},
            {"key": "date_of_birth", "label": "Date of birth"},
            {"key": "medical_history", "label": "Medical history"},
            {"key": "contact_info", "label": "Contact info"},
            {"key": "uhid", "label": "UHID / MRN"},
            {"key": "gender", "label": "Gender"},
            {"key": "address", "label": "Address"},
            {"key": "emergency_contact", "label": "Emergency contact"},
        ],
    },
    "appointments": {
        "name": "Appointments",
        "fields": [
            {"key": "appointment_date", "label": "Date"},
            {"key": "appointment_time", "label": "Time"},
            {"key": "provider_name", "label": "Provider name"},
            {"key": "reason_for_visit", "label": "Reason for visit"},
            {"key": "status", "label": "Status"},
            {"key": "patient_link", "label": "Linked patient"},
            {"key": "notes", "label": "Notes"},
        ],
    },
    "billing": {
        "name": "Billing",
        "fields": [
            {"key": "invoice_number", "label": "Invoice number"},
            {"key": "amount_due", "label": "Amount due"},
            {"key": "payment_status", "label": "Payment status"},
            {"key": "insurance_details", "label": "Insurance details"},
            {"key": "line_items", "label": "Line items"},
            {"key": "tax_discount", "label": "Tax & discounts"},
            {"key": "due_date", "label": "Due date"},
        ],
    },
    "payments": {
        "name": "Payments",
        "fields": [
            {"key": "amount", "label": "Amount"},
            {"key": "payment_method", "label": "Payment method"},
            {"key": "transaction_id", "label": "Transaction ID"},
            {"key": "invoice_link", "label": "Linked invoice"},
            {"key": "receipt_notes", "label": "Receipt notes"},
        ],
    },
    "opd": {
        "name": "OPD",
        "fields": [
            {"key": "chief_complaint", "label": "Chief complaint"},
            {"key": "diagnosis", "label": "Diagnosis"},
            {"key": "visit_date", "label": "Visit date"},
            {"key": "vitals", "label": "Vitals"},
            {"key": "prescription_link", "label": "Prescription ref."},
        ],
    },
    "ipd": {
        "name": "IPD",
        "fields": [
            {"key": "admission_date", "label": "Admission date"},
            {"key": "bed_assignment", "label": "Bed assignment"},
            {"key": "admission_diagnosis", "label": "Admission diagnosis"},
            {"key": "attending_doctor", "label": "Attending doctor"},
            {"key": "discharge_summary", "label": "Discharge summary"},
        ],
    },
    "tokens": {
        "name": "Tokens / Queue",
        "fields": [
            {"key": "token_number", "label": "Token number"},
            {"key": "queue_status", "label": "Queue status"},
            {"key": "department", "label": "Department"},
            {"key": "priority", "label": "Priority"},
        ],
    },
    "staff": {
        "name": "Staff",
        "fields": [
            {"key": "full_name", "label": "Full name"},
            {"key": "employee_id", "label": "Employee ID"},
            {"key": "department", "label": "Department"},
            {"key": "contact", "label": "Contact"},
            {"key": "shift", "label": "Shift"},
        ],
    },
    "doctors": {
        "name": "Doctors",
        "fields": [
            {"key": "registration_no", "label": "Registration no."},
            {"key": "specialty", "label": "Specialty"},
            {"key": "schedule", "label": "Schedule"},
            {"key": "consultation_fee", "label": "Consultation fee"},
        ],
    },
    "inventory": {
        "name": "Inventory",
        "fields": [
            {"key": "sku_item_name", "label": "SKU / item name"},
            {"key": "quantity", "label": "Quantity on hand"},
            {"key": "batch_expiry", "label": "Batch & expiry"},
            {"key": "supplier", "label": "Supplier"},
        ],
    },
    "pharmacy": {
        "name": "Pharmacy",
        "fields": [
            {"key": "prescription_ref", "label": "Prescription ref."},
            {"key": "dispense_quantity", "label": "Dispense quantity"},
            {"key": "drug_interaction_flags", "label": "Interaction flags"},
        ],
    },
    "lab": {
        "name": "Laboratory",
        "fields": [
            {"key": "test_name", "label": "Test name"},
            {"key": "specimen", "label": "Specimen"},
            {"key": "result_value", "label": "Result value"},
            {"key": "reference_range", "label": "Reference range"},
        ],
    },
    "prescriptions": {
        "name": "Prescriptions",
        "fields": [
            {"key": "medication", "label": "Medication"},
            {"key": "dosage", "label": "Dosage"},
            {"key": "duration", "label": "Duration"},
            {"key": "instructions", "label": "Instructions"},
        ],
    },
    "followups": {
        "name": "Follow-ups",
        "fields": [
            {"key": "next_visit_date", "label": "Next visit date"},
            {"key": "followup_notes", "label": "Notes"},
            {"key": "assigned_provider", "label": "Assigned provider"},
        ],
    },
    "insurance": {
        "name": "Insurance",
        "fields": [
            {"key": "policy_number", "label": "Policy number"},
            {"key": "coverage_type", "label": "Coverage type"},
            {"key": "payer_details", "label": "Payer details"},
            {"key": "authorization_ref", "label": "Authorization ref."},
        ],
    },
    "documents": {
        "name": "Documents",
        "fields": [
            {"key": "document_type", "label": "Document type"},
            {"key": "file_reference", "label": "File reference"},
            {"key": "patient_link", "label": "Linked patient"},
            {"key": "confidentiality_flag", "label": "Confidentiality"},
        ],
    },
    "emergency": {
        "name": "Emergency",
        "fields": [
            {"key": "triage_level", "label": "Triage level"},
            {"key": "arrival_time", "label": "Arrival time"},
            {"key": "chief_complaint", "label": "Chief complaint"},
            {"key": "stabilization_notes", "label": "Stabilization notes"},
        ],
    },
    "attendance": {
        "name": "Attendance",
        "fields": [
            {"key": "check_in", "label": "Check-in"},
            {"key": "check_out", "label": "Check-out"},
            {"key": "overtime", "label": "Overtime"},
        ],
    },
    "nursing": {
        "name": "Nursing",
        "fields": [
            {"key": "care_notes", "label": "Care notes"},
            {"key": "vitals_round", "label": "Vitals round"},
            {"key": "medication_admin", "label": "Medication administration"},
        ],
    },
    "beds": {
        "name": "Beds",
        "fields": [
            {"key": "ward", "label": "Ward"},
            {"key": "bed_code", "label": "Bed code"},
            {"key": "occupancy_status", "label": "Occupancy status"},
        ],
    },
    "referrals": {
        "name": "Referrals",
        "fields": [
            {"key": "referred_to", "label": "Referred to"},
            {"key": "reason", "label": "Reason"},
            {"key": "referral_date", "label": "Referral date"},
        ],
    },
    "reports": {
        "name": "Reports",
        "fields": [
            {"key": "report_type", "label": "Report type"},
            {"key": "date_range", "label": "Date range"},
            {"key": "export_payload", "label": "Export / payload"},
        ],
    },
    "settings_management": {
        "name": "Settings",
        "fields": [
            {"key": "hospital_profile", "label": "Hospital profile"},
            {"key": "theme_branding", "label": "Theme & branding"},
            {"key": "feature_flags", "label": "Feature flags"},
        ],
    },
    "discharge": {
        "name": "Discharge",
        "fields": [
            {"key": "discharge_date", "label": "Discharge date"},
            {"key": "final_diagnosis", "label": "Final diagnosis"},
            {"key": "followup_plan", "label": "Follow-up plan"},
        ],
    },
}


def list_modules_for_api() -> list[dict]:
    out: list[dict] = []
    for code, meta in sorted(MODULE_FIELDS.items(), key=lambda x: x[0]):
        fields = meta["fields"]
        if not isinstance(fields, list):
            continue
        out.append(
            {
                "code": code,
                "name": str(meta["name"]),
                "fields": [{"key": f["key"], "label": f["label"]} for f in fields],
            }
        )
    return out
