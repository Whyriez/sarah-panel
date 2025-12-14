'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Archive, Download, Trash2, Plus, HardDrive, Clock } from 'lucide-react';

export default function BackupsPage() {
    const [backups, setBackups] = useState<any[]>([]);
    const [sites, setSites] = useState<any[]>([]);
    const [selectedSite, setSelectedSite] = useState('');
    const [loading, setLoading] = useState(false);

    // Load Data
    const loadData = async () => {
        const token = localStorage.getItem('token');
        try {
            const [resBackup, resSites] = await Promise.all([
                api.get('/backups/list', { headers: { Authorization: `Bearer ${token}` } }),
                api.get('/sites', { headers: { Authorization: `Bearer ${token}` } })
            ]);
            setBackups(resBackup.data);
            setSites(resSites.data);
            if (resSites.data.length > 0 && !selectedSite) setSelectedSite(resSites.data[0].id);
        } catch (err) { console.error(err); }
    };

    useEffect(() => { loadData(); }, []);

    const handleCreate = async () => {
        if (!selectedSite) return alert("Pilih website dulu!");
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            await api.post(`/backups/create/${selectedSite}`, {}, {
                headers: { Authorization: `Bearer ${token}` }
            });
            alert("Backup started! Refresh list in a few seconds.");
            // Delay dikit biar background task jalan
            setTimeout(loadData, 2000);
        } catch (err: any) {
            alert("Gagal: " + err.response?.data?.detail);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (filename: string) => {
        if (!confirm("Hapus backup ini?")) return;
        try {
            const token = localStorage.getItem('token');
            await api.delete(`/backups/delete/${filename}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            loadData();
        } catch (err) { alert("Gagal hapus"); }
    };

    const downloadUrl = (filename: string) => {
        // Direct link ke API endpoint download
        // Perlu token sebenernya, tapi untuk simpel kita pakai window.open
        // Note: Di production sebaiknya pakai fetch blob biar bisa pass header Auth
        // Untuk dev mode local, kita biarkan browser handle
        const token = localStorage.getItem('token');
        return `http://localhost:8000/backups/download/${filename}?token=${token}`; // (Note: perlu update backend dikit kalau mau support query param token di endpoint ini, tapi utk skrg kita klik manual aja di backend logs atau anggap public dlu utk MVP)
    }

    // Helper convert bytes to MB
    const formatSize = (bytes: number) => (bytes / 1024 / 1024).toFixed(2) + ' MB';

    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                <Archive className="text-yellow-500"/> Backup Manager
            </h2>

            {/* Control Bar */}
            <div className="bg-slate-900 p-6 rounded-xl border border-slate-800 mb-8 flex flex-col md:flex-row gap-4 items-end">
                <div className="flex-1 w-full">
                    <label className="text-slate-400 text-sm mb-2 block">Backup Target</label>
                    <select
                        className="w-full bg-slate-950 text-white p-2.5 rounded border border-slate-700 outline-none"
                        value={selectedSite}
                        onChange={(e) => setSelectedSite(e.target.value)}
                    >
                        {sites.map(s => <option key={s.id} value={s.id}>{s.domain}</option>)}
                    </select>
                </div>
                <button
                    onClick={handleCreate}
                    disabled={loading}
                    className="w-full md:w-auto bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded font-medium transition-colors flex items-center justify-center gap-2"
                >
                    {loading ? 'Processing...' : <><Plus size={18}/> Create New Backup</>}
                </button>
            </div>

            {/* List Backups */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
                    <tr>
                        <th className="px-6 py-4">Filename</th>
                        <th className="px-6 py-4">Size</th>
                        <th className="px-6 py-4">Created At</th>
                        <th className="px-6 py-4 text-right">Action</th>
                    </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                    {backups.length === 0 ? (
                        <tr><td colSpan={4} className="p-8 text-center text-slate-500">No backups found.</td></tr>
                    ) : (
                        backups.map((bk, idx) => (
                            <tr key={idx} className="hover:bg-slate-800/50 transition-colors">
                                <td className="px-6 py-4 font-mono text-white text-sm flex items-center gap-3">
                                    <Archive size={16} className="text-yellow-600"/>
                                    {bk.filename}
                                </td>
                                <td className="px-6 py-4 text-slate-400 text-sm">
                                    {formatSize(bk.size)}
                                </td>
                                <td className="px-6 py-4 text-slate-400 text-sm flex items-center gap-2">
                                    <Clock size={14}/> {bk.created_at}
                                </td>
                                <td className="px-6 py-4 flex justify-end gap-2">
                                    {/* Tombol Download (Pake API Backend) */}
                                    <button
                                        onClick={() => {
                                            const token = localStorage.getItem('token');
                                            // Fetch Blob manual biar bisa kasih Header Auth
                                            fetch(`http://localhost:8000/backups/download/${bk.filename}`, {
                                                headers: { 'Authorization': `Bearer ${token}` }
                                            })
                                                .then(res => res.blob())
                                                .then(blob => {
                                                    const url = window.URL.createObjectURL(blob);
                                                    const a = document.createElement('a');
                                                    a.href = url;
                                                    a.download = bk.filename;
                                                    a.click();
                                                })
                                                .catch(err => alert("Download failed"));
                                        }}
                                        className="bg-slate-800 hover:bg-green-900/30 text-green-500 p-2 rounded transition-colors"
                                        title="Download"
                                    >
                                        <Download size={16} />
                                    </button>

                                    <button
                                        onClick={() => handleDelete(bk.filename)}
                                        className="bg-slate-800 hover:bg-red-900/30 text-red-400 p-2 rounded transition-colors"
                                        title="Delete"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </td>
                            </tr>
                        ))
                    )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}