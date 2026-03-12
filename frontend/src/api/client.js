/**
 * client.js
 * ----------
 * Axios instance pre-configured for the Cloud Cost Advisor API.
 *
 * Responsibilities:
 *   - Inject Authorization: Bearer <token> header from in-memory auth state
 *   - Handle 401 → redirect to /login
 *   - Handle 422 → re-throw with parsed validation error for UI display
 *   - NEVER log raw API response bodies (security)
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const apiClient = axios.create({
    baseURL: `${API_BASE}/api/v1`,
    timeout: 30000,
});

// Injected from AuthContext at setup time (called in App.jsx)
let _getToken = () => null;

export function setTokenGetter(fn) {
    _getToken = fn;
}

// ─── Request interceptor: attach JWT ─────────────────────────────────────────
apiClient.interceptors.request.use((config) => {
    const token = _getToken();
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
});

// ─── Response interceptor: handle error codes ─────────────────────────────────
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (!error.response) {
            return Promise.reject({ code: 'NETWORK_ERROR', message: 'Network error. Please check your connection.' });
        }
        const { status, data } = error.response;
        // FastAPI puts HTTPException detail under data.detail;
        // if detail is a structured object we set {status, error: {code, message}}
        const detail = data?.detail;
        const backendMessage =
            (typeof detail === 'object' && detail?.error?.message) ||
            (typeof detail === 'string' && detail) ||
            data?.error?.message ||
            null;

        if (status === 401) {
            window.location.href = '/login';
            return Promise.reject({ code: 'UNAUTHORIZED', message: 'Session expired. Please log in again.' });
        }
        if (status === 403) {
            return Promise.reject({ code: 'FORBIDDEN', message: 'You do not have permission to perform this action.' });
        }
        if (status === 422) {
            const message = backendMessage || 'Validation error. Please check the uploaded file.';
            return Promise.reject({ code: 'VALIDATION_ERROR', message });
        }
        if (status === 413) {
            return Promise.reject({ code: 'FILE_TOO_LARGE', message: 'File exceeds the maximum allowed size.' });
        }
        if (status === 503) {
            const message = backendMessage || 'Service temporarily unavailable.';
            return Promise.reject({ code: 'SERVICE_UNAVAILABLE', message });
        }
        const message = backendMessage || 'An unexpected server error occurred.';
        return Promise.reject({ code: 'SERVER_ERROR', message });
    }
);

export default apiClient;
