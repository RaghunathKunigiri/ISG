import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { projectsApi, tasksApi } from '../lib/api';
import {
  ArrowLeft,
  Calendar,
  Clock,
  Activity,
  CheckCircle2,
  AlertCircle,
  TrendingDown,
  Layers,
  CheckSquare
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  AreaChart,
  Area
} from 'recharts';

export const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<any>(null);
  const [snapshots, setSnapshots] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      loadProjectData(id);
    }
  }, [id]);

  const loadProjectData = async (projId: string) => {
    setLoading(true);
    try {
      const [projRes, snapRes, taskRes] = await Promise.all([
        projectsApi.get(projId),
        projectsApi.getSnapshots(projId),
        tasksApi.list({ project_id: projId, page_size: 50 }),
      ]);
      setProject(projRes.data);
      setSnapshots(snapRes.data || []);
      setTasks(taskRes.data?.items || []);
    } catch (err) {
      console.error('Failed to load project details', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <p className="text-slate-500">Project not found.</p>
        <Link to="/projects" className="text-indigo-600 text-sm font-semibold mt-2 inline-block">
          &larr; Back to Projects
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button & Breadcrumb */}
      <div className="flex items-center space-x-2 text-xs text-slate-500">
        <Link to="/projects" className="hover:text-indigo-600 flex items-center">
          <ArrowLeft className="h-3.5 w-3.5 mr-1" />
          Projects
        </Link>
        <span>/</span>
        <span className="text-slate-800 font-semibold">{project.code}</span>
      </div>

      {/* Project Overview Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="flex items-center space-x-3">
              <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider bg-indigo-50 px-2.5 py-1 rounded border border-indigo-100">
                {project.code}
              </span>
              <h1 className="text-2xl font-bold text-slate-900">{project.name}</h1>
            </div>
            <p className="text-sm text-slate-500 mt-1 max-w-2xl">{project.description}</p>
          </div>

          <div className="flex items-center space-x-4">
            <div className="text-right">
              <span className="text-xs text-slate-400 uppercase font-semibold block">Health Status</span>
              <span className="text-sm font-bold capitalize text-emerald-600">● {project.health}</span>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-400 uppercase font-semibold block">SPI Metric</span>
              <span className="text-sm font-bold text-slate-800">{project.spi || 1.0}</span>
            </div>
          </div>
        </div>

        {/* Progress & Metadata Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-6 text-xs text-slate-600">
          <div>
            <span className="text-slate-400 uppercase block font-semibold mb-1">Target End Date</span>
            <div className="flex items-center space-x-1.5 font-medium text-slate-800">
              <Calendar className="h-4 w-4 text-slate-400" />
              <span>{project.target_end_date}</span>
            </div>
          </div>
          <div>
            <span className="text-slate-400 uppercase block font-semibold mb-1">Budget Logged</span>
            <div className="flex items-center space-x-1.5 font-medium text-slate-800">
              <Clock className="h-4 w-4 text-slate-400" />
              <span>{project.actual_hours || 0} / {project.budget_hours} hrs</span>
            </div>
          </div>
          <div>
            <span className="text-slate-400 uppercase block font-semibold mb-1">Progress Cascade</span>
            <span className="text-base font-bold text-indigo-600">{project.progress_pct}%</span>
          </div>
          <div>
            <span className="text-slate-400 uppercase block font-semibold mb-1">Client Org</span>
            <span className="font-medium text-slate-800">{project.client}</span>
          </div>
        </div>
      </div>

      {/* Burndown Chart & Progress Snapshot Trends */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-slate-900">Burndown & Progress Trajectory</h3>
            <p className="text-xs text-slate-500">
              Historical daily snapshots from Huntsville operations &bull; Progress % vs Actual Hours
            </p>
          </div>
          <span className="text-xs font-semibold bg-indigo-50 text-indigo-700 px-2.5 py-1 rounded-full border border-indigo-200">
            {snapshots.length} Data Points
          </span>
        </div>

        <div className="h-72">
          {snapshots.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={snapshots} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="progGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="snapshot_date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} domain={[0, 100]} />
                <Tooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="progress_pct"
                  stroke="#6366f1"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#progGrad)"
                  name="Progress %"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-400">
              Snapshots will be generated tonight or upon ticket milestone progression.
            </div>
          )}
        </div>
      </div>

      {/* Milestones Hierarchy */}
      {project.milestones && project.milestones.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center space-x-2 mb-4">
            <Layers className="h-5 w-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">Milestones & Sprint Allocations</h3>
          </div>

          <div className="space-y-3">
            {project.milestones.map((m: any) => (
              <div
                key={m.id}
                className="p-4 rounded-lg border border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <h4 className="font-semibold text-slate-800 text-sm">{m.name}</h4>
                    <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-slate-200 text-slate-700">
                      Weight: {m.weight}x
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">Due: {m.due_date} &bull; Status: {m.status}</p>
                </div>

                <div className="flex items-center space-x-3 w-48">
                  <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-emerald-500 h-2 rounded-full"
                      style={{ width: `${Math.min(m.progress_pct, 100)}%` }}
                    ></div>
                  </div>
                  <span className="text-xs font-bold text-slate-700 w-10 text-right">
                    {Math.round(m.progress_pct)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Associated Tasks Preview */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <CheckSquare className="h-5 w-5 text-indigo-600" />
            <h3 className="text-base font-bold text-slate-900">Recent Operational Tickets</h3>
          </div>
          <Link
            to={`/tasks?project_id=${project.id}`}
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
          >
            Open in Ticket Tracker &rarr;
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500 uppercase font-semibold">
                <th className="pb-2.5">Ticket / Title</th>
                <th className="pb-2.5">Assignee</th>
                <th className="pb-2.5">Status</th>
                <th className="pb-2.5">Priority</th>
                <th className="pb-2.5">Hours</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {tasks.slice(0, 8).map((t) => (
                <tr key={t.id} className="hover:bg-slate-50">
                  <td className="py-2.5 font-medium text-slate-900 max-w-xs truncate">{t.title}</td>
                  <td className="py-2.5 text-slate-600">{t.assignee_name || 'Technician'}</td>
                  <td className="py-2.5">
                    <span className="capitalize font-semibold text-slate-700">{t.status}</span>
                  </td>
                  <td className="py-2.5 uppercase font-semibold text-indigo-600">{t.priority}</td>
                  <td className="py-2.5 text-slate-600">{t.actual_hours}h</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

