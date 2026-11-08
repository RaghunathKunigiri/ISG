import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/auth/login')) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', newRefreshToken);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }
        processQueue(null, access_token);
        return api(originalRequest);
      } catch (refreshErr) {
        processQueue(refreshErr as Error, null);
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// Endpoints
export const authApi = {
  login: (data: { email: string; password: string; totp_code?: string }) =>
    api.post('/api/v1/auth/login', data),
  me: () => api.get('/api/v1/auth/me'),
  logout: () => api.post('/api/v1/auth/logout'),
};

export const dashboardApi = {
  getMember: () => api.get('/api/v1/dashboards/member'),
  getManager: () => api.get('/api/v1/dashboards/manager'),
  getAdmin: () => api.get('/api/v1/dashboards/admin'),
};

export const projectsApi = {
  list: () => api.get('/api/v1/projects'),
  get: (id: string) => api.get(`/api/v1/projects/${id}`),
  create: (data: any) => api.post('/api/v1/projects', data),
  update: (id: string, data: any) => api.put(`/api/v1/projects/${id}`, data),
  getSnapshots: (id: string) => api.get(`/api/v1/projects/${id}/snapshots`),
};

export const tasksApi = {
  list: (params?: any) => api.get('/api/v1/tasks', { params }),
  get: (id: string) => api.get(`/api/v1/tasks/${id}`),
  create: (data: any) => api.post('/api/v1/tasks', data),
  update: (id: string, data: any) => api.put(`/api/v1/tasks/${id}`, data),
  addUpdate: (id: string, data: any) => api.post(`/api/v1/tasks/${id}/updates`, data),
};

export const timesheetsApi = {
  list: (params?: any) => api.get('/api/v1/timesheets', { params }),
  create: (data: any) => api.post('/api/v1/timesheets', data),
  update: (id: string, data: any) => api.put(`/api/v1/timesheets/${id}`, data),
  approve: (id: string) => api.post(`/api/v1/timesheets/${id}/approve`),
  reject: (id: string, reason?: string) => api.post(`/api/v1/timesheets/${id}/reject`, { reason }),
};

export const attendanceApi = {
  list: (params?: any) => api.get('/api/v1/attendance', { params }),
};

export const reportsApi = {
  getBurndown: (projectId: string) => api.get(`/api/v1/reports/burndown/${projectId}`),
  getUtilization: (params?: any) => api.get('/api/v1/reports/utilization', { params }),
  getSlaBreaches: () => api.get('/api/v1/reports/sla-breaches'),
};

export const auditApi = {
  getLogs: (params?: any) => api.get('/api/v1/audit/logs', { params }),
  getSessions: (params?: any) => api.get('/api/v1/audit/sessions', { params }),
};

export const employeesApi = {
  list: () => api.get('/api/v1/employees'),
  get: (id: string) => api.get(`/api/v1/employees/${id}`),
};

