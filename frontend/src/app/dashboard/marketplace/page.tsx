'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Download, CheckCircle, Loader2, Server, Terminal, Box } from 'lucide-react';

// Daftar versi PHP yang didukung oleh Installer Backend
const AVAILABLE_PHP_VERSIONS = ["7.4", "8.0", "8.1", "8.2", "8.3", "8.4"];

export default function MarketplacePage() {
    // State untuk Web Apps (WordPress, dll)
    const [sites, setSites] = useState<any[]>([]);
    const [selectedSite, setSelectedSite] = useState('');
    const [appLoading, setAppLoading] = useState(false);

    // State untuk Server Software (PHP)
    const [installedPhp, setInstalledPhp] = useState<string[]>([]);
    const [installingPhpVer, setInstallingPhpVer] = useState<string | null>(null);

    // 1. Fetch Data Awal
    useEffect(() => {
        const token = localStorage.getItem('token');
        const headers = { Authorization: `Bearer ${token}` };

        // Load List Sites
        api.get('/sites', { headers }).then(res => {
            setSites(res.data);
            if (res.data.length > 0) setSelectedSite(res.data[0].id);
        });

        // Load Installed PHP Versions
        fetchPhpVersions();
    }, []);

    const fetchPhpVersions = () => {
        api.get('/php-versions', { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
            .then(res => setInstalledPhp(res.data.versions));
    };

    // 2. Handler Install Web Apps (WordPress)
    const handleInstallApp = async (app: string) => {
        if (!selectedSite) return alert("Pilih domain dulu!");
        if (!confirm(`Install ${app} di website terpilih? File lama mungkin tertimpa!`)) return;

        setAppLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await api.post(`/marketplace/install/${app}`,
                null,
                {
                    params: { site_id: selectedSite },
                    headers: { Authorization: `Bearer ${token}` }
                }
            );
            alert(`Sukses! ${res.data.message}\nDatabase: ${res.data.db_name}`);
        } catch (err: any) {
            alert("Gagal: " + err.response?.data?.detail);
        } finally {
            setAppLoading(false);
        }
    };

    // 3. Handler Install PHP System (Global)
    const handleInstallPhp = async (version: string) => {
        if(!confirm(`Install PHP ${version} ke server? Proses ini berjalan di background.`)) return;

        setInstallingPhpVer(version);
        try {
            // Panggil API endpoint backend yang baru kita buat
            const res = await api.post('/marketplace/php/install', {
                version: version
            });
            alert(res.data.message);

            // Refresh list (walaupun install belum kelar, user tau progress)
            // Idealnya pakai websocket/interval, tapi manual refresh ok untuk MVP
            setTimeout(fetchPhpVersions, 5000);
        } catch (err: any) {
            alert("Gagal Install PHP: " + (err.response?.data?.detail || err.message));
        } finally {
            setInstallingPhpVer(null);
        }
    };

    return (
        <div className="space-y-10">

            {/* --- SECTION 1: SERVER SOFTWARE (PHP VERSIONS) --- */}
            <div>
                <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                    <Server className="text-blue-500" /> Server Software
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    {AVAILABLE_PHP_VERSIONS.map((ver) => {
                        const isInstalled = installedPhp.includes(ver);
                        const isInstalling = installingPhpVer === ver;

                        return (
                            <div key={ver} className={`p-4 rounded-xl border ${isInstalled ? 'bg-slate-900/50 border-green-900' : 'bg-slate-900 border-slate-800'} flex flex-col items-center justify-center gap-3 transition-all`}>
                                <div className="text-lg font-bold text-white font-mono">PHP {ver}</div>

                                {isInstalled ? (
                                    <div className="flex items-center gap-1 text-green-500 text-xs font-medium px-2 py-1 bg-green-900/20 rounded-full">
                                        <CheckCircle size={12} /> Installed
                                    </div>
                                ) : (
                                    <button
                                        onClick={() => handleInstallPhp(ver)}
                                        disabled={isInstalling}
                                        className="text-xs bg-slate-800 hover:bg-blue-600 text-white px-3 py-1.5 rounded transition-colors flex items-center gap-2 disabled:opacity-50"
                                    >
                                        {isInstalling ? <Loader2 className="animate-spin" size={12}/> : <Download size={12}/>}
                                        {isInstalling ? '...' : 'Install'}
                                    </button>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            <hr className="border-slate-800" />

            {/* --- SECTION 2: WEB APPLICATIONS (WORDPRESS, ETC) --- */}
            <div>
                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                    <Box className="text-yellow-500" /> One-Click Apps
                </h2>

                {/* Selector Domain Target */}
                <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 mb-8 flex items-center gap-4 max-w-2xl">
                    <span className="text-slate-400 text-sm font-medium">Install to Website:</span>
                    <select
                        className="bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none flex-1 text-sm"
                        value={selectedSite}
                        onChange={(e) => setSelectedSite(e.target.value)}
                    >
                        {sites.map(s => <option key={s.id} value={s.id}>{s.domain}</option>)}
                    </select>
                </div>

                {/* Grid Aplikasi */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                    {/* WORDPRESS CARD */}
                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl hover:border-blue-500 transition-colors group relative overflow-hidden">
                        <div className="absolute top-0 right-0 bg-blue-600/10 p-10 rounded-bl-full -mr-10 -mt-10 group-hover:bg-blue-600/20 transition-all"></div>

                        <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center mb-4 text-white font-bold text-xl relative z-10">
                            W
                        </div>
                        <h3 className="text-xl font-bold text-white relative z-10">WordPress</h3>
                        <p className="text-slate-400 text-sm mt-2 mb-6 relative z-10">
                            CMS terpopuler di dunia. Blog, Toko Online, Company Profile, semua bisa.
                        </p>
                        <button
                            onClick={() => handleInstallApp('wordpress')}
                            disabled={appLoading}
                            className="w-full py-2 bg-slate-800 hover:bg-blue-600 text-white rounded-lg font-medium transition-all flex items-center justify-center gap-2 relative z-10"
                        >
                            {appLoading ? <Loader2 className="animate-spin" size={18}/> : <Download size={18}/>}
                            One-Click Install
                        </button>
                    </div>

                    {/* LARAVEL CARD */}
                    <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl opacity-60">
                        <div className="w-12 h-12 bg-red-600 rounded-lg flex items-center justify-center mb-4 text-white font-bold text-xl">
                            L
                        </div>
                        <h3 className="text-xl font-bold text-white">Laravel Kit</h3>
                        <p className="text-slate-400 text-sm mt-2 mb-6">
                            Auto-deploy Laravel Starter Kit + Composer + Permission fix.
                        </p>
                        <button disabled className="w-full py-2 bg-slate-800 text-slate-500 rounded-lg font-medium cursor-not-allowed">
                            Coming Soon
                        </button>
                    </div>

                </div>
            </div>
        </div>
    );
}