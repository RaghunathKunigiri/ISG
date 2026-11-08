import React, { useState, useEffect } from 'react';
import { reportsApi, projectsApi } from '../lib/api';
import {
  BarChart3,
  TrendingDown,
  AlertTriangle,
  Users,
  Clock,
  Download,
  Filter
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  LineChart,
  Line
} from 'recharts';

export const Reports: React.FC = () => {
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [burndownData, setBurndownData] = useState<any[]>([]);
  const [utilizationData, setUtilizationData] = useState<any[]>([]);
  const [slaBreaches, setSlaBreaches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadReports(selectedProjectId);
    }
  }, [selectedProjectId]);

  const loadProjects = async () => {
    try {
      const res = await projectsApi.list();
      setProjects(res.data || []);
      if (res.data && res.data.length > 0) {
        setSelectedProjectId(res.data[0].id);
      }
    } catch (err) {
      console.error('Failed to load projects', err);
    }
  };

  const loadReports = async (projId: string) => {
    setLoading(true);
    try {
      const [burnRes, utilRes, slaRes] = await Promise.all([
        reportsApi.getBurndown(projId),
        reportsApi.getUtilization(),
        reportsApi.getSlaBreaches(),
      ]);
      setBurndownData(burnRes.data?.snapshots || []);
      setUtilizationData(utilRes.data || []);
      setSlaBreaches(slaRes.data || []);
    } catch (err) {
      console.error('Failed to load reports', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Executive Analytics & Reports
          </h1>
          <p className="text-sm text-slate-500">
            Sprint burndown velocity, technician utilization, and SLA compliance
          </p>
        </div>

        {/* Project Selector */}
        <div className="flex items-center space-x-2">
          <span className="text-xs font-semibold text-slate-500 uppercase">Project:</span>
          <select
            value={selectedProjectId}
            onChange={(e) => setSelectedProjectId(e.target.value)}
            className="bg-white border border-slate-300 rounded-lg text-xs font-semibold px-3 py-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code} - {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <>
          {/* Burndown Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">Sprint Burndown Velocity</h3>
                <p className="text-xs text-slate-500">
                  Remaining Story Points vs Actual Cumulative Hours
                </p>
              </div>
              <span className="text-xs font-semibold bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-full border border-emerald-200">
                Velocity: On Track
              </span>
            </div>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={burndownData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="snapshot_date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="remaining_story_points"
                    stroke="#ef4444"
                    strokeWidth={2}
                    name="Remaining Story Points"
                  />
                  <Line
                    type="monotone"
                    dataKey="actual_hours"
                    stroke="#6366f1"
                    strokeWidth={2}
                    name="Cumulative Hours"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Technician Utilization Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-base font-bold text-slate-900">Technician Utilization & Billable Hours</h3>
                <p className="text-xs text-slate-500">
                  Total logged hours across current billing period
                </p>
              </div>
            </div>

            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={utilizationData.slice(0, 10)} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="employee_name" tick={{ fontSize: 11 }} angle={-25} textAnchor="end" />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="total_hours" fill="#4f46e5" name="Logged Hours" />
                  <Bar dataKey="billable_hours" fill="#10b981" name="Billable Hours" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* SLA Breaches Table */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center space-x-2 mb-4">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              <h3 className="text-base font-bold text-slate-900">
                SLA Breaches & Overdue Monitoring ({slaBreaches.length})
              </h3>
            </div>

            {slaBreaches.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500">
                No active SLA breaches detected across operations.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold">
                    <tr>
                      <th className="py-2.5 px-3">Ticket</th>
                      <th className="py-2.5 px-3">Assignee</th>
                      <th className="py-2.5 px-3">Due Date</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Breach Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {slaBreaches.map((b, idx) => (
                      <tr key={idx} className="hover:bg-slate-50">
                        <td className="py-2.5 px-3 font-semibold text-slate-900">{b.title}</td>
                        <td className="py-2.5 px-3 text-slate-700">{b.assignee_name || 'Unassigned'}</td>
                        <td className="py-2.5 px-3 text-rose-600 font-medium">{b.due_date}</td>
                        <td className="py-2.5 px-3 capitalize font-semibold">{b.status}</td>
                        <td className="py-2.5 px-3 text-rose-600">{b.blocked_reason || 'Past target due date'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

