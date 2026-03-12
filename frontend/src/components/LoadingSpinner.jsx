/**
 * LoadingSpinner.jsx
 */
import React from 'react';

export default function LoadingSpinner({ label = 'Processing…' }) {
    return (
        <div className="loading-panel" aria-busy="true">
            <div className="spinner" />
            <p>{label}</p>
        </div>
    );
}
