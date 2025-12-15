import Sidebar from '@/components/layout/Sidebar';
import AuthGuard from '@/components/auth/AuthGuard';

export default function DashboardLayout({ children, }: {
    children: React.ReactNode;
}) {
    return (
        // [BARU] Bungkus dengan AuthGuard
        <AuthGuard>
            <div className="min-h-screen bg-slate-950 text-slate-200">
                {/* Sidebar Tetap */}
                <Sidebar/>

                {/* Konten Utama */}
                <main className="ml-64 p-8">
                    {children}
                </main>
            </div>
        </AuthGuard>
    );
}