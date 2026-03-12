/**
 * DetailedAnalyticsPage.jsx
 * -------------------------
 * Page 6: In-depth cost charts — by service, by region, by day.
 *
 * API calls:
 *   POST /api/v1/analyze  (LIVE mode for breakdown + daily trend)
 *
 * Charts: Recharts BarChart (by service), LineChart (daily trend)
 * All data sourced from backend — zero local computation.
 */
import React, { useState } from 'react';
import {
    BarChart, Bar, LineChart, Line, XAxis, YAxis,
    Tooltip, CartesianGrid, ResponsiveContainer, Legend, Cell,
} from 'recharts';
import apiClient from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';

const DEFAULT_START = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];
const DEFAULT_END = new Date().toISOString().split('T')[0];

const CHART_COLORS = ['#4f7cff', '#34d399', '#fbbf24', '#f87171', '#a78bfa', '#38bdf8'];

const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 6, padding: '8px 12px' }}>
            <p style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{label}</p>
            {payload.map((p, i) => (
                <p key={i} style={{ color: p.color, fontWeight: 600, fontSize: 13 }}>
                    ${typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
                </p>
            ))}
        </div>
    );
};

export default function DetailedAnalyticsPage() {
    const [startDate, setStartDate] = useState(DEFAULT_START);
    const [endDate, setEndDate] = useState(DEFAULT_END);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [breakdown, setBreakdown] = useState(null);
    const [trend, setTrend] = useState(null);

    const handleAnalyze = async () => {
        setError(null);
        setBreakdown(null);
        setTrend(null);
        setLoading(true);
        try {
            const form = new FormData();
            form.append('data_source', 'LIVE');
            form.append('start_date', startDate);
            form.append('end_date', endDate);

            const res = await apiClient.post('/analyze', form);
            setBreakdown(res.data.data.cost_breakdown || []);
            setTrend(res.data.data.daily_trend || []);
        } catch (err) {
            setError(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <div className="page-header">
                <h1>Detailed Analytics</h1>
                <p>Cost by service and daily spend trend for the selected period.</p>
            </div>

            <div style={{ display: 'flex', gap: 12, marginBottom: 20, alignItems: 'flex-end' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">Start Date</label>
                    <input id="analytics-start-date" type="date" className="form-input" value={startDate}
                        onChange={e => setStartDate(e.target.value)} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">End Date</label>
                    <input id="analytics-end-date" type="date" className="form-input" value={endDate}
                        onChange={e => setEndDate(e.target.value)} />
                </div>
                <button id="analytics-run-btn" className="btn btn-primary" onClick={handleAnalyze} disabled={loading}>
                    {loading ? 'Analysing…' : '▶ Run Analysis'}
                </button>
            </div>

            <ErrorBanner error={error} />
            {loading && <LoadingSpinner label="Running detailed analytics…" />}

            {breakdown && !loading && (
                <>
                    {breakdown.length === 0 ? (
                        <div className="empty-state"><h3>No data for this range.</h3></div>
                    ) : (
                        <div className="chart-row">
                            {/* Cost by Service */}
                            <div className="card">
                                <p className="section-title" style={{ marginTop: 0 }}>Cost by Service (USD)</p>
                                <div className="chart-container">
                                    <ResponsiveContainer width="100%" height={260}>
                                        <BarChart data={breakdown} margin={{ top: 5, right: 10, left: 0, bottom: 60 }}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                            <XAxis dataKey="service" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                                                angle={-35} textAnchor="end" interval={0} />
                                            <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                                                tickFormatter={v => `$${v}`} />
                                            <Tooltip content={<CustomTooltip />} />
                                            <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
                                                {breakdown.map((_, i) => (
                                                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                                                ))}
                                            </Bar>
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            {/* Daily Trend */}
                            <div className="card">
                                <p className="section-title" style={{ marginTop: 0 }}>Daily Spend Trend (USD)</p>
                                <div className="chart-container">
                                    <ResponsiveContainer width="100%" height={260}>
                                        <LineChart data={trend || []} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                                            <XAxis dataKey="date" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }}
                                                tickFormatter={d => d?.slice(5)} />
                                            <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                                                tickFormatter={v => `$${v}`} />
                                            <Tooltip content={<CustomTooltip />} />
                                            <Line type="monotone" dataKey="cost" stroke="var(--accent)"
                                                strokeWidth={2} dot={false} />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
