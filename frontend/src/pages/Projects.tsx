import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { projectsApi } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import {
  FolderKanban,
  Plus,
  ArrowUpRight,
  Clock,
  DollarSign,
  Activity,
  Calendar,
  AlertCircle
} from 'lucide-react';

const HEALTH_COLORS: Record<string, string> = {
  green: '#10b981',
  amber: '#f59e0b',
  red: '#ef4444',
};

export const Projects: React.FC = () => {
  const { hasRole } = useAuth();
  const [projects, setProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    client: '',
    priority: 'medium',
    start_date: new Date().toISOString().split('T')[0],
    target_end_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
    budget_hours: 500,
    budget_cost: 20000,
  });

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const res = await projectsApi.list();
      setProjects(res.data);
    } catch (err) {
      console.error('Failed to load projects', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await projectsApi.create(formData);
      setShowModal(false);
      setFormData({
        code: '',
        name: '',
        description: '',
        client: '',
        priority: 'medium',
        start_date: new Date().toISOString().split('T')[0],
        target_end_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
        budget_hours: 500,
        budget_cost: 20000,
      });
      loadProjects();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create project');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Projects & Operations</h1>
          <p className="text-sm text-slate-500">
            Multi-sprint operations tracking, automated SPI calculations, and milestone cascaded progress
          </p>
        </div>

        {hasRole(['admin', 'manager']) && (
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-sm transition-colors"
          >
            <Plus className="h-4 w-4 mr-1.5" />
            New Project
          </button>
        )}
      </div>

      {/* Projects Grid */}
      {loading ? (
        <div className="h-64 flex items-center justify-center">
          <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((proj) => (
            <div
              key={proj.id}
              className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider bg-indigo-50 px-2.5 py-1 rounded border border-indigo-100">
                    {proj.code}
                  </span>
                  <span
                    className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold uppercase"
                    style={{
                      backgroundColor: `${HEALTH_COLORS[proj.health] || '#10b981'}15`,
                      color: HEALTH_COLORS[proj.health] || '#10b981',
                    }}
                  >
                    ● {proj.health}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-slate-900 leading-snug">
                  <Link to={`/projects/${proj.id}`} className="hover:text-indigo-600">
                    {proj.name}
                  </Link>
                </h3>
                <p className="text-xs text-slate-500 mt-1 line-clamp-2">{proj.description}</p>

                {/* Progress bar */}
                <div className="mt-5 space-y-1.5">
                  <div className="flex justify-between text-xs font-medium text-slate-700">
                    <span>Progress</span>
                    <span className="font-bold">{proj.progress_pct}%</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-indigo-600 h-2 rounded-full"
                      style={{ width: `${Math.min(proj.progress_pct, 100)}%` }}
                    ></div>
                  </div>
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-3 mt-5 pt-4 border-t border-slate-100 text-xs text-slate-600">
                  <div className="flex items-center space-x-1.5">
                    <Activity className="h-4 w-4 text-slate-400" />
                    <span>SPI: <strong>{proj.spi || 1.0}</strong></span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <Clock className="h-4 w-4 text-slate-400" />
                    <span>Budget: <strong>{proj.budget_hours}h</strong></span>
                  </div>
                  <div className="flex items-center space-x-1.5 col-span-2">
                    <Calendar className="h-4 w-4 text-slate-400" />
                    <span>Target: {proj.target_end_date}</span>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-100">
                <Link
                  to={`/projects/${proj.id}`}
                  className="w-full inline-flex items-center justify-center py-2 px-3 rounded-lg bg-slate-50 hover:bg-indigo-50 hover:text-indigo-600 text-xs font-semibold text-slate-700 border border-slate-200 transition-colors"
                >
                  View Burndown & Milestones
                  <ArrowUpRight className="h-4 w-4 ml-1" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Create New Project</h3>
            <p className="text-xs text-slate-500 mb-4">Initialize tracking, budget hours, and delivery target</p>

            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase">Project Code</label>
                  <input
                    type="text"
                    required
                    placeholder="HSV-OPT"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase">Client</label>
                  <input
                    type="text"
                    required
                    placeholder="Acme Corp"
                    value={formData.client}
                    onChange={(e) => setFormData({ ...formData, client: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase">Project Name</label>
                <input
                  type="text"
                  required
                  placeholder="Data Hall Optimization Sprint"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 uppercase">Description</label>
                <textarea
                  rows={2}
                  placeholder="Scope, objectives, and deliverables"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase">Start Date</label>
                  <input
                    type="date"
                    required
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase">Target End Date</label>
                  <input
                    type="date"
                    required
                    value={formData.target_end_date}
                    onChange={(e) => setFormData({ ...formData, target_end_date: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase">Budget Hours</label>
                  <input
                    type="number"
                    value={formData.budget_hours}
                    onChange={(e) => setFormData({ ...formData, budget_hours: parseFloat(e.target.value) })}
                    className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 uppercase">Budget Cost ($)</label>
                  <input
                    type="number"
                    value={formData.budget_cost}
                    onChange={(e) => setFormData({ ...formData, budget_cost: parseFloat(e.target.value) })}
                    className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg"
                >
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

