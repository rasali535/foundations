import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const HRAuthContext = createContext(null);

export const hrApi = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL || ''}/api`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const HRAuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const res = await hrApi.get('/hr/me');
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
    const res = await hrApi.post('/login', { username, password });
    if (res.data.role !== 'hr_admin' && res.data.role !== 'hr_viewer' && res.data.role !== 'super_admin') {
      await hrApi.post('/logout');
      throw new Error('This portal is restricted to authorised Corporate HR accounts.');
    }
    await checkAuth();
    return res.data;
  };

  const logout = async () => {
    try {
      await hrApi.post('/logout');
    } catch (err) {
      console.warn('Logout request warning:', err);
    }
    setUser(null);
  };

  return (
    <HRAuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
      {children}
    </HRAuthContext.Provider>
  );
};

export const useHRAuth = () => {
  const context = useContext(HRAuthContext);
  if (!context) {
    throw new Error('useHRAuth must be used within an HRAuthProvider');
  }
  return context;
};
