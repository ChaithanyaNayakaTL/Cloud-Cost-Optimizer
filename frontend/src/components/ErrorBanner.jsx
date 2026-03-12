/**
 * ErrorBanner.jsx
 * ----------------
 * Displays structured API error responses to the user.
 * Handles both plain {code, message} objects (from axios interceptor)
 * and Error instances.
 */
import React from 'react';

export default function ErrorBanner({ error }) {
    if (!error) return null;

    const code = error?.code || null;
    const message =
        typeof error === 'string'
            ? error
            : error.message || 'An unexpected error occurred.';

    return (
        <div className="error-banner" role="alert">
            <span className="error-icon">⚠</span>
            <span>
                {code && (
                    <strong style={{ marginRight: 6, opacity: 0.75, fontSize: '0.85em', fontFamily: 'monospace' }}>
                        [{code}]
                    </strong>
                )}
                {message}
            </span>
        </div>
    );
}
