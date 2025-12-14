'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function DashboardPage() {
    const router = useRouter();
    const [token, setToken] = useState<string | null>(null);

    useEffect(() => {
        // Cek apakah user punya token?
        const storedToken = localStorage.getItem('token');
        if (!storedToken) {
            router.push('/login'); // Tendang balik kalau gak login
        } else {
            setToken(storedToken);
        }
    }, [router]);

    if (!token) return <div className="p-10 text-white">Checking auth...</div>;

    return (
        <div className="min-h-screen bg-slate-950 text-white p-10">
            <h1 className="text-3xl font-bold mb-4">Dashboard AlimPanel</h1>
            <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl">
                <p>Halo, Selamat datang di panel hosting Anda!</p>
                <div className="mt-4 p-4 bg-slate-800 rounded-lg overflow-hidden text-xs font-mono break-all">
                    Token Anda: {token}
                </div>

                <button
                    onClick={() => {
                        localStorage.removeItem('token');
                        router.push('/login');
                    }}
                    className="mt-6 px-4 py-2 bg-red-600 rounded hover:bg-red-700"
                >
                    Logout
                </button>
            </div>
        </div>
    );
}