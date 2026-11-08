import React from 'react';
import { LogOut, Bell, Shield, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-4">
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
          Org: Huntsville DC Operations
        </span>
        <span className="text-xs text-slate-500 font-medium hidden sm:inline-block">
          {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
        </span>
      </div>

      <div className="flex items-center space-x-4">
        {/* Role Badge */}
        <div className="flex items-center space-x-2 bg-slate-100 px-3 py-1 rounded-full border border-slate-200 text-xs font-medium text-slate-700">
          <Shield className="h-3.5 w-3.5 text-indigo-600" />
          <span className="capitalize">{user?.role_name || 'Member'}</span>
        </div>

        {/* User identifier */}
        <div className="text-right hidden md:block">
          <p className="text-sm font-medium text-slate-800 leading-tight">{user?.full_name}</p>
          <p className="text-xs text-slate-500">{user?.email}</p>
        </div>

        {/* Logout */}
        <button
          onClick={logout}
          title="Sign out"
          className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
        >
          <LogOut className="h-5 w-5" />
        </button>
      </div>
    </header>
  );
};

