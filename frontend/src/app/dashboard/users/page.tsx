'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Users, UserPlus, Trash2, Shield, User } from 'lucide-react';

export default function UsersPage() {
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    // Form State
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState('user');

    const fetchUsers = async () => {
        try {
            const token = localStorage.getItem('token');
            const res = await api.get('/users', { headers: { Authorization: `Bearer ${token}` } });
            setUsers(res.data);
        } catch (err: any) {
            if(err.response?.status === 403) alert("Access Denied: Admin Only");
        }
    };

    useEffect(() => { fetchUsers(); }, []);

    const handleCreate = async () => {
        if (!username || !password) return alert("Username & Password wajib!");
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            await api.post('/users', { username, password, role }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchUsers();
            setUsername(''); setPassword('');
            alert("User Created!");
        } catch (err: any) {
            alert("Gagal: " + err.response?.data?.detail);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if(!confirm("Hapus user ini? Website mereka mungkin akan error (orphan).")) return;
        try {
            const token = localStorage.getItem('token');
            await api.delete(`/users/${id}`, { headers: { Authorization: `Bearer ${token}` } });
            fetchUsers();
        } catch (err: any) { alert("Gagal hapus: " + err.response?.data?.detail); }
    };

    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                <Users className="text-pink-500"/> User Management
            </h2>

            {/* Form Create */}
            <div className="bg-slate-900 p-6 rounded-xl border border-slate-800 mb-8 grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                <div>
                    <label className="text-slate-400 text-sm block mb-1">Username</label>
                    <input
                        className="w-full bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none"
                        value={username} onChange={(e) => setUsername(e.target.value)}
                    />
                </div>
                <div>
                    <label className="text-slate-400 text-sm block mb-1">Password</label>
                    <input
                        type="password"
                        className="w-full bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none"
                        value={password} onChange={(e) => setPassword(e.target.value)}
                    />
                </div>
                <div>
                    <label className="text-slate-400 text-sm block mb-1">Role</label>
                    <select
                        className="w-full bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none"
                        value={role} onChange={(e) => setRole(e.target.value)}
                    >
                        <option value="user">Customer</option>
                        <option value="admin">Admin</option>
                    </select>
                </div>
                <button
                    onClick={handleCreate}
                    disabled={loading}
                    className="bg-pink-600 hover:bg-pink-700 text-white py-2 rounded font-medium flex justify-center items-center gap-2"
                >
                    <UserPlus size={18}/> Create User
                </button>
            </div>

            {/* List Users */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
                    <tr>
                        <th className="px-6 py-4">ID</th>
                        <th className="px-6 py-4">Username</th>
                        <th className="px-6 py-4">Role</th>
                        <th className="px-6 py-4 text-right">Action</th>
                    </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                    {users.map((u) => (
                        <tr key={u.id} className="hover:bg-slate-800/50">
                            <td className="px-6 py-4 text-slate-500 font-mono text-xs">#{u.id}</td>
                            <td className="px-6 py-4 text-white font-medium flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${u.is_active ? 'bg-green-500' : 'bg-red-500'}`}></div>
                                {u.username}
                            </td>
                            <td className="px-6 py-4">
                                {u.role === 'admin' ? (
                                    <span className="flex items-center gap-1 text-yellow-400 text-xs font-bold uppercase">
                                    <Shield size={12}/> Admin
                                </span>
                                ) : (
                                    <span className="flex items-center gap-1 text-slate-400 text-xs font-medium uppercase">
                                    <User size={12}/> Customer
                                </span>
                                )}
                            </td>
                            <td className="px-6 py-4 text-right">
                                <button onClick={() => handleDelete(u.id)} className="text-red-400 hover:text-red-300">
                                    <Trash2 size={18} />
                                </button>
                            </td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}