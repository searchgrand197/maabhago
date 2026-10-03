import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ArrowLeft,
  ClipboardList,
  Lock,
  LockOpen,
  PenLine,
  Plus,
  Search,
  Send,
  UserPlus,
  Users,
  X,
} from 'lucide-react'
import api from '../api'
import toast from 'react-hot-toast'
import { format } from 'date-fns'

const STATUS_COLORS = {
  active: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  locked: 'bg-amber-100 text-amber-800 border-amber-200',
  completed: 'bg-blue-100 text-blue-800 border-blue-200',
  cancelled: 'bg-slate-100 text-slate-600 border-slate-200',
  Active: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  Completed: 'bg-blue-100 text-blue-800 border-blue-200',
  'No Plan': 'bg-slate-100 text-slate-600 border-slate-200',
}

function PatientCard({ patient, onOpenPlan }) {
  const statusCls = STATUS_COLORS[patient.plan_status] || STATUS_COLORS['No Plan']
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 hover:shadow-md transition-shadow flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-bold text-slate-900 truncate">{patient.patient_name}</h3>
          <p className="text-[10px] text-slate-500 font-mono">{patient.uhid}</p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
            {patient.admission_type}
          </span>
          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${statusCls}`}>
            {patient.plan_status}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-[10px] text-slate-600">
        <Users size={12} className="text-slate-400" />
        {patient.assigned_staff_count > 0 ? (
          <span>{patient.assigned_staff_count} staff assigned</span>
        ) : (
          <span className="text-slate-400">No staff assigned</span>
        )}
        {patient.plan_count > 0 && (
          <span className="text-[10px] text-slate-500">
            {patient.plan_count} plan{patient.plan_count > 1 ? 's' : ''}
          </span>
        )}
        <button
          type="button"
          onClick={() => onOpenPlan(patient)}
          className="ml-auto text-[11px] font-semibold px-2.5 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
        >
          Open Plan
        </button>
      </div>

      {patient.assigned_staff_names.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {patient.assigned_staff_names.slice(0, 4).map((name, i) => (
            <span key={i} className="text-[9px] bg-slate-100 text-slate-700 rounded px-1.5 py-0.5">
              {name}
            </span>
          ))}
          {patient.assigned_staff_names.length > 4 && (
            <span className="text-[9px] text-slate-500">+{patient.assigned_staff_names.length - 4}</span>
          )}
        </div>
      )}

      <div className="mt-auto pt-1 border-t border-slate-100" />
    </div>
  )
}

function StaffSelector({ planId, admissionId, onClose }) {
  const [staffList, setStaffList] = useState([])
  const [assigned, setAssigned] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [staffRes, plansRes] = await Promise.all([
        api.get('/staff/?limit=200'),
        api.get(`/treatment-plans/?ipd_admission=${admissionId}&status=active`),
      ])
      const allStaff = staffRes.data?.results || staffRes.data?.data || staffRes.data || []
      setStaffList(Array.isArray(allStaff) ? allStaff : [])

      const plans = plansRes.data?.results || plansRes.data?.data || plansRes.data || []
      const allAssigned = []
      for (const plan of (Array.isArray(plans) ? plans : [])) {
        const asRes = await api.get(`/treatment-plans/${plan.id}/staff-assignments/`)
        const items = Array.isArray(asRes.data) ? asRes.data : asRes.data?.results || []
        items.forEach((a) => allAssigned.push({ ...a, plan_id: plan.id }))
      }
      setAssigned(allAssigned)
    } catch {
      toast.error('Failed to load staff data')
    } finally {
      setLoading(false)
    }
  }, [admissionId])

  useEffect(() => {
    loadData()
  }, [loadData])

  const assignedStaffIds = new Set(assigned.map((a) => String(a.staff)))

  const filtered = useMemo(() => {
    const qLower = q.toLowerCase().trim()
    if (!qLower) return staffList
    return staffList.filter(
      (s) =>
        `${s.first_name || ''} ${s.last_name || ''} ${s.employee_code || ''}`
          .toLowerCase()
          .includes(qLower),
    )
  }, [staffList, q])

  async function handleAssign(staffId) {
    const plans = await api
      .get(`/treatment-plans/?ipd_admission=${admissionId}&status=active`)
      .then((r) => r.data?.results || r.data?.data || r.data || [])
    if (!plans.length) {
      toast.error('No active plan for this patient. Create a plan first.')
      return
    }
    try {
      await api.post(`/treatment-plans/${plans[0].id}/staff-assignments/`, { staff: staffId })
      toast.success('Staff assigned')
      loadData()
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.response?.data?.staff?.[0] || 'Failed to assign'
      toast.error(detail)
    }
  }

  async function handleRemove(assignment) {
    try {
      await api.delete(`/treatment-plans/${assignment.plan_id}/staff-assignments/${assignment.id}/`)
      toast.success('Staff removed')
      loadData()
    } catch {
      toast.error('Failed to remove')
    }
  }

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[200] flex items-center justify-center p-4">
      <div className="bg-white w-full max-w-lg rounded-xl shadow-xl border border-slate-200 overflow-hidden">
        <div className="p-3 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">Assign Staff</h3>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={16} />
          </button>
        </div>
        <div className="p-3">
          {assigned.length > 0 && (
            <div className="mb-3">
              <p className="text-[10px] font-bold text-slate-500 uppercase mb-1">Currently Assigned</p>
              <div className="flex flex-wrap gap-1.5">
                {assigned.map((a) => (
                  <span
                    key={a.id}
                    className="inline-flex items-center gap-1 bg-blue-50 text-blue-800 border border-blue-200 rounded-full px-2 py-0.5 text-[11px] font-medium"
                  >
                    {a.staff_name}
                    <button
                      type="button"
                      onClick={() => handleRemove(a)}
                      className="text-blue-400 hover:text-red-500"
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="relative mb-2">
            <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search staff..."
              className="w-full pl-8 pr-3 py-1.5 text-[12px] rounded border border-slate-200 outline-none focus:border-blue-500"
            />
          </div>

          <div className="max-h-48 overflow-y-auto space-y-1">
            {loading && <p className="text-[11px] text-slate-500 p-2">Loading...</p>}
            {!loading &&
              filtered.map((s) => {
                const isAssigned = assignedStaffIds.has(String(s.id))
                const name = `${s.first_name || ''} ${s.last_name || ''}`.trim() || s.employee_code
                return (
                  <div
                    key={s.id}
                    className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-slate-50"
                  >
                    <div className="min-w-0">
                      <p className="text-[12px] font-medium text-slate-900 truncate">{name}</p>
                      <p className="text-[10px] text-slate-500">{s.designation_name || s.department_name || ''}</p>
                    </div>
                    {isAssigned ? (
                      <span className="text-[10px] text-emerald-600 font-semibold">Assigned</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleAssign(s.id)}
                        className="text-[10px] font-semibold px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
                      >
                        Assign
                      </button>
                    )}
                  </div>
                )
              })}
            {!loading && filtered.length === 0 && (
              <p className="text-[11px] text-slate-500 p-2 text-center">No staff found.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function PatientInfoChip({ patient, onBack }) {
  return (
    <div className="flex items-center gap-1.5 shrink-0">
      <button
        type="button"
        onClick={onBack}
        className="p-1 rounded border border-slate-200 text-slate-600 hover:bg-slate-50"
        title="Back to patient list"
      >
        <ArrowLeft size={14} />
      </button>
      <span className="text-[11px] font-bold text-slate-900">{patient.patient_name}</span>
      <span className="text-[9px] font-mono text-slate-500">{patient.uhid}</span>
      <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
        {patient.admission_type}
      </span>
      <span className={`text-[9px] font-bold px-1 py-0.5 rounded border ${patient.plan_status === 'Active' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
        {patient.plan_status}
      </span>
    </div>
  )
}

