import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi } from '../lib/api';

export interface Employee {
  id: string;
  org_id: string;
  employee_code: string;
  full_name: string;
  email: string;
  role_id: string;
  role_name: string;
  department: string;
  designation: string;
  location?: string;
  mfa_enabled: boolean;
  permissions: string[];
}

interface AuthContextType {
  user: Employee | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string, totpCode?: string) => Promise<{ requiresMfa?: boolean }>;
  logout: () => void;
  hasPermission: (perm: string) => boolean;
  hasRole: (role: string | string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<Employee | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('access_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchMe = async () => {
      const storedToken = localStorage.getItem('access_token');
      if (!storedToken) {
        setIsLoading(false);
        return;
      }
      try {
        // Decode permissions from stored token payload (base64 middle segment)
        let tokenPerms: string[] = [];
        let tokenRole = '';
        try {
          const payload = JSON.parse(atob(storedToken.split('.')[1]));
          tokenPerms = payload.permissions || [];
          tokenRole = payload.role || '';
        } catch (_) {}

        const res = await authApi.me();
        setUser({
          ...res.data,
          role_name: res.data.role_name || tokenRole,
          permissions: tokenPerms,
          mfa_enabled: false,
        });
      } catch (err) {
        console.error('Failed to load user session', err);
        localStorage.clear();
        setUser(null);
        setToken(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMe();
  }, []);

  const login = async (email: string, password: string, totpCode?: string) => {
    try {
      const res = await authApi.login({ email, password, totp_code: totpCode });
      const {
        access_token,
        refresh_token,
        employee_id,
        employee_name,
        role,
        permissions,
        org_id,
      } = res.data;

      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      setToken(access_token);

      // Build user profile from the flat TokenOut response
      // Then enrich with /me for department, designation, etc.
      const baseUser: Employee = {
        id: employee_id,
        org_id: org_id,
        employee_code: '',
        full_name: employee_name,
        email: email.toLowerCase().trim(),
        role_id: '',
        role_name: role,
        department: '',
        designation: '',
        mfa_enabled: false,
        permissions: permissions || [],
      };
      setUser(baseUser);

      // Enrich with full profile from /me (non-blocking)
      try {
        const meRes = await authApi.me();
        setUser({
          ...meRes.data,
          role_name: meRes.data.role_name || role,
          permissions: permissions || [],
          mfa_enabled: false,
        });
      } catch (_) {
        // Keep base user if /me fails
      }

      return {};
    } catch (err: any) {
      const detail = err.response?.data?.detail || '';
      if (err.response?.status === 401 && (detail.includes('MFA') || detail.includes('TOTP'))) {
        return { requiresMfa: true };
      }
      throw err;
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (err) {
      // ignore logout network errors
    } finally {
      localStorage.clear();
      setUser(null);
      setToken(null);
      window.location.href = '/login';
    }
  };

  const hasPermission = (perm: string): boolean => {
    if (!user) return false;
    if (user.role_name === 'admin') return true;
    return user.permissions?.includes(perm) || false;
  };

  const hasRole = (role: string | string[]): boolean => {
    if (!user) return false;
    if (Array.isArray(role)) {
      return role.includes(user.role_name);
    }
    return user.role_name === role;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        hasPermission,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

