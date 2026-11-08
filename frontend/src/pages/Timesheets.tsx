import React, { useState, useEffect } from 'react';
import { timesheetsApi, employeesApi, projectsApi } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import {
  Clock,
  Plus,
  CheckCircle,
  XCircle,
  Calendar,
  Filter,
  DollarSign,
  AlertCircle
} from 'lucide-react';

export const Timesheets: React.FC = () => {
  const { user, hasRole } = useAuth();
  const [timesheets, setTimesheets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [showModal, setShowModal] = useState(false);

  // New Timesheet Form
  const [formData, setFormData] = useState({
    work_date: new Date().toISOString().split('T')[0],
    hours: 8.0,
    description: '',
    billable: true,
  });

  useEffect(() => {
    loadTimesheets();
  }, [statusFilter]);

  const loadTimesheets = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      const res = await timesheetsApi.list(params);
      setTimesheets(res.data || []);
    } catch (err) {
      console.error('Failed to load timesheets', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await timesheetsApi.approve(id);
      loadTimesheets();
    } catch (err) {
      alert('Failed to approve timesheet.');
    }
  };

  const handleReject = async (id: string) => {
    const reason = prompt('Please provide rejection reason:') || 'Incomplete description';
    try {
      await timesheetsApi.reject(id, reason);
      loadTimesheets();
    } catch (err) {
      alert('Failed to reject timesheet.');
    }
  };

  // Compute total hours
  const totalApprovedHours = timesheets
    .filter((t) => t.status === 'approved')
    .reduce((sum, t) => sum + (t.hours || 0), 0);

  const totalPendingHours = timesheets
    .filter((t) => t.status === 'submitted')
    .reduce((sum, t) => sum + (t.hours || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Timesheet Logs</h1>
          <p className="text-sm text-slate-500">
            Technician daily hours, client billing reconciliation, and approval workflows
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-sm transition-colors"
        >
          <Plus className="h-4 w-4 mr-1.5" />
          Log Time
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase text-slate-400">Total Approved Hours</span>
          <p className="text-2xl font-bold text-emerald-600 mt-1">{totalApprovedHours.toFixed(1)} hrs</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase text-slate-400">Pending Review</span>
          <p className="text-2xl font-bold text-amber-600 mt-1">{totalPendingHours.toFixed(1)} hrs</p>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase text-slate-400">Recorded Entries</span>
          <p className="text-2xl font-bold text-slate-900 mt-1">{timesheets.length.toLocaleString()}</p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold text-slate-500 uppercase mr-1">Status:</span>
          {['all', 'approved', 'submitted', 'rejected'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-md text-xs capitalize transition-colors ${
                statusFilter === st
                  ? 'bg-indigo-600 text-white font-semibold shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Timesheets Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : timesheets.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">No timesheets found.</div>
        ) : (
          <div className="overflow-x-auto max-h-[600px]">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold sticky top-0 z-10">
                <tr>
                  <th className="py-3 px-4">Technician</th>
                  <th className="py-3 px-4">Work Date</th>
                  <th className="py-3 px-4">Project</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4">Hours</th>
                  <th className="py-3 px-4">Status</th>
                  {hasRole(['admin', 'manager']) && <th className="py-3 px-4 text-right">Approvals</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {timesheets.slice(0, 100).map((ts) => (
                  <tr key={ts.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-900">{ts.employee_name}</td>
                    <td className="py-3 px-4 text-slate-600">{ts.work_date}</td>
                    <td className="py-3 px-4 text-indigo-600 font-medium">{ts.project_name}</td>
                    <td className="py-3 px-4 text-slate-700 max-w-xs truncate">{ts.description}</td>
                    <td className="py-3 px-4 font-bold text-slate-900">{ts.hours}h</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase ${
                          ts.status === 'approved'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : ts.status === 'rejected'
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}
                      >
                        {ts.status}
                      </span>
                    </td>
                    {hasRole(['admin', 'manager']) && (
                      <td className="py-3 px-4 text-right space-x-1.5">
                        {ts.status === 'submitted' && (
                          <>
                            <button
                              onClick={() => handleApprove(ts.id)}
                              title="Approve"
                              className="p-1 rounded hover:bg-emerald-50 text-emerald-600 transition-colors"
                            >
                              <CheckCircle className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleReject(ts.id)}
                              title="Reject"
                              className="p-1 rounded hover:bg-rose-50 text-rose-600 transition-colors"
                            >
                              <XCircle className="h-4 w-4" />
                            </button>
                          </>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

