import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { HardDrive, ShieldCheck, KeyRound, AlertCircle, ArrowRight } from 'lucide-react';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [requiresMfa, setRequiresMfa] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await login(email, password, totpCode || undefined);
      if (res.requiresMfa) {
        setRequiresMfa(true);
      } else {
        navigate('/');
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Authentication failed. Please verify credentials.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const setQuickUser = (userEmail: string) => {
    setEmail(userEmail);
    setPassword('ChangeMe123!');
    setRequiresMfa(false);
    setTotpCode('');
    setError(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-slate-100">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex items-center justify-center h-14 w-14 rounded-2xl bg-indigo-600 text-white shadow-lg mb-4 ring-4 ring-indigo-500/20">
          <HardDrive className="h-8 w-8" />
        </div>
        <h2 className="text-3xl font-extrabold tracking-tight text-white">
          ISG Progress Tracker
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Enterprise Data Center Operations & Performance Management
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-900 py-8 px-6 shadow-2xl rounded-2xl sm:px-10 border border-slate-800">
          {error && (
            <div className="mb-5 p-3.5 rounded-lg bg-rose-950/60 border border-rose-800/80 text-rose-200 text-xs flex items-start space-x-2.5">
              <AlertCircle className="h-4 w-4 text-rose-400 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                Work Email Address
              </label>
              <div className="mt-1.5">
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="technician@example.com"
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
                Password (Argon2id)
              </label>
              <div className="mt-1.5">
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                />
              </div>
            </div>

            {requiresMfa && (
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-amber-400 flex items-center space-x-1">
                  <KeyRound className="h-3.5 w-3.5 mr-1" />
                  MFA Code (TOTP 6-digit)
                </label>
                <div className="mt-1.5">
                  <input
                    type="text"
                    maxLength={6}
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value)}
                    placeholder="123456"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-amber-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500 text-sm tracking-widest text-center"
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center items-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Authenticating...' : requiresMfa ? 'Verify & Sign In' : 'Sign In'}
              <ArrowRight className="ml-2 h-4 w-4" />
            </button>
          </form>

          {/* Quick Demo Logins */}
          <div className="mt-6 pt-6 border-t border-slate-800">
            <p className="text-xs font-medium text-slate-400 mb-2.5 text-center">
              Quick Sign-in (Huntsville DC Team):
            </p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <button
                type="button"
                onClick={() => setQuickUser('admin@example.com')}
                className="px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 rounded text-slate-200 text-left truncate transition-colors"
              >
                👑 <strong>Admin</strong> (Alice)
              </button>
              <button
                type="button"
                onClick={() => setQuickUser('manager@example.com')}
                className="px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 rounded text-slate-200 text-left truncate transition-colors"
              >
                📊 <strong>Manager</strong> (Bob)
              </button>
              <button
                type="button"
                onClick={() => setQuickUser('raghunath@example.com')}
                className="px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 rounded text-slate-200 text-left truncate transition-colors"
              >
                🔧 <strong>Lead</strong> (Raghunath)
              </button>
              <button
                type="button"
                onClick={() => setQuickUser('haripriya@example.com')}
                className="px-2.5 py-1.5 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 rounded text-slate-200 text-left truncate transition-colors"
              >
                ⚡ <strong>Tech</strong> (Hari Priya)
              </button>
            </div>
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-slate-500">
          Enforced rate-limiting (5 req/min on login) &bull; Automatic 30-min lockout after 5 failed attempts.
        </p>
      </div>
    </div>
  );
};

