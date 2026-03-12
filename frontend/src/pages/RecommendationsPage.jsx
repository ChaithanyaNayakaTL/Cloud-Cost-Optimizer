/**
 * RecommendationsPage.jsx
 * -----------------------
 * Page 5: Advisory optimization recommendations from live AWS data.
 *
 * API call:
 *   GET /api/v1/recommendations?start_date=&end_date=
 *
 * Displays: recommendation list with resource, issue, action, savings, risk.
 * All recommendations are advisory only — no destructive actions performed.
 */
import React, { useState } from 'react';
import apiClient from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';

const DEFAULT_START = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];
const DEFAULT_END = new Date().toISOString().split('T')[0];

export default function RecommendationsPage() {
    const [startDate, setStartDate] = useState(DEFAULT_START);
    const [endDate, setEndDate] = useState(DEFAULT_END);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [recs, setRecs] = useState(null);
    const [meta, setMeta] = useState(null);

    const handleFetch = async () => {
        setError(null);
        setRecs(null);
        setLoading(true);
        try {
            const res = await apiClient.get(
                `/recommendations?start_date=${startDate}&end_date=${endDate}`
            );
            setRecs(res.data.data || []);
            setMeta(res.data.metadata);
        } catch (err) {
            setError(err);
        } finally {
            setLoading(false);
        }
    };

    const riskClass = (level) => {
        if (!level) return '';
        return `badge-${level.toLowerCase()}`;
    };

    return (
        <div>
            <div className="page-header">
                <h1>Recommendations</h1>
                <p>Advisory cost optimisation suggestions based on live AWS data.</p>
            </div>

            <div style={{ display: 'flex', gap: 12, marginBottom: 20, alignItems: 'flex-end' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">Start Date</label>
                    <input id="rec-start-date" type="date" className="form-input" value={startDate}
                        onChange={e => setStartDate(e.target.value)} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">End Date</label>
                    <input id="rec-end-date" type="date" className="form-input" value={endDate}
                        onChange={e => setEndDate(e.target.value)} />
                </div>
                <button id="rec-fetch-btn" className="btn btn-primary" onClick={handleFetch} disabled={loading}>
                    {loading ? 'Loading…' : 'Get Recommendations'}
                </button>
            </div>

            <ErrorBanner error={error} />

            {loading && <LoadingSpinner label="Analysing cloud spend for optimisation opportunities…" />}

            {recs !== null && !loading && (
                <>
                    {meta && (
                        <div className="card stat-card" style={{ marginBottom: 20, maxWidth: 280 }}>
                            <span className="stat-label">Total Estimated Savings</span>
                            <span className="stat-value" style={{ color: 'var(--accent-success)' }}>
                                ${meta.total_estimated_savings?.toFixed(2)}/mo
                            </span>
                        </div>
                    )}

                    {recs.length === 0 ? (
                        <div className="empty-state">
                            <h3>No Recommendations</h3>
                            <p>No actionable optimisation opportunities were found for this period.</p>
                        </div>
                    ) : (
                        <>
                            <p className="section-title">{recs.length} recommendation{recs.length !== 1 ? 's' : ''} found</p>
                            {recs.map((rec, i) => (
                                <article key={i} className="rec-card" aria-label={`Recommendation ${i + 1}`}>
                                    <div className="rec-card-header">
                                        <div>
                                            <p className="rec-issue">{rec.issue_type}</p>
                                            <p className="rec-resource">Resource: {rec.resource_id}</p>
                                        </div>
                                        <div style={{ textAlign: 'right' }}>
                                            <p className="rec-savings">−${rec.estimated_monthly_savings?.toFixed(2)}/mo</p>
                                            <span className={`badge ${riskClass(rec.risk_level)}`}>{rec.risk_level} Risk</span>
                                        </div>
                                    </div>
                                    <p className="rec-action"><strong>Action:</strong> {rec.suggested_action}</p>
                                    <p className="rec-explanation">{rec.explanation}</p>
                                </article>
                            ))}
                        </>
                    )}
                </>
            )}
        </div>
    );
}
