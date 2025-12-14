import Sidebar from '@/components/layout/Sidebar';

export default function DashboardLayout({ children, }: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen bg-slate-950 text-slate-200">
            {/* Sidebar Tetap */}
            <Sidebar/>

            {/* Konten Utama (Bergeser 64 unit ke kanan karena ada sidebar) */}
            <main className="ml-64 p-8">
                {children}
            </main>
        </div>
    );
}