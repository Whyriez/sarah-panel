'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { Lock, User, Server } from 'lucide-react';

export default function LoginPage() {
    const router = useRouter();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            // Data harus dikirim sebagai Form Data (standar OAuth2 FastAPI)
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            // Tembak endpoint Auth Backend
            const res = await api.post('/auth/token', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data', // Wajib untuk OAuth2
                },
            });

            // Jika sukses, kita dapat access_token
            const { access_token } = res.data;

            // SIMPAN TOKEN (Di LocalStorage buat sementara)
            localStorage.setItem('token', access_token);

            // Redirect ke Dashboard (Nanti kita buat halamannya)
            alert("Login Sukses! Token tersimpan.");
            router.push('/dashboard');

        } catch (err: any) {
            console.error(err);
            if (err.response?.status === 401) {
                setError('Username atau Password salah!');
            } else {
                setError('Terjadi kesalahan server.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
            <div className="w-full max-w-md p-8 bg-slate-900 rounded-2xl shadow-xl border border-slate-800">
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-600/20 text-blue-500 mb-4">
                        <Server size={32} />
                    </div>
                    <h1 className="text-3xl font-bold text-white">AlimPanel</h1>
                    <p className="text-slate-400 mt-2">Manage your server like a Pro</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-6">
                    {error && (
                        <div className="p-3 text-sm text-red-400 bg-red-900/20 border border-red-900/50 rounded-lg">
                            {error}
                        </div>
                    )}

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Username</label>
                        <div className="relative">
                            <User className="absolute left-3 top-3 text-slate-500" size={18} />
                            <input
                                type="text"
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 pl-10 pr-4 focus:outline-none focus:border-blue-500 transition-colors"
                                placeholder="admin"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-3 text-slate-500" size={18} />
                            <input
                                type="password"
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 pl-10 pr-4 focus:outline-none focus:border-blue-500 transition-colors"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? 'Connecting...' : 'Sign In to Console'}
                    </button>
                </form>
            </div>
        </div>
    );
}