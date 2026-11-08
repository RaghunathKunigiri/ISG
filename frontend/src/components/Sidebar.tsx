import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderKanban,
  CheckSquare,
  Clock,
  CalendarCheck,
  BarChart3,
  ShieldAlert,
  History,
  Building2,
  HardDrive
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { user, hasPermission, hasRole } = useAuth();

  const navItems = [
    { label: 'Dashboard', path: '/', icon: LayoutDashboard },
    { label: 'Projects', path: '/projects', icon: FolderKanban },
    { label: 'Tasks & Tickets', path: '/tasks', icon: CheckSquare },
    { label: 'Timesheets', path: '/timesheets', icon: Clock },
    { label: 'Attendance', path: '/attendance', icon: CalendarCheck },
    { label: 'Reports & Analytics', path: '/reports', icon: BarChart3 },
  ];

  const adminItems = [
    { label: 'Login Sessions', path: '/admin/sessions', icon: ShieldAlert, condition: hasRole('admin') },
    { label: 'Audit Logs', path: '/admin/audit', icon: History, condition: hasRole(['admin', 'manager']) },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-100 flex flex-col min-h-screen border-r border-slate-800">
      {/* Branding */}
      <div className="p-5 border-b border-slate-800 flex items-center space-x-3">
        <div className="h-10 w-10 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-md">
          <HardDrive className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-bold text-base leading-tight text-white tracking-wide">ISG Tracker</h1>
          <p className="text-xs text-indigo-400 font-medium">Huntsville DC Ops</p>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Core Workflows
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}

        {/* Administration Section */}
        {hasRole(['admin', 'manager']) && (
          <div className="pt-6">
            <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Security & Audit
            </div>
            {adminItems
              .filter((item) => item.condition)
              .map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-indigo-600 text-white shadow'
                          : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                      }`
                    }
                  >
                    <Icon className="h-5 w-5 flex-shrink-0" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
          </div>
        )}
      </nav>

      {/* User info & Organization Badge */}
      <div className="p-4 border-t border-slate-800 bg-slate-950">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold text-sm uppercase border border-indigo-500/30">
            {user?.full_name?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-white truncate">{user?.full_name}</p>
            <div className="flex items-center space-x-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
              <p className="text-xs text-slate-400 capitalize truncate">{user?.role_name}</p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};

