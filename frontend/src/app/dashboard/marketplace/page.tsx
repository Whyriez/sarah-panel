'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Download, CheckCircle, Loader2 } from 'lucide-react';

export default function MarketplacePage() {
    const [sites, setSites] = useState<any[]>([]);
    const [selectedSite, setSelectedSite] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // Load list site buat dropdown target instalasi
        api.get('/sites', { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
            .then(res => {
                setSites(res.data);
                if (res.data.length > 0) setSelectedSite(res.data[0].id);
            });
    }, []);

    const handleInstall = async (app: string) => {
        if (!selectedSite) return alert("Pilih domain dulu!");
        if (!confirm(`Install ${app} di website terpilih? File lama mungkin tertimpa!`)) return;

        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await api.post(`/marketplace/install/${app}`,
                null, // Body kosong karena parameter lewat query/path logic
                {
                    params: { site_id: selectedSite },
                    headers: { Authorization: `Bearer ${token}` }
                }
            );
            alert(`Sukses! ${res.data.message}\nDatabase: ${res.data.db_name}`);
        } catch (err: any) {
            alert("Gagal: " + err.response?.data?.detail);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-6">App Marketplace</h2>

            {/* Selector Domain Target */}
            <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 mb-8 flex items-center gap-4">
                <span className="text-slate-400">Install to:</span>
                <select
                    className="bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none flex-1"
                    value={selectedSite}
                    onChange={(e) => setSelectedSite(e.target.value)}
                >
                    {sites.map(s => <option key={s.id} value={s.id}>{s.domain}</option>)}
                </select>
            </div>

            {/* Grid Aplikasi */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                {/* WORDPRESS CARD */}
                <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl hover:border-blue-500 transition-colors group">
                    <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4 text-white font-bold text-xl">
                        W
                    </div>
                    <h3 className="text-xl font-bold text-white">WordPress</h3>
                    <p className="text-slate-400 text-sm mt-2 mb-6">
                        CMS terpopuler di dunia. Blog, Toko Online, Company Profile, semua bisa.
                    </p>
                    <button
                        onClick={() => handleInstall('wordpress')}
                        disabled={loading}
                        className="w-full py-2 bg-slate-800 hover:bg-blue-600 text-white rounded-lg font-medium transition-all flex items-center justify-center gap-2"
                    >
                        {loading ? <Loader2 className="animate-spin" size={18}/> : <Download size={18}/>}
                        One-Click Install
                    </button>
                </div>

                {/* COMING SOON CARD */}
                <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl opacity-50 cursor-not-allowed">
                    <div className="w-12 h-12 bg-red-600 rounded-lg flex items-center justify-center mb-4 text-white font-bold text-xl">
                        L
                    </div>
                    <h3 className="text-xl font-bold text-white">Laravel</h3>
                    <p className="text-slate-400 text-sm mt-2 mb-6">
                        Framework PHP modern untuk developer pro. (Coming Soon)
                    </p>
                    <button disabled className="w-full py-2 bg-slate-800 text-slate-500 rounded-lg font-medium">
                        Coming Soon
                    </button>
                </div>

            </div>
        </div>
    );
}