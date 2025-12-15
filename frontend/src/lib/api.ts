import axios from 'axios';

// Gunakan environment variable, fallback ke localhost hanya untuk dev
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.request.use((config) => {
    // Pastikan kode jalan di browser (bukan server)
    if (typeof window !== 'undefined') {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Jika error 401 (Unauthorized) dari backend
        if (typeof window !== 'undefined' && error.response?.status === 401) {
            console.warn("Session expired. Redirecting to login...");

            // Hapus token busuk
            localStorage.removeItem('token');

            // Redirect paksa ke login (window.location lebih aman buat reset state dibanding router)
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);

export default api;