'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import {Plus, Globe, Server, Trash2, FolderOpen, GitBranch, Settings} from 'lucide-react';
import Link from 'next/link';

interface Site {
    id: number;
    domain: string;
    type: string;
    app_port: number | null;
    is_active: boolean;
}

export default function SitesPage() {
    const [sites, setSites] = useState<Site[]>([]);
    const [loading, setLoading] = useState(true);

    // Fetch data saat halaman dibuka
    const fetchSites = async () => {
        try {
            // Kita perlu kirim Token di header (PENTING!)
            const token = localStorage.getItem('token');
            const res = await api.get('/sites', {
                headers: { Authorization: `Bearer ${token}` }
            });
            setSites(res.data);
        } catch (error) {
            console.error("Gagal load sites:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSites();
    }, []);

    // Fungsi Create Dummy (Nanti kita bikin Modal Form)
    const handleCreateDummy = async () => {
        const domain = prompt("Masukkan Domain (contoh: toko.alim.com):");
        const type = prompt("Tipe (php/node/static):");

        if (domain && type) {
            try {
                const token = localStorage.getItem('token');
                await api.post('/sites', { domain, type }, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                fetchSites(); // Reload list
                alert("Website berhasil ditambahkan ke Database!");
            } catch (err: any) {
                alert("Gagal: " + err.response?.data?.detail);
            }
        }
    };

    const handleDelete = async (id: number, domain: string) => {
        if(!confirm(`Yakin ingin menghapus website ${domain}?`)) return;

        try {
            const token = localStorage.getItem('token');
            await api.delete(`/sites/${id}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchSites(); // Reload <Trash2 size={16} />
            alert("Website berhasil dihapus!");
        } catch (err: any) {
            alert("Gagal hapus: " + err.message);
        }
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-white">Websites</h2>
                    <p className="text-slate-400">Manage your applications and domains</p>
                </div>
                <button
                    onClick={handleCreateDummy}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                >
                    <Plus size={18} />
                    Add New Site
                </button>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
                    <tr>
                        <th className="px-6 py-4">Domain</th>
                        <th className="px-6 py-4">Type</th>
                        <th className="px-6 py-4">Port</th>
                        <th className="px-6 py-4">Status</th>
                        <th className="px-6 py-4">Action</th>
                    </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                    {loading ? (
                        <tr><td colSpan={5} className="px-6 py-8 text-center text-slate-500">Loading...</td></tr>
                    ) : sites.length === 0 ? (
                        <tr><td colSpan={5} className="px-6 py-8 text-center text-slate-500">Belum ada website. Klik Add New Site.</td></tr>
                    ) : (
                        sites.map((site) => (
                            <tr key={site.id} className="hover:bg-slate-800/50 transition-colors">
                                <td className="px-6 py-4 font-medium text-white flex items-center gap-3">
                                    <div className="p-2 bg-slate-800 rounded text-blue-400"><Globe size={16}/></div>
                                    {site.domain}
                                </td>
                                <td className="px-6 py-4">
                                <span className="px-2 py-1 rounded text-xs font-semibold bg-slate-800 text-slate-300 uppercase border border-slate-700">
                                    {site.type}
                                </span>
                                </td>
                                <td className="px-6 py-4 text-slate-400 font-mono text-sm">
                                    {site.app_port ? site.app_port : '-'}
                                </td>
                                <td className="px-6 py-4">
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-900/30 text-green-400 border border-green-900/50">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-400"></span>
                                    Active
                                </span>
                                </td>
                                <td className="px-6 py-4 flex items-center gap-2">
                                    <Link
                                        href={`/dashboard/sites/${site.id}/files`}
                                        className="text-blue-400 hover:text-blue-300 transition-colors p-2 hover:bg-blue-900/20 rounded"
                                        title="File Manager"
                                    >
                                        <FolderOpen size={16} />
                                    </Link>

                                    <Link href={`/dashboard/sites/${site.id}/git`}
                                        className="text-blue-400 hover:text-blue-300 transition-colors p-2 hover:bg-blue-900/20 rounded"
                                        title="File Manager"
                                    >
                                        <GitBranch size={16} />
                                    </Link>

                                    <Link href={`/dashboard/sites/${site.id}/settings`} className="text-blue-400 hover:text-blue-300 transition-colors p-2 hover:bg-blue-900/20 rounded"
                                          title="Settings">
                                        <Settings size={16} />
                                    </Link>

                                    <button
                                        onClick={() => handleDelete(site.id, site.domain)} // <--- Update baris ini
                                        className="text-red-400 hover:text-red-300 transition-colors p-2 hover:bg-red-900/20 rounded"
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