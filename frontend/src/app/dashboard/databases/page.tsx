'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Database, Plus, Trash2, Copy, Check } from 'lucide-react';

interface DBItem {
    id: number;
    name: string;
    db_user: string;
    db_password: string;
}

export default function DatabasePage() {
    const [dbs, setDbs] = useState<DBItem[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchDbs = async () => {
        try {
            const token = localStorage.getItem('token');
            const res = await api.get('/databases', {
                headers: { Authorization: `Bearer ${token}` }
            });
            setDbs(res.data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDbs();
    }, []);

    const handleCreate = async () => {
        const name = prompt("Masukkan Nama Database (tanpa spasi/simbol):");
        if (!name) return;

        try {
            const token = localStorage.getItem('token');
            await api.post('/databases', { name }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchDbs();
            alert("Database berhasil dibuat!");
        } catch (err: any) {
            alert("Gagal: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleDelete = async (id: number) => {
        if(!confirm("Hapus Database ini? Data akan hilang permanen!")) return;
        try {
            const token = localStorage.getItem('token');
            await api.delete(`/databases/${id}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchDbs();
        } catch (err) {
            alert("Gagal hapus");
        }
    }

    // Component kecil buat copy text
    const CopyButton = ({ text }: { text: string }) => {
        const [copied, setCopied] = useState(false);
        return (
            <button
                onClick={() => {
                    navigator.clipboard.writeText(text);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                }}
                className="text-slate-500 hover:text-white transition-colors"
                title="Copy Password"
            >
                {copied ? <Check size={14} className="text-green-500"/> : <Copy size={14}/>}
            </button>
        );
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-white">Databases</h2>
                    <p className="text-slate-400">Manage MySQL/MariaDB databases</p>
                </div>
                <button
                    onClick={handleCreate}
                    className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                >
                    <Plus size={18} />
                    Create Database
                </button>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
                    <tr>
                        <th className="px-6 py-4">DB Name</th>
                        <th className="px-6 py-4">Username</th>
                        <th className="px-6 py-4">Password</th>
                        <th className="px-6 py-4">Host</th>
                        <th className="px-6 py-4">Action</th>
                    </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                    {loading ? (
                        <tr><td colSpan={5} className="px-6 py-8 text-center text-slate-500">Loading...</td></tr>
                    ) : dbs.length === 0 ? (
                        <tr><td colSpan={5} className="px-6 py-8 text-center text-slate-500">No databases found.</td></tr>
                    ) : (
                        dbs.map((db) => (
                            <tr key={db.id} className="hover:bg-slate-800/50 transition-colors">
                                <td className="px-6 py-4 font-medium text-white flex items-center gap-3">
                                    <Database size={16} className="text-yellow-500"/>
                                    {db.name}
                                </td>
                                <td className="px-6 py-4 text-slate-300 font-mono text-sm">
                                    {db.db_user}
                                </td>
                                <td className="px-6 py-4 text-slate-400 font-mono text-sm flex items-center gap-2">
                                <span className="bg-slate-950 px-2 py-1 rounded border border-slate-800">
                                    {db.db_password}
                                </span>
                                    <CopyButton text={db.db_password} />
                                </td>
                                <td className="px-6 py-4 text-slate-500 text-sm">
                                    localhost
                                </td>
                                <td className="px-6 py-4">
                                    <button
                                        onClick={() => handleDelete(db.id)}
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