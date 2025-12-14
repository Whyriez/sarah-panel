'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Clock, Plus, Trash2, PlayCircle } from 'lucide-react';

export default function CronPage() {
    const [jobs, setJobs] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    // Form State
    const [name, setName] = useState('');
    const [command, setCommand] = useState('');
    const [schedule, setSchedule] = useState('* * * * *');

    const fetchJobs = async () => {
        try {
            const token = localStorage.getItem('token');
            const res = await api.get('/cron', { headers: { Authorization: `Bearer ${token}` } });
            setJobs(res.data);
        } catch (err) {}
    };

    useEffect(() => { fetchJobs(); }, []);

    const handleCreate = async () => {
        if (!name || !command) return alert("Isi semua data!");
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            await api.post('/cron', { name, command, schedule }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchJobs();
            setName(''); setCommand('');
            alert("Cron Job Berhasil Dibuat!");
        } catch (err: any) {
            alert("Gagal: " + err.response?.data?.detail);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if(!confirm("Hapus jadwal ini?")) return;
        try {
            const token = localStorage.getItem('token');
            await api.delete(`/cron/${id}`, { headers: { Authorization: `Bearer ${token}` } });
            fetchJobs();
        } catch (err) { alert("Gagal hapus"); }
    };

    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                <Clock className="text-purple-500"/> Task Scheduler (Cron)
            </h2>

            {/* Form Create */}
            <div className="bg-slate-900 p-6 rounded-xl border border-slate-800 mb-8 grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                <div>
                    <label className="text-slate-400 text-sm block mb-1">Job Name</label>
                    <input
                        className="w-full bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none"
                        placeholder="Daily Backup"
                        value={name} onChange={(e) => setName(e.target.value)}
                    />
                </div>
                <div className="md:col-span-2">
                    <label className="text-slate-400 text-sm block mb-1">Command (Shell)</label>
                    <input
                        className="w-full bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none font-mono text-sm"
                        placeholder="echo 'Hello' >> log.txt"
                        value={command} onChange={(e) => setCommand(e.target.value)}
                    />
                </div>
                <div>
                    <label className="text-slate-400 text-sm block mb-1">Schedule (Cron)</label>
                    <input
                        className="w-full bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none font-mono text-center"
                        placeholder="* * * * *"
                        value={schedule} onChange={(e) => setSchedule(e.target.value)}
                    />
                    <p className="text-[10px] text-slate-500 mt-1 text-center">min hour day month week</p>
                </div>
                <button
                    onClick={handleCreate}
                    disabled={loading}
                    className="md:col-span-4 bg-purple-600 hover:bg-purple-700 text-white py-2 rounded font-medium mt-2 flex justify-center items-center gap-2"
                >
                    <Plus size={18}/> Add Scheduled Task
                </button>
            </div>

            {/* List Jobs */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <table className="w-full text-left">
                    <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
                    <tr>
                        <th className="px-6 py-4">Job Name</th>
                        <th className="px-6 py-4">Command</th>
                        <th className="px-6 py-4">Schedule</th>
                        <th className="px-6 py-4 text-right">Action</th>
                    </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                    {jobs.map((job) => (
                        <tr key={job.id} className="hover:bg-slate-800/50">
                            <td className="px-6 py-4 text-white font-medium">{job.name}</td>
                            <td className="px-6 py-4 text-slate-300 font-mono text-xs bg-slate-950/50 p-2 rounded">
                                {job.command}
                            </td>
                            <td className="px-6 py-4">
                            <span className="bg-purple-900/30 text-purple-400 px-2 py-1 rounded text-xs font-mono border border-purple-900/50">
                                {job.schedule}
                            </span>
                            </td>
                            <td className="px-6 py-4 text-right">
                                <button onClick={() => handleDelete(job.id)} className="text-red-400 hover:text-red-300">
                                    <Trash2 size={18} />
                                </button>
                            </td>
                        </tr>
                    ))}
                    {jobs.length === 0 && (
                        <tr><td colSpan={4} className="p-8 text-center text-slate-500">No active jobs.</td></tr>
                    )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}