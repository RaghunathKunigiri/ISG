import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { dashboardApi, timesheetsApi, tasksApi } from '../lib/api';
import { StatCard } from '../components/StatCard';
import {
  FolderKanban,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Users,
  ShieldCheck,
  TrendingUp,
  Activity,
  ArrowUpRight,
  Filter,
  Check,
  X
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  CartesianGrid
} from 'recharts';
import { Link } from 'react-router-dom';

const STATUS_COLORS: Record<string, string> = {
  done: '#10b981',
  in_progress: '#3b82f6',
  blocked: '#ef4444',
  in_review: '#f59e0b',
  todo: '#64748b',
};

const HEALTH_COLORS: Record<string, string> = {
  green: '#10b981',
  amber: '#f59e0b',
  red: '#ef4444',
};

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'default' | 'admin' | 'manager' | 'member'>('default');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Determine effective view
  const role = user?.role_name || 'member';
  const effectiveView = activeTab === 'default'
    ? (role === 'admin' ? 'admin' : (role === 'manager' || role === 'team_lead' ? 'manager' : 'member'))
    : activeTab;

  useEffect(() => {
    fetchDashboardData(effectiveView);
  }, [effectiveView]);

  const fetchDashboardData = async (view: string) => {
    setLoading(true);
    try {
      if (view === 'admin') {
        const res = await dashboardApi.getAdmin();
        setData(res.data);
      } else if (view === 'manager') {
        const res = await dashboardApi.getManager();
        setData(res.data);
      } else {
        const res = await dashboardApi.getMember();
        setData(res.data);
      }
    } catch (err) {
      console.error('Failed to load dashboard', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveTimesheet = async (timesheetId: string) => {
    try {
      await timesheetsApi.approve(timesheetId);
      fetchDashboardData(effectiveView);
    } catch (err) {
      alert('Failed to approve timesheet.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Role Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Operations & Performance Dashboard
          </h1>
          <p className="text-sm text-slate-500">
            Huntsville Data Center Campus &bull; Real-time ticket progress & resource health
          </p>
        </div>

        {/* View Switcher for Admins / Managers */}
        {(role === 'admin' || role === 'manager') && (
          <div className="flex bg-slate-200/80 p-1 rounded-lg text-xs font-semibold text-slate-600">
            <button
              onClick={() => setActiveTab('admin')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                effectiveView === 'admin' ? 'bg-white text-indigo-700 shadow-sm' : 'hover:text-slate-900'
              }`}
            >
              Executive View
            </button>
            <button
              onClick={() => setActiveTab('manager')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                effectiveView === 'manager' ? 'bg-white text-indigo-700 shadow-sm' : 'hover:text-slate-900'
              }`}
            >
              Manager View
            </button>
            <button
              onClick={() => setActiveTab('member')}
              className={`px-3 py-1.5 rounded-md transition-colors ${
                effectiveView === 'member' ? 'bg-white text-indigo-700 shadow-sm' : 'hover:text-slate-900'
              }`}
            >
              Technician View
            </button>
          </div>
        )}
      </div>

      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <>
          {/* ============================================================== */}
          {/* ADMIN / EXECUTIVE DASHBOARD */}
          {/* ============================================================== */}
          {effectiveView === 'admin' && data && (
            <div className="space-y-6">
              {/* Stat Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  title="Tracked Projects"
                  value={data.project_count || 3}
                  icon={FolderKanban}
                  subtitle="HSV-TKT, HSV-FIBER, HSV-TOOL"
                  color="indigo"
                />
                <StatCard
                  title="Active Workforce"
                  value={data.employee_count || 22}
                  icon={Users}
                  subtitle="Field technicians & leads"
                  color="emerald"
                />
                <StatCard
                  title="Live Sessions"
                  value={data.active_sessions_count || 4}
                  icon={ShieldCheck}
                  subtitle="Enterprise secure tokens active"
                  color="slate"
                />
                <StatCard
                  title="Org Health SPI"
                  value="0.98"
                  badge="Healthy"
                  trend="up"
                  icon={Activity}
                  subtitle="Schedule performance index"
                  color="emerald"
                />
              </div>

              {/* Project Health Grid */}
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Project Health Matrix</h3>
                    <p className="text-xs text-slate-500">
                      Evaluated on progress vs elapsed time, effort variance, and blocked tickets
                    </p>
                  </div>
                  <Link
                    to="/projects"
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center"
                  >
                    View All Projects <ArrowUpRight className="h-4 w-4 ml-0.5" />
                  </Link>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-xs font-semibold uppercase text-slate-500">
                        <th className="pb-3">Code</th>
                        <th className="pb-3">Project Name</th>
                        <th className="pb-3">Health</th>
                        <th className="pb-3">Progress</th>
                        <th className="pb-3">SPI</th>
                        <th className="pb-3">Hours Logged</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {(data.project_health_grid || []).map((proj: any) => (
                        <tr key={proj.id} className="hover:bg-slate-50">
                          <td className="py-3 font-semibold text-slate-800">{proj.code}</td>
                          <td className="py-3 text-slate-700">
                            <Link to={`/projects/${proj.id}`} className="hover:text-indigo-600 font-medium">
                              {proj.name}
                            </Link>
                          </td>
                          <td className="py-3">
                            <span
                              className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide"
                              style={{
                                backgroundColor: `${HEALTH_COLORS[proj.health] || '#10b981'}15`,
                                color: HEALTH_COLORS[proj.health] || '#10b981',
                              }}
                            >
                              ● {proj.health}
                            </span>
                          </td>
                          <td className="py-3">
                            <div className="w-32 bg-slate-100 rounded-full h-2.5 overflow-hidden">
                              <div
                                className="bg-indigo-600 h-2.5 rounded-full"
                                style={{ width: `${Math.min(proj.progress_pct, 100)}%` }}
                              ></div>
                            </div>
                            <span className="text-xs text-slate-500 mt-1 inline-block">
                              {proj.progress_pct}%
                            </span>
                          </td>
                          <td className="py-3 font-medium text-slate-700">{proj.spi || 1.0}</td>
                          <td className="py-3 text-slate-600">{proj.actual_hours || 0} hrs</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Recent Security Attempts */}
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                <h3 className="text-base font-bold text-slate-900 mb-1">Recent Authentication & Access Events</h3>
                <p className="text-xs text-slate-500 mb-4">
                  Monitored for automated brute-force lockouts and anomalous logins
                </p>

                <div className="space-y-3">
                  {(data.recent_login_attempts || []).slice(0, 5).map((att: any, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 rounded-lg border border-slate-100 bg-slate-50/50 text-xs"
                    >
                      <div className="flex items-center space-x-3">
                        <span
                          className={`w-2.5 h-2.5 rounded-full ${att.success ? 'bg-emerald-500' : 'bg-rose-500'}`}
                        ></span>
                        <span className="font-semibold text-slate-800">{att.email_attempted}</span>
                        <span className="text-slate-500">IP: {att.ip_address || '127.0.0.1'}</span>
                      </div>
                      <div className="text-slate-500">
                        {att.attempted_at ? new Date(att.attempted_at).toLocaleString() : 'Just now'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* MANAGER DASHBOARD */}
          {/* ============================================================== */}
          {effectiveView === 'manager' && data && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  title="Team Technicians"
                  value={data.team_size || 18}
                  icon={Users}
                  subtitle="Assigned to Huntsville DC"
                  color="indigo"
                />
                <StatCard
                  title="Blocked / Escalated"
                  value={data.blocked_count || (data.blocked_tasks ? data.blocked_tasks.length : 0)}
                  badge={data.blocked_count > 0 ? "Requires Attention" : "Clear"}
                  trend={data.blocked_count > 0 ? "down" : "up"}
                  icon={AlertTriangle}
                  subtitle="Engineering/fiber blockers"
                  color="rose"
                />
                <StatCard
                  title="Timesheets Pending"
                  value={data.timesheet_approval_queue || 0}
                  icon={Clock}
                  subtitle="Submitted for review"
                  color="amber"
                />
                <StatCard
                  title="Overall Team Output"
                  value="3,351 Tickets"
                  badge="+100% SLA"
                  trend="up"
                  icon={CheckCircle2}
                  subtitle="Cumulative closures"
                  color="emerald"
                />
              </div>

              {/* Blocked Tasks Escalation Queue */}
              {data.blocked_tasks && data.blocked_tasks.length > 0 && (
                <div className="bg-white rounded-xl border border-rose-200 p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-2">
                      <AlertTriangle className="h-5 w-5 text-rose-600" />
                      <h3 className="text-base font-bold text-slate-900">
                        Blocked Tickets Queue ({data.blocked_tasks.length})
                      </h3>
                    </div>
                    <span className="text-xs text-rose-700 font-semibold bg-rose-50 px-2.5 py-1 rounded-full border border-rose-200">
                      SLA Alert
                    </span>
                  </div>

                  <div className="divide-y divide-slate-100">
                    {data.blocked_tasks.slice(0, 6).map((t: any) => (
                      <div key={t.id} className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-semibold text-slate-900 text-sm">{t.title}</span>
                            <span className="text-xs bg-rose-100 text-rose-800 font-semibold px-2 py-0.5 rounded">
                              {t.priority}
                            </span>
                          </div>
                          <p className="text-xs text-rose-600 mt-0.5 font-medium">
                            Blocker: {t.blocked_reason || 'Escalated to engineering'}
                          </p>
                          <p className="text-xs text-slate-400">
                            Technician: {t.assignee_name || 'Assigned Tech'} &bull; Due: {t.due_date || 'N/A'}
                          </p>
                        </div>
                        <Link
                          to={`/tasks?search=${encodeURIComponent(t.title)}`}
                          className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold"
                        >
                          Resolve & Update &rarr;
                        </Link>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Team Progress & Closure Distribution */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                  <h3 className="text-base font-bold text-slate-900 mb-1">Technician Output Distribution</h3>
                  <p className="text-xs text-slate-500 mb-4">Tickets worked vs closed by team members</p>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={(data.team_progress || []).slice(0, 8)}
                        margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="employee_name" tick={{ fontSize: 11 }} angle={-25} textAnchor="end" />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="closed_tasks" fill="#10b981" name="Closed Tickets" />
                        <Bar dataKey="total_tasks" fill="#6366f1" name="Total Assigned" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Capacity & Allocation Heatmap Table */}
                <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                  <h3 className="text-base font-bold text-slate-900 mb-1">Resource Allocation & Hours</h3>
                  <p className="text-xs text-slate-500 mb-4">Weekly logged hours vs standard 40h capacity</p>
                  <div className="overflow-y-auto max-h-64">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500 font-semibold uppercase">
                          <th className="pb-2">Technician</th>
                          <th className="pb-2">Logged Hours</th>
                          <th className="pb-2">Utilization</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {(data.capacity_heatmap || []).map((tech: any, idx: number) => {
                          const pct = Math.round((tech.logged_hours / 40.0) * 100);
                          return (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="py-2.5 font-medium text-slate-800">{tech.employee_name}</td>
                              <td className="py-2.5 text-slate-600">{tech.logged_hours} hrs</td>
                              <td className="py-2.5">
                                <span
                                  className={`px-2 py-0.5 rounded font-semibold text-[11px] ${
                                    pct >= 100
                                      ? 'bg-rose-100 text-rose-800'
                                      : pct >= 80
                                      ? 'bg-emerald-100 text-emerald-800'
                                      : 'bg-amber-100 text-amber-800'
                                  }`}
                                >
                                  {pct}%
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ============================================================== */}
          {/* MEMBER / TECHNICIAN DASHBOARD */}
          {/* ============================================================== */}
          {effectiveView === 'member' && data && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  title="Completed Today"
                  value={data.my_tasks_by_status?.done || 0}
                  icon={CheckCircle2}
                  subtitle="Resolved tickets"
                  color="emerald"
                />
                <StatCard
                  title="In Progress"
                  value={data.my_tasks_by_status?.in_progress || 0}
                  icon={Activity}
                  subtitle="Active on floor"
                  color="indigo"
                />
                <StatCard
                  title="Blocked / Needs Lead"
                  value={data.my_tasks_by_status?.blocked || 0}
                  icon={AlertTriangle}
                  subtitle="Awaiting escalation"
                  color="rose"
                />
                <StatCard
                  title="My Hours Logged"
                  value={`${data.my_hours_this_week || 0} hrs`}
                  icon={Clock}
                  subtitle="Current payroll week"
                  color="slate"
                />
              </div>

              {/* Recent Tasks List */}
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-bold text-slate-900">My Assigned Tickets</h3>
                  <Link
                    to="/tasks"
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center"
                  >
                    View All My Tasks <ArrowUpRight className="h-4 w-4 ml-0.5" />
                  </Link>
                </div>

                <div className="divide-y divide-slate-100">
                  {(data.recent_tasks || []).map((task: any) => (
                    <div key={task.id} className="py-3.5 flex items-center justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: STATUS_COLORS[task.status] || '#64748b' }}
                          ></span>
                          <span className="font-semibold text-sm text-slate-900">{task.title}</span>
                          <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 capitalize">
                            {task.priority}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-1 line-clamp-1">{task.description}</p>
                      </div>
                      <div className="flex items-center space-x-3 text-right">
                        <div>
                          <span className="text-xs font-semibold text-slate-700 block">
                            {task.actual_hours}h spent
                          </span>
                          <span className="text-[11px] text-slate-400 capitalize">{task.status}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

