/**
 * UploadReportPage.jsx
 * --------------------
 * Page 4: Upload a billing CSV file for offline analysis.
 *
 * API call:
 *   POST /api/v1/analyze  (multipart form: data_source=UPLOAD, file=<csv>)
 *
 * Supported formats: AWS billing CSV export with columns:
 *   service, region, usage_type, usage_amount, cost_amount, timestamp
 *
 * Security:
 *   - File size limit enforced by backend (413 mapped to friendly message)
 *   - No file stored on client after upload
 */
import React, { useState, useRef } from 'react';
import apiClient from '../api/client';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';

const EXPECTED_COLUMNS = ['service', 'region', 'usage_type', 'usage_amount', 'cost_amount', 'timestamp'];

export default function UploadReportPage() {
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [result, setResult] = useState(null);
    const [dragOver, setDragOver] = useState(false);
    const fileRef = useRef();

    const handleFile = (f) => {
        if (!f) return;
        if (!f.name.endsWith('.csv')) {
            setError({ message: 'Only CSV files are supported.' });
            return;
        }
        setFile(f);
        setError(null);
        setResult(null);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        handleFile(e.dataTransfer.files[0]);
    };

    const handleUpload = async () => {
        if (!file) return;
        setError(null);
        setResult(null);
        setLoading(true);
        try {
            const form = new FormData();
            form.append('data_source', 'UPLOAD');
            form.append('file', file);

            const res = await apiClient.post('/analyze', form, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
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
                <h1>Upload Billing Report</h1>
                <p>Analyse offline CSV billing exports from AWS or Azure.</p>
            </div>

            <div className="card" style={{ maxWidth: 560, marginBottom: 24 }}>
                <p className="section-title" style={{ marginTop: 0 }}>Expected CSV Columns</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
                    {EXPECTED_COLUMNS.map(col => (
                        <code key={col} style={{
                            background: 'var(--bg-primary)', border: '1px solid var(--border)',
                            borderRadius: 4, padding: '2px 8px', fontSize: 12, color: 'var(--accent)'
                        }}>{col}</code>
                    ))}
                </div>

                <label
                    className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
                    htmlFor="csv-file-input"
                    onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                >
                    <input
                        id="csv-file-input"
                        ref={fileRef}
                        type="file"
                        accept=".csv,text/csv"
                        onChange={e => handleFile(e.target.files[0])}
                    />
                    {file ? (
                        <div>
                            <p style={{ color: 'var(--accent-success)', fontWeight: 600 }}>✓ {file.name}</p>
                            <p style={{ fontSize: 12, marginTop: 4 }}>{(file.size / 1024).toFixed(1)} KB</p>
                        </div>
                    ) : (
                        <div>
                            <p>Drop your CSV file here, or <span style={{ color: 'var(--accent)' }}>browse</span></p>
                            <p style={{ fontSize: 12, marginTop: 4, color: 'var(--text-muted)' }}>Maximum file size: 10 MB</p>
                        </div>
                    )}
                </label>

                <button id="upload-analyze-btn" className="btn btn-primary"
                    onClick={handleUpload} disabled={!file || loading}
                    style={{ width: '100%', marginTop: 16 }}>
                    {loading ? 'Analysing…' : '▶ Analyse File'}
                </button>
            </div>

            <ErrorBanner error={error} />

            {loading && <LoadingSpinner label="Processing uploaded billing report…" />}

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

                    {result.recommendations?.length > 0 && (
                        <>
                            <p className="section-title">Recommendations</p>
                            {result.recommendations.map((rec, i) => (
                                <div key={i} className="rec-card">
                                    <div className="rec-card-header">
                                        <div>
                                            <p className="rec-issue">{rec.issue_type}</p>
                                            <p className="rec-resource">{rec.resource_id}</p>
                                        </div>
                                        <div style={{ textAlign: 'right' }}>
                                            <p className="rec-savings">−${rec.estimated_monthly_savings?.toFixed(2)}/mo</p>
                                            <span className={`badge badge-${rec.risk_level?.toLowerCase()}`}>{rec.risk_level} Risk</span>
                                        </div>
                                    </div>
                                    <p className="rec-action">{rec.suggested_action}</p>
                                    <p className="rec-explanation">{rec.explanation}</p>
                                </div>
                            ))}
                        </>
                    )}
                </>
            )}
        </div>
    );
}
