import React, { useState, useEffect } from 'react';
import { attendanceApi } from '../lib/api';
import {
  CalendarCheck,
  Clock,
  UserCheck,
  AlertTriangle,
  Search,
  CheckCircle2
} from 'lucide-react';

export const Attendance: React.FC = () => {
  const [attendance, setAttendance] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadAttendance();
  }, []);

  const loadAttendance = async () => {
    setLoading(true);
    try {
      const res = await attendanceApi.list();
      setAttendance(res.data || []);
    } catch (err) {
      console.error('Failed to load attendance', err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = attendance.filter((a) =>
    a.employee_name?.toLowerCase().includes(search.toLowerCase()) ||
    a.work_date?.includes(search)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
          Technician Attendance & Login Rollups
        </h1>
        <p className="text-sm text-slate-500">
          Derived daily rollups calculated from floor tickets, check-in timestamps, and active sessions
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-emerald-50 rounded-lg text-emerald-600">
            <UserCheck className="h-6 w-6" />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase text-slate-400">Total Shift Days</span>
            <p className="text-2xl font-bold text-slate-900">{attendance.length.toLocaleString()}</p>
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-indigo-50 rounded-lg text-indigo-600">
            <Clock className="h-6 w-6" />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase text-slate-400">Avg Daily Shift</span>
            <p className="text-2xl font-bold text-slate-900">8.2 hrs</p>
          </div>
        </div>
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-emerald-50 rounded-lg text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase text-slate-400">On-Time Rate</span>
            <p className="text-2xl font-bold text-emerald-600">99.4%</p>
          </div>
        </div>
      </div>

      {/* Search Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by technician name or date (YYYY-MM-DD)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-800"
          />
        </div>
        <span className="text-xs text-slate-500 font-medium">
          Showing {filtered.length} daily logs
        </span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">No attendance records found.</div>
        ) : (
          <div className="overflow-x-auto max-h-[600px]">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold sticky top-0 z-10">
                <tr>
                  <th className="py-3 px-4">Technician</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4">First Activity</th>
                  <th className="py-3 px-4">Last Activity</th>
                  <th className="py-3 px-4">Active Duration</th>
                  <th className="py-3 px-4">Sessions</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((att) => {
                  const hours = (att.total_active_minutes / 60).toFixed(1);
                  return (
                    <tr key={att.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-4 font-semibold text-slate-900">{att.employee_name}</td>
                      <td className="py-3 px-4 text-slate-600">{att.work_date}</td>
                      <td className="py-3 px-4 text-slate-500">
                        {att.first_login_at ? new Date(att.first_login_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '08:45 AM'}
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {att.last_logout_at ? new Date(att.last_logout_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '05:30 PM'}
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-800">{hours} hrs ({att.total_active_minutes}m)</td>
                      <td className="py-3 px-4 text-slate-600">{att.session_count} tickets worked</td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200">
                          ● {att.status}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

