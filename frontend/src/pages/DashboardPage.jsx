/**
 * DashboardPage.jsx
 * -----------------
 * Page 2: High-level cloud cost summary.
 *
 * API calls:
 *   GET /api/v1/summary?start_date=&end_date=
 *   GET /api/v1/cost-breakdown?start_date=&end_date=
 *
 * Displays: summary stats, provider cost breakdown table, monthly trend chart.
 * All data comes from backend — ZERO local computation.
 */
import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import apiClient from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';

const DEFAULT_START = new Date(Date.now() - 30 * 86400000).toISOString().split('T')[0];
const DEFAULT_END = new Date().toISOString().split('T')[0];

export default function DashboardPage() {
    const [summary, setSummary] = useState(null);
    const [breakdown, setBreakdown] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [dataSource, setDataSource] = useState(null);
    const [startDate, setStartDate] = useState(DEFAULT_START);
    const [endDate, setEndDate] = useState(DEFAULT_END);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const params = `?start_date=${startDate}&end_date=${endDate}`;
            const [sumRes, brkRes] = await Promise.all([
                apiClient.get(`/summary${params}`),
                apiClient.get(`/cost-breakdown${params}`),
            ]);
            setSummary(sumRes.data.data);
            setBreakdown(brkRes.data.data || []);
            setDataSource(sumRes.data.metadata?.data_source || null);
        } catch (err) {
            setError(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchData(); }, []);

    return (
        <div>
            <div className="page-header">
                <h1>Dashboard</h1>
                <p>Cloud cost summary for the selected date range</p>
            </div>

            {/* Date range controls */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 20, alignItems: 'flex-end' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">Start Date</label>
                    <input id="dashboard-start-date" type="date" className="form-input" value={startDate}
                        onChange={e => setStartDate(e.target.value)} />
                </div>
                <div className="form-group" style={{ marginBottom: 0 }}>
                    <label className="form-label">End Date</label>
                    <input id="dashboard-end-date" type="date" className="form-input" value={endDate}
                        onChange={e => setEndDate(e.target.value)} />
                </div>
                <button id="dashboard-refresh-btn" className="btn btn-primary" onClick={fetchData} disabled={loading}>
                    Refresh
                </button>
            </div>

            <ErrorBanner error={error} />

            {/* Demo mode notice */}
            {dataSource === 'MOCK' && !error && (
                <div style={{
                    background: 'rgba(251, 191, 36, 0.12)',
                    border: '1px solid rgba(251, 191, 36, 0.4)',
                    borderRadius: 8,
                    padding: '10px 16px',
                    marginBottom: 20,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    color: '#fbbf24',
                    fontSize: '0.9rem',
                }}>
                    <span>🔆</span>
                    <span>
                        <strong>Demo Mode</strong> — Showing sample data.
                        Add your AWS credentials to <code style={{ opacity: 0.8 }}>backend/.env.local</code> to see live cost data.
                    </span>
                </div>
            )}

            {loading ? <LoadingSpinner label="Loading cost summary…" /> : (
                <>
                    {/* Summary cards */}
                    {summary ? (
                        <div className="card-grid">
                            <div className="card stat-card">
                                <span className="stat-label">Total Cost</span>
                                <span className="stat-value">${summary.total_cost?.toLocaleString()}</span>
                            </div>
                            <div className="card stat-card">
                                <span className="stat-label">Avg Daily Cost</span>
                                <span className="stat-value">${summary.average_daily_cost?.toFixed(2)}</span>
                            </div>
                            <div className="card stat-card">
                                <span className="stat-label">Top Service</span>
                                <span className="stat-value" style={{ fontSize: 16 }}>{summary.top_service}</span>
                                <span className="stat-sub">${summary.top_service_cost?.toFixed(2)}</span>
                            </div>
                        </div>
                    ) : (
                        <div className="empty-state"><h3>No summary data available for this range.</h3></div>
                    )}

                    {/* Cost breakdown table */}
                    {breakdown.length > 0 && (
                        <>
                            <p className="section-title">Service Cost Breakdown</p>
                            <div className="card" style={{ marginBottom: 24 }}>
                                <table className="data-table">
                                    <thead>
                                        <tr>
                                            <th>Service</th>
                                            <th>Cost (USD)</th>
                                            <th>% of Total</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {breakdown.map(item => (
                                            <tr key={item.service}>
                                                <td>{item.service}</td>
                                                <td>${item.cost?.toFixed(2)}</td>
                                                <td>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                        <div className="progress-bar-wrapper" style={{ flex: 1 }}>
                                                            <div className="progress-bar-fill" style={{ width: `${item.percentage}%` }} />
                                                        </div>
                                                        <span style={{ width: 38, textAlign: 'right', color: 'var(--text-secondary)' }}>
                                                            {item.percentage?.toFixed(1)}%
                                                        </span>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </>
            )}
        </div>
    );
}
