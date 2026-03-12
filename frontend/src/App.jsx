/**
 * App.jsx
 * --------
 * Application router and navigation shell.
 * Wires the API client token getter to the AuthContext on mount.
 */
import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from './auth/AuthContext';
import { setTokenGetter } from './api/client';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import LiveAnalysisPage from './pages/LiveAnalysisPage';
import UploadReportPage from './pages/UploadReportPage';
import RecommendationsPage from './pages/RecommendationsPage';
import DetailedAnalyticsPage from './pages/DetailedAnalyticsPage';

function Shell() {
    const { user, signOut, getToken } = useAuth();

    useEffect(() => {
        setTokenGetter(getToken);
    }, [getToken]);

    return (
        <div className="app-layout">
            <aside className="sidebar">
                <div className="sidebar-logo">
                    ☁ Cloud Cost Advisor
                    <span>Advisory Platform v1.0</span>
                </div>
                <nav className="sidebar-nav" aria-label="Main navigation">
                    <NavLink to="/dashboard" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
                        📊 Dashboard
                    </NavLink>
                    <NavLink to="/live-analysis" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
                        🔴 Live Analysis
                    </NavLink>
                    <NavLink to="/upload" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
                        📂 Upload Report
                    </NavLink>
                    <NavLink to="/recommendations" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
                        💡 Recommendations
                    </NavLink>
                    <NavLink to="/analytics" className={({ isActive }) => 'nav-link' + (isActive ? ' active' : '')}>
                        📈 Detailed Analytics
                    </NavLink>
                </nav>
                <div className="sidebar-footer">
                    <p className="user-info">{user?.email}</p>
                    <button className="btn btn-secondary" onClick={signOut} id="sign-out-btn">
                        Sign Out
                    </button>
                </div>
            </aside>
            <main className="main-content">
                <Routes>
                    <Route path="/dashboard" element={<DashboardPage />} />
                    <Route path="/live-analysis" element={<LiveAnalysisPage />} />
                    <Route path="/upload" element={<UploadReportPage />} />
                    <Route path="/recommendations" element={<RecommendationsPage />} />
                    <Route path="/analytics" element={<DetailedAnalyticsPage />} />
                    <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Routes>
            </main>
        </div>
    );
}

export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route element={<ProtectedRoute />}>
                    <Route path="/*" element={<Shell />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}
