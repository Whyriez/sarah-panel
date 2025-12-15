'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/api';
import { Cpu, HardDrive, MemoryStick } from 'lucide-react';

// Tipe data sesuai response Python Backend
interface SystemStats {
    cpu: { usage_percent: number; cores: number };
    memory: { total_gb: number; used_gb: number; percent: number };
    disk: { total_gb: number; used_gb: number; percent: number };
    system: { os: string; boot_time: string };
}

export default function DashboardPage() {
    const [stats, setStats] = useState<SystemStats | null>(null);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await api.get('/monitor');
                setStats(res.data.data);
            } catch (error) {
                console.error("Gagal fetch monitor:", error);
            }
        };

        // Panggil pertama kali
        fetchStats();

        // Polling setiap 2 detik
        const interval = setInterval(fetchStats, 2000);

        // Cleanup saat pindah halaman (biar gak memory leak)
        return () => clearInterval(interval);
    }, []);

    if (!stats) return <div className="text-white">Loading System Stats...</div>;

    return (
        <div>
            <div className="mb-8">
                <h2 className="text-2xl font-bold text-white">Server Overview</h2>
                <p className="text-slate-400">
                    OS: {stats.system.os} | Up since: {stats.system.boot_time}
                </p>
            </div>

            {/* Grid Kartu Statistik */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                {/* CPU CARD */}
                <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-slate-400 font-medium">CPU Usage</h3>
                        <Cpu className="text-blue-500" />
                    </div>
                    <div className="text-3xl font-bold text-white mb-2">
                        {stats.cpu.usage_percent}%
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2.5">
                        <div
                            className="bg-blue-600 h-2.5 rounded-full transition-all duration-500"
                            style={{ width: `${stats.cpu.usage_percent}%` }}
                        ></div>
                    </div>
                    <p className="text-xs text-slate-500 mt-2">{stats.cpu.cores} Cores detected</p>
                </div>

                {/* RAM CARD */}
                <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-slate-400 font-medium">Memory (RAM)</h3>
                        <MemoryStick className="text-purple-500" />
                    </div>
                    <div className="text-3xl font-bold text-white mb-2">
                        {stats.memory.percent}%
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2.5">
                        <div
                            className="bg-purple-600 h-2.5 rounded-full transition-all duration-500"
                            style={{ width: `${stats.memory.percent}%` }}
                        ></div>
                    </div>
                    <p className="text-xs text-slate-500 mt-2">
                        {stats.memory.used_gb} GB / {stats.memory.total_gb} GB
                    </p>
                </div>

                {/* DISK CARD */}
                <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-slate-400 font-medium">Disk Space</h3>
                        <HardDrive className="text-green-500" />
                    </div>
                    <div className="text-3xl font-bold text-white mb-2">
                        {stats.disk.percent}%
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2.5">
                        <div
                            className="bg-green-600 h-2.5 rounded-full transition-all duration-500"
                            style={{ width: `${stats.disk.percent}%` }}
                        ></div>
                    </div>
                    <p className="text-xs text-slate-500 mt-2">
                        {stats.disk.used_gb} GB / {stats.disk.total_gb} GB
                    </p>
                </div>

            </div>
        </div>
    );
}