'use client';

import dynamic from 'next/dynamic';

// Import komponen LogViewer tadi, matikan SSR (Server Side Rendering)
const LogViewer = dynamic(() => import('@/components/ui/LogViewer'), {
    ssr: false, // <--- INI KUNCINYA BANG!
    loading: () => (
        <div className="p-8 text-slate-500 flex items-center gap-2">
            <div className="w-4 h-4 border-2 border-slate-500 border-t-transparent rounded-full animate-spin"></div>
            Loading Terminal...
        </div>
    )
});

export default function LogsPage() {
    return <LogViewer />;
}