/**
 * LiveAnalysisPage.jsx
 * --------------------
 * Page 3: Trigger live AWS Cost Explorer ingestion.
 *
 * API call:
 *   POST /api/v1/analyze  (multipart form: data_source=LIVE, start_date, end_date)
 *
 * UI flow: date range inputs → Analyze button → loading → results display
 * ZERO local computation — all analysis done by backend.
 */
import React, { useState } from 'react';
import apiClient from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';

const DEFAULT_START = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];
const DEFAULT_END = new Date().toISOString().split('T')[0];

export default function LiveAnalysisPage() {
    const [startDate, setStartDate] = useState(DEFAULT_START);
    const [endDate, setEndDate] = useState(DEFAULT_END);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);

    const handleAnalyze = async () => {
        setError(null);
        setResult(null);
        setLoading(true);
        try {
            // Must send as multipart/form-data per API spec §5.2
            const form = new FormData();
            form.append('data_source', 'LIVE');
            form.append('start_date', startDate);
            form.append('end_date', endDate);

            const res = await apiClient.post('/analyze', form);
            setResult(res.data.data);
        } catch (err) {
            setError(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <div className="page-header">
                <h1>Live Cloud Analysis</h1>
                <p>Fetch real-time cost data directly from your AWS account via Cost Explorer.</p>
            </div>

            <div className="alert alert-info" style={{ marginBottom: 20 }}>
                <strong>Requirements:</strong> AWS credentials must be configured in the backend
                environment with read-only Cost Explorer permissions.
            </div>

            <div className="card" style={{ maxWidth: 480, marginBottom: 24 }}>
                <div className="form-group">
                    <label className="form-label" htmlFor="live-start-date">Start Date</label>
                    <input id="live-start-date" type="date" className="form-input" value={startDate}
                        onChange={e => setStartDate(e.target.value)} />
                </div>
                <div className="form-group">
                    <label className="form-label" htmlFor="live-end-date">End Date</label>
                    <input id="live-end-date" type="date" className="form-input" value={endDate}
                        onChange={e => setEndDate(e.target.value)} />
                </div>
                <button id="live-analyze-btn" className="btn btn-primary" onClick={handleAnalyze}
                    disabled={loading} style={{ width: '100%' }}>
                    {loading ? 'Running Analysis…' : '▶ Run Live Analysis'}
                </button>
            </div>

            <ErrorBanner error={error} />

            {loading && <LoadingSpinner label="Fetching live AWS data and running analysis…" />}

            {result && !loading && (
                <>
                    <p className="section-title">Analysis Complete</p>
                    <div className="card-grid">
                        <div className="card stat-card">
                            <span className="stat-label">Total Cost</span>
                            <span className="stat-value">${result.summary?.total_cost?.toLocaleString()}</span>
                        </div>
                        <div className="card stat-card">
                            <span className="stat-label">Top Service</span>
                            <span className="stat-value" style={{ fontSize: 15 }}>{result.summary?.top_service}</span>
                        </div>
                        <div className="card stat-card">
                            <span className="stat-label">Recommendations</span>
                            <span className="stat-value">{result.recommendations?.length ?? 0}</span>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