function PlanListView({ patient, onBack, onEditPlan, onCreateNew }) {
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)

  const loadPlans = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get(`/treatment-plans/?ipd_admission=${patient.admission_id}`)
      const list = res.data?.results || res.data?.data || res.data || []
      setPlans(Array.isArray(list) ? list : [])
    } catch {
      toast.error('Failed to load plans')
    } finally {
      setLoading(false)
    }
  }, [patient.admission_id])

  useEffect(() => {
    loadPlans()
  }, [loadPlans])

  async function handleLock(plan) {
    try {
      await api.post(`/treatment-plans/${plan.id}/lock/`)
      toast.success('Plan locked & sent to staff')
      loadPlans()
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to lock plan')
    }
  }

  async function handleUnlock(plan) {
    try {
      await api.post(`/treatment-plans/${plan.id}/unlock/`)
      toast.success('Plan unlocked for editing')
      loadPlans()
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to unlock plan')
    }
  }

  return (
    <div className="h-full flex flex-col gap-2 overflow-hidden">
      <div className="flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <button type="button" onClick={onBack} className="p-1 rounded border border-slate-200 text-slate-600 hover:bg-slate-50">
            <ArrowLeft size={14} />
          </button>
          <span className="text-sm font-bold text-slate-900">{patient.patient_name}</span>
          <span className="text-[9px] font-mono text-slate-500">{patient.uhid}</span>
        </div>
        <button
          type="button"
          onClick={onCreateNew}
          className="flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded bg-blue-600 text-white hover:bg-blue-700"
        >
          <Plus size={14} /> New Plan
        </button>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {loading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-lg p-3 animate-pulse">
                <div className="h-4 bg-slate-200 rounded w-1/2 mb-2" />
                <div className="h-3 bg-slate-100 rounded w-1/3" />
              </div>
            ))}
          </div>
        ) : plans.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <ClipboardList size={28} className="mb-2 text-slate-300" />
            <p className="text-sm font-medium mb-2">No treatment plans yet</p>
            <button
              type="button"
              onClick={onCreateNew}
              className="flex items-center gap-1 text-[11px] font-semibold px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700"
            >
              <Plus size={14} /> Create First Plan
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {plans.map((plan) => {
              const isLocked = plan.status === 'locked'
              const isActive = plan.status === 'active'
              const statusCls = STATUS_COLORS[plan.status] || STATUS_COLORS['cancelled']
              return (
                <div key={plan.id} className="bg-white border border-slate-200 rounded-lg p-3 flex items-center gap-3 hover:shadow-sm transition-shadow">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <p className="text-[12px] font-bold text-slate-900 truncate">{plan.name || 'Unnamed Plan'}</p>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border shrink-0 ${statusCls}`}>
                        {plan.status}
                      </span>
                      {isLocked && <Lock size={12} className="text-amber-600 shrink-0" />}
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-slate-500">
                      <span>{plan.start_date} → {plan.end_date || '...'}</span>
                      <span>{plan.item_count || 0} items</span>
                      <span>by {plan.created_by_email || '—'}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {isActive && (
                      <>
                        <button
                          type="button"
                          onClick={() => onEditPlan(plan)}
                          className="flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded border border-slate-300 text-slate-700 hover:bg-slate-50"
                          title="Edit plan"
                        >
                          <PenLine size={12} /> Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleLock(plan)}
                          className="flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded bg-amber-500 text-white hover:bg-amber-600"
                          title="Lock and send to staff"
                        >
                          <Lock size={12} /> Lock & Send
                        </button>
                      </>
                    )}
                    {isLocked && (
                      <button
                        type="button"
                        onClick={() => handleUnlock(plan)}
                        className="flex items-center gap-1 text-[10px] font-semibold px-2 py-1 rounded border border-amber-300 text-amber-700 hover:bg-amber-50"
                        title="Unlock for editing"
                      >
                        <LockOpen size={12} /> Unlock & Edit
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default function TreatmentPlansModule({ TPBuilderComponent }) {
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedPatient, setSelectedPatient] = useState(null)

  const loadPatients = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.get('/treatment/patient-overview/')
      setPatients(Array.isArray(res.data) ? res.data : res.data?.data || [])
    } catch {
      toast.error('Failed to load patient overview')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPatients()
  }, [loadPatients])

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return patients
    return patients.filter(
      (p) =>
        p.patient_name.toLowerCase().includes(q) ||
        p.uhid.toLowerCase().includes(q) ||
        p.plan_status.toLowerCase().includes(q),
    )
  }, [patients, search])

  if (selectedPatient) {
    return (
      <div style={{ height: 'calc(100vh - 120px)' }} className="flex flex-col overflow-hidden">
        <TPBuilderComponent
          preSelectedAdmission={selectedPatient.admission_id}
          onBack={() => { setSelectedPatient(null); loadPatients() }}
          patientChip={
            <PatientInfoChip
              patient={selectedPatient}
              onBack={() => {
                setSelectedPatient(null)
                loadPatients()
              }}
            />
          }
        />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col gap-2 overflow-hidden">
      <div className="flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2">
          <ClipboardList size={18} className="text-blue-600" />
          <h2 className="text-base font-bold text-slate-900">Treatment Plans</h2>
          <span className="text-[10px] font-semibold bg-slate-100 text-slate-600 rounded-full px-2 py-0.5">
            {patients.length} patients
          </span>
        </div>
        <div className="relative">
          <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search patient..."
            className="pl-8 pr-3 py-1.5 text-[12px] rounded border border-slate-200 bg-white outline-none focus:border-blue-500 w-56"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-lg p-3 animate-pulse">
                <div className="h-4 bg-slate-200 rounded w-3/4 mb-2" />
                <div className="h-3 bg-slate-100 rounded w-1/2 mb-3" />
                <div className="h-8 bg-slate-100 rounded" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <ClipboardList size={32} className="mb-2 text-slate-300" />
            <p className="text-sm font-medium">
              {patients.length === 0 ? 'No admitted patients found' : 'No patients match your search'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {filtered.map((p) => (
              <PatientCard
                key={p.admission_id}
                patient={p}
                onOpenPlan={(pt) => setSelectedPatient(pt)}
              />
            ))}
          </div>
        )}
      </div>

    </div>
  )
}
