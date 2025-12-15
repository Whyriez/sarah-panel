'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const [isAuthorized, setIsAuthorized] = useState(false);

    useEffect(() => {
        // Cek apakah ada token di localStorage
        const token = localStorage.getItem('token');

        if (!token) {
            // Kalau gak ada, tendang ke login
            router.push('/login');
        } else {
            // Kalau ada, izinkan masuk
            setIsAuthorized(true);
        }
    }, [router]);

    // Selama belum authorized, jangan tampilkan apa-apa (atau tampilkan Loading Spinner)
    if (!isAuthorized) {
        return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-500">Checking access...</div>;
    }

    return <>{children}</>;
}