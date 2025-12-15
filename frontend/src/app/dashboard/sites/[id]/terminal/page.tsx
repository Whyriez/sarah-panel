'use client';

import { useParams } from 'next/navigation';
import TerminalView from '@/components/ui/TerminalView';

export default function SiteTerminalPage() {
    const { id } = useParams();

    // Pastikan id dalam bentuk string
    const siteId = Array.isArray(id) ? id[0] : id;

    return (
        <div>
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-white">Site Terminal</h2>
                <p className="text-slate-400 text-sm">Access terminal inside your website directory.</p>
            </div>

            {/* Panggil TerminalView dengan ID Website */}
            <TerminalView siteId={siteId} />
        </div>
    );
}