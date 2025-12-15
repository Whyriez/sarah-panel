'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import api from '@/lib/api';
import {ShieldCheck, Key, Plus, Trash, Save, Loader2, Settings, RefreshCw} from 'lucide-react';

export default function SettingsPage() {
    const { id } = useParams();
    const [activeTab, setActiveTab] = useState('env'); // 'env' or 'ssl'
    const [loading, setLoading] = useState(false);

    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-6">Site Settings</h2>

            {/* TABS HEADER */}
            <div className="flex gap-4 border-b border-slate-800 mb-6">
                <button
                    onClick={() => setActiveTab('general')}
                    className={`pb-2 px-4 text-sm font-medium transition-colors ${activeTab === 'general' ? 'text-white border-b-2 border-white' : 'text-slate-400 hover:text-white'}`}
                >
                    General
                </button>
                <button
                    onClick={() => setActiveTab('env')}
                    className={`pb-2 px-4 text-sm font-medium transition-colors ${activeTab === 'env' ? 'text-blue-500 border-b-2 border-blue-500' : 'text-slate-400 hover:text-white'}`}
                >
                    Environment Variables
                </button>
                <button
                    onClick={() => setActiveTab('ssl')}
                    className={`pb-2 px-4 text-sm font-medium transition-colors ${activeTab === 'ssl' ? 'text-green-500 border-b-2 border-green-500' : 'text-slate-400 hover:text-white'}`}
                >
                    SSL / HTTPS
                </button>
            </div>

            {/* CONTENT */}
            {activeTab === 'general' && <GeneralSettings siteId={id} />}
            {activeTab === 'env' && <EnvManager siteId={id} />}
            {activeTab === 'ssl' && <SSLManager siteId={id} />}
        </div>
    );
}

// --- SUB COMPONENT: ENV MANAGER ---
function EnvManager({ siteId }: { siteId: any }) {
    const [envs, setEnvs] = useState<{key: string, value: string}[]>([]);

    useEffect(() => {
        api.get(`/sites/${siteId}/env`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
            .then(res => setEnvs(res.data.env));
    }, [siteId]);

    const handleSave = async () => {
        try {
            await api.post(`/sites/${siteId}/env`, { env: envs }, {
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
            });
            alert("Saved & App Restarted!");
        } catch (err) { alert("Failed to save"); }
    };

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="mb-4 flex justify-between items-center">
                <h3 className="text-white font-bold flex items-center gap-2"><Key size={18}/> .env Editor</h3>
                <button onClick={handleSave} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-1.5 rounded text-sm flex items-center gap-2">
                    <Save size={16}/> Save Changes
                </button>
            </div>

            <div className="space-y-3">
                {envs.map((env, idx) => (
                    <div key={idx} className="flex gap-3">
                        <input
                            placeholder="KEY (e.g. DB_HOST)"
                            className="bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white w-1/3 outline-none focus:border-blue-500 font-mono text-sm"
                            value={env.key}
                            onChange={(e) => {
                                const newEnvs = [...envs];
                                newEnvs[idx].key = e.target.value.toUpperCase();
                                setEnvs(newEnvs);
                            }}
                        />
                        <input
                            placeholder="VALUE"
                            className="bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white flex-1 outline-none focus:border-blue-500 font-mono text-sm"
                            value={env.value}
                            onChange={(e) => {
                                const newEnvs = [...envs];
                                newEnvs[idx].value = e.target.value;
                                setEnvs(newEnvs);
                            }}
                        />
                        <button
                            onClick={() => setEnvs(envs.filter((_, i) => i !== idx))}
                            className="p-2 text-red-500 hover:bg-red-900/20 rounded"
                        >
                            <Trash size={16}/>
                        </button>
                    </div>
                ))}
            </div>

            <button
                onClick={() => setEnvs([...envs, {key: "", value: ""}])}
                className="mt-4 text-blue-400 text-sm hover:text-blue-300 flex items-center gap-1"
            >
                <Plus size={16}/> Add New Variable
            </button>
        </div>
    );
}

// --- SUB COMPONENT: SSL MANAGER ---
function SSLManager({ siteId }: { siteId: any }) {
    const [loading, setLoading] = useState(false);

    const handleIssue = async () => {
        setLoading(true);
        try {
            const res = await api.post(`/sites/${siteId}/ssl`, {}, {
                headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
            });
            alert(res.data.message);
        } catch (err: any) {
            alert("Error: " + err.response?.data?.detail);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-start gap-4">
                <div className="p-3 bg-green-900/30 rounded-lg">
                    <ShieldCheck size={32} className="text-green-500"/>
                </div>
                <div>
                    <h3 className="text-white font-bold text-lg">SSL Certificate (HTTPS)</h3>
                    <p className="text-slate-400 text-sm mt-1 mb-4">
                        Secure your website with Let's Encrypt Free SSL.
                        This will automatically configure Nginx to force HTTPS.
                    </p>

                    <button
                        onClick={handleIssue}
                        disabled={loading}
                        className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded font-medium flex items-center gap-2 disabled:opacity-50"
                    >
                        {loading ? <Loader2 className="animate-spin" size={18}/> : <ShieldCheck size={18}/>}
                        {loading ? 'Issuing Certificate...' : 'Issue Free SSL'}
                    </button>

                    <p className="text-xs text-slate-500 mt-4">
                        Note: Domain harus sudah mengarah ke server ini (DNS A Record) agar proses validasi berhasil.
                    </p>
                </div>
            </div>
        </div>
    );
}

function GeneralSettings({ siteId }: { siteId: any }) {
    const [site, setSite] = useState<any>(null);
    const [newPort, setNewPort] = useState('');
    const [loading, setLoading] = useState(false);

    // Load data site saat ini
    useEffect(() => {
        const token = localStorage.getItem('token');
        // Kita butuh endpoint detail site (GET /sites/{id})
        // Tapi endpoint list /sites kita ngembaliin array.
        // Hack dikit: ambil semua, cari yg id cocok (biar gk bikin endpoint baru dlu)
        api.get('/sites', { headers: { Authorization: `Bearer ${token}` } })
            .then(res => {
                const found = res.data.find((s: any) => s.id == siteId);
                if(found) {
                    setSite(found);
                    setNewPort(found.app_port);
                }
            });
    }, [siteId]);

    const handleSavePort = async () => {
        if(!confirm("Ubah port akan me-restart aplikasi. Lanjut?")) return;
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            await api.put(`/sites/${siteId}/port`, { new_port: parseInt(newPort) }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            alert("Port berhasil diubah! Aplikasi sedang restart...");
            // Refresh halaman atau state
            window.location.reload();
        } catch (err: any) {
            alert("Gagal: " + err.response?.data?.detail);
        } finally {
            setLoading(false);
        }
    };

    if (!site) return <div className="text-slate-500">Loading details...</div>;

    return (
        <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-white font-bold flex items-center gap-2 mb-4">
                    <Settings size={18}/> App Configuration
                </h3>

                <div className="grid grid-cols-2 gap-6">
                    <div>
                        <label className="text-slate-400 text-sm block mb-1">Domain Name</label>
                        <input disabled value={site.domain} className="w-full bg-slate-950 text-slate-500 p-2 rounded border border-slate-800 cursor-not-allowed"/>
                        <p className="text-xs text-slate-600 mt-1">Domain tidak bisa diubah (Hapus & Buat baru jika ingin ganti).</p>
                    </div>

                    <div>
                        <label className="text-slate-400 text-sm block mb-1">Application Port</label>
                        <div className="flex gap-2">
                            <input
                                type="number"
                                value={newPort}
                                onChange={(e) => setNewPort(e.target.value)}
                                className="flex-1 bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none focus:border-blue-500"
                            />
                            <button
                                onClick={handleSavePort}
                                disabled={loading || newPort == site.app_port}
                                className="bg-blue-600 hover:bg-blue-700 text-white px-4 rounded transition-colors disabled:opacity-50"
                            >
                                {loading ? <RefreshCw className="animate-spin" size={18}/> : 'Save'}
                            </button>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                            Port aplikasi Node.js/Python di localhost. Nginx akan meneruskan traffic ke sini.
                        </p>
                    </div>
                </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="text-white font-bold flex items-center gap-2 mb-2 text-red-500">
                    Danger Zone
                </h3>
                <p className="text-slate-400 text-sm mb-4">Hapus website ini dan seluruh datanya secara permanen.</p>
                <button className="border border-red-900 text-red-500 hover:bg-red-900/20 px-4 py-2 rounded text-sm font-medium">
                    Delete Website
                </button>
            </div>
        </div>
    );
}