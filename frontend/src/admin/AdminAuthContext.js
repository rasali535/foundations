import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AdminAuthContext = createContext(null);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
export const API_BASE = `${BACKEND_URL}/api`;

// Axios instance with credentials enabled for session cookies
export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const AdminAuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const res = await api.get('/me');
      setUser(res.data);
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const login = async (username, password) => {
    const res = await api.post('/login', { username, password });
    setUser(res.data);
    return res.data;
  };

  const logout = async () => {
    try {
      await api.post('/logout');
    } catch (err) {
      console.warn('Logout error:', err);
    } finally {
      setUser(null);
    }
  };

  return (
    <AdminAuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
      {children}
    </AdminAuthContext.Provider>
  );
};

export const useAdminAuth = () => {
  const context = useContext(AdminAuthContext);
  if (!context) {
    throw new Error('useAdminAuth must be used within an AdminAuthProvider');
  }
  return context;
};
