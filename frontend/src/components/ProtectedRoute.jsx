/**
 * ProtectedRoute.jsx
 * -------------------
 * Guards all pages that require authentication.
 * Redirects unauthenticated users to /login.
 * Shows a loading spinner while auth state is resolving.
 */
import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export default function ProtectedRoute() {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div className="loading-screen">
                <div className="spinner" aria-label="Loading" />
                <p>Verifying session…</p>
            </div>
        );
    }

    return user ? <Outlet /> : <Navigate to="/login" replace />;
}
