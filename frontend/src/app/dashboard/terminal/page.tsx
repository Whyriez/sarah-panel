'use client';

import dynamic from 'next/dynamic';

// Import komponen TerminalView secara dynamic (SSR False)
// Ini mencegah error "self is not defined" saat build
const TerminalView = dynamic(() => import('@/components/ui/TerminalView'), {
    ssr: false,
    loading: () => (
        <div className="p-10 text-slate-500 font-mono">
            Initialize Terminal...
        </div>
    )
});

export default function TerminalPage() {
    return <TerminalView />;
}