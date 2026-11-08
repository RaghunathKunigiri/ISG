import React, { useState, useEffect } from 'react';
import { auditApi } from '../lib/api';
import { ShieldAlert, Laptop, Smartphone, Globe, Clock, Ban } from 'lucide-react';

export const AdminSessions: React.FC = () => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const res = await auditApi.getSessions();
      setSessions(res.data || []);
    } catch (err) {
      console.error('Failed to load login sessions', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Active Login Sessions</h1>
        <p className="text-sm text-slate-500">
          Enterprise session tracking &bull; Token lifetimes (15-min access, 7-day refresh with rotation)
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">No active sessions found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-4">Employee</th>
                  <th className="py-3 px-4">Device / Client</th>
                  <th className="py-3 px-4">IP Address</th>
                  <th className="py-3 px-4">Login Method</th>
                  <th className="py-3 px-4">Login Time</th>
                  <th className="py-3 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sessions.map((sess) => (
                  <tr key={sess.id} className="hover:bg-slate-50">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900">{sess.employee_name}</div>
                      <div className="text-[11px] text-slate-400">{sess.employee_code}</div>
                    </td>
                    <td className="py-3 px-4 text-slate-700">
                      <div className="flex items-center space-x-1.5">
                        <Laptop className="h-3.5 w-3.5 text-slate-400" />
                        <span>{sess.device_type} &bull; {sess.browser} ({sess.os})</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-slate-600 font-mono">{sess.ip_address}</td>
                    <td className="py-3 px-4 uppercase font-semibold text-indigo-600">{sess.login_method}</td>
                    <td className="py-3 px-4 text-slate-500">
                      {new Date(sess.login_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full font-semibold uppercase text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Active
                      </span>
                    </td>
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

