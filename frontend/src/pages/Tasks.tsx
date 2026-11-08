import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { tasksApi, employeesApi, projectsApi } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import {
  CheckSquare,
  Search,
  Filter,
  Plus,
  AlertTriangle,
  Clock,
  CheckCircle,
  Tag,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

const STATUS_OPTIONS = ['all', 'done', 'in_progress', 'blocked', 'in_review', 'todo'];
const PRIORITY_OPTIONS = ['all', 'urgent', 'high', 'medium', 'low'];

export const Tasks: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { user } = useAuth();

  const [tasks, setTasks] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [status, setStatus] = useState(searchParams.get('status') || 'all');
  const [priority, setPriority] = useState('all');

  // Modal for status & progress update
  const [selectedTask, setSelectedTask] = useState<any>(null);
  const [updateComment, setUpdateComment] = useState('');
  const [updateHours, setUpdateHours] = useState(1.0);
  const [updateProgress, setUpdateProgress] = useState(100);
  const [updateStatus, setUpdateStatus] = useState('done');

  // Create task modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState('medium');
  const [newEstHours, setNewEstHours] = useState(1.0);

  useEffect(() => {
    loadTasks();
  }, [page, status, priority]);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const params: any = {
        page,
        page_size: pageSize,
      };
      if (search) params.search = search;
      if (status !== 'all') params.status = status;
      if (priority !== 'all') params.priority = priority;

      const res = await tasksApi.list(params);
      setTasks(res.data?.items || []);
      setTotal(res.data?.total || 0);
    } catch (err) {
      console.error('Failed to load tasks', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadTasks();
  };

  const handleSaveUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask) return;

    try {
      await tasksApi.addUpdate(selectedTask.id, {
        progress_pct: updateProgress,
        comment: updateComment,
        hours_logged: updateHours,
      });

      if (updateStatus !== selectedTask.status) {
        await tasksApi.update(selectedTask.id, {
          status: updateStatus,
          progress_pct: updateProgress,
        });
      }

      setSelectedTask(null);
      setUpdateComment('');
      loadTasks();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit update');
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Datacenter Tickets & Tasks
          </h1>
          <p className="text-sm text-slate-500">
            Total indexed tickets: {total.toLocaleString()} from Huntsville operations
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-sm transition-colors"
        >
          <Plus className="h-4 w-4 mr-1.5" />
          Create Ticket
        </button>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search ticket #, circuit, or notes..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-800"
          />
        </form>

        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
          {/* Status Filter */}
          <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg text-xs font-medium text-slate-600">
            {STATUS_OPTIONS.map((st) => (
              <button
                key={st}
                onClick={() => {
                  setStatus(st);
                  setPage(1);
                }}
                className={`px-2.5 py-1 rounded-md capitalize transition-colors ${
                  status === st ? 'bg-white text-indigo-700 shadow-sm font-semibold' : 'hover:text-slate-900'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          {/* Priority Filter */}
          <select
            value={priority}
            onChange={(e) => {
              setPriority(e.target.value);
              setPage(1);
            }}
            className="bg-slate-50 border border-slate-200 rounded-lg text-xs px-2.5 py-2 text-slate-700 focus:outline-none"
          >
            {PRIORITY_OPTIONS.map((pr) => (
              <option key={pr} value={pr}>
                Priority: {pr.toUpperCase()}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tasks Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="h-64 flex items-center justify-center">
            <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No tickets match your search filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-semibold">
                <tr>
                  <th className="py-3 px-4">Ticket & Circuit</th>
                  <th className="py-3 px-4">Assignee</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Logged / Est</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tasks.map((task) => (
                  <tr key={task.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-slate-900 text-sm max-w-sm truncate">
                        {task.title}
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1 max-w-sm">
                        {task.description}
                      </p>
                      {task.blocked_reason && (
                        <span className="inline-block mt-1 text-[10px] text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                          Blocker: {task.blocked_reason}
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 font-medium text-slate-700">
                      {task.assignee_name || 'Unassigned'}
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full font-semibold text-[11px] capitalize ${
                          task.status === 'done'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : task.status === 'blocked'
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : task.status === 'in_progress'
                            ? 'bg-blue-50 text-blue-700 border border-blue-200'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {task.status}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`font-semibold uppercase text-[11px] ${
                          task.priority === 'urgent'
                            ? 'text-rose-600'
                            : task.priority === 'high'
                            ? 'text-amber-600'
                            : 'text-slate-600'
                        }`}
                      >
                        {task.priority}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-slate-600">
                      <strong>{task.actual_hours}h</strong> / {task.estimated_hours}h
                    </td>

                    <td className="py-3.5 px-4 text-slate-500">
                      {task.start_date || 'N/A'}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => {
                          setSelectedTask(task);
                          setUpdateStatus(task.status);
                          setUpdateProgress(task.progress_pct || 100);
                        }}
                        className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-2.5 py-1.5 rounded transition-colors"
                      >
                        Log Work
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-600">
          <div>
            Showing <strong>{(page - 1) * pageSize + 1}</strong> to{' '}
            <strong>{Math.min(page * pageSize, total)}</strong> of <strong>{total}</strong> tickets
          </div>
          <div className="flex items-center space-x-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              className="p-1.5 rounded border bg-white disabled:opacity-40 hover:bg-slate-100"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="font-semibold px-2">
              Page {page} of {totalPages}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              className="p-1.5 rounded border bg-white disabled:opacity-40 hover:bg-slate-100"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Progress & Work Log Modal */}
      {selectedTask && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900 mb-1">
              Log Progress & Hours
            </h3>
            <p className="text-xs text-slate-500 mb-4 truncate">{selectedTask.title}</p>

            <form onSubmit={handleSaveUpdate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase text-slate-600">
                  Status
                </label>
                <select
                  value={updateStatus}
                  onChange={(e) => setUpdateStatus(e.target.value)}
                  className="mt-1 w-full px-3 py-2 border rounded-lg text-sm bg-white"
                >
                  <option value="done">Done / Completed</option>
                  <option value="in_progress">In Progress</option>
                  <option value="blocked">Blocked / Escalated</option>
                  <option value="in_review">In Review</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-600">
                    Hours Logged
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    value={updateHours}
                    onChange={(e) => setUpdateHours(parseFloat(e.target.value))}
                    className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase text-slate-600">
                    Progress %
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={updateProgress}
                    onChange={(e) => setUpdateProgress(parseInt(e.target.value))}
                    className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-slate-600">
                  Update Note / Resolution Comments
                </label>
                <textarea
                  rows={3}
                  required
                  placeholder="Notes on fiber testing, cable swaps, or equipment verification..."
                  value={updateComment}
                  onChange={(e) => setUpdateComment(e.target.value)}
                  className="mt-1 w-full px-3 py-2 border rounded-lg text-sm"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setSelectedTask(null)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg shadow-sm"
                >
                  Save & Recompute Progress
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

