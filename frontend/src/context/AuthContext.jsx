import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = sessionStorage.getItem('case_connect_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => sessionStorage.getItem('case_connect_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const verifyToken = async () => {
      const savedToken = sessionStorage.getItem('case_connect_token');
      if (savedToken) {
        try {
          const profile = await authApi.getMe();
          setUser(profile);
          sessionStorage.setItem('case_connect_user', JSON.stringify(profile));
        } catch (err) {
          setUser(null);
          setToken(null);
          sessionStorage.removeItem('case_connect_token');
          sessionStorage.removeItem('case_connect_user');
        }
      }
      setLoading(false);
    };
    verifyToken();
  }, []);

  const login = async (username, password) => {
    const data = await authApi.login(username, password);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const quickLogin = async (role = 'investigator') => {
    const data = await authApi.quickLogin(role);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (e) {
      // Ignore network errors on logout
    } finally {
      setUser(null);
      setToken(null);
      sessionStorage.removeItem('case_connect_token');
      sessionStorage.removeItem('case_connect_user');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isAdmin: user?.role === 'admin',
        isInvestigator: user?.role === 'investigator',
        isViewer: user?.role === 'viewer',
        loading,
        login,
        quickLogin,
        logout,
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
