/**
 * AuthContext.jsx
 * ---------------
 * In-memory authentication state manager.
 *
 * Security design:
 *   - Token stored ONLY in React state (in-memory)
 *   - NEVER written to localStorage or sessionStorage
 *   - Unauthenticated state is the default before Firebase responds
 *   - Token auto-refreshed via Firebase onIdTokenChanged listener
 */
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
    signInWithPopup,
    signOut as firebaseSignOut,
    onIdTokenChanged,
} from 'firebase/auth';
import { auth, googleProvider } from '../firebase';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);  // in-memory only
    const [loading, setLoading] = useState(true);

    // Subscribe to token changes (handles auto-refresh)
    useEffect(() => {
        const unsubscribe = onIdTokenChanged(auth, async (firebaseUser) => {
            if (firebaseUser) {
                const idToken = await firebaseUser.getIdToken();
                setUser(firebaseUser);
                setToken(idToken);       // held in React state — never in storage
            } else {
                setUser(null);
                setToken(null);
            }
            setLoading(false);
        });
        return unsubscribe;
    }, []);

    const signInWithGoogle = useCallback(async () => {
        await signInWithPopup(auth, googleProvider);
    }, []);

    const signOut = useCallback(async () => {
        await firebaseSignOut(auth);
    }, []);

    const getToken = useCallback(() => token, [token]);

    return (
        <AuthContext.Provider value={{ user, loading, getToken, signInWithGoogle, signOut }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
    return ctx;
}
