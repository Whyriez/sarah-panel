'use client';

import { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';
import { Play, Square } from 'lucide-react';
import api from '@/lib/api';

export default function LogViewer() {
    const terminalRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const [sites, setSites] = useState<any[]>([]);
    const [selectedSite, setSelectedSite] = useState('');
    const [logType, setLogType] = useState('app');
    const [isPlaying, setIsPlaying] = useState(false);
    const termRef = useRef<Terminal | null>(null);

    // 1. Load Daftar Website
    useEffect(() => {
        const fetchSites = async () => {
            try {
                const token = localStorage.getItem('token');
                const res = await api.get('/sites', { headers: { Authorization: `Bearer ${token}` } });
                setSites(res.data);
                if (res.data.length > 0) setSelectedSite(res.data[0].domain);
            } catch (err) {}
        };
        fetchSites();
    }, []);

    // 2. Setup Terminal
    useEffect(() => {
        const term = new Terminal({
            cursorBlink: false,
            disableStdin: true,
            convertEol: true,
            theme: { background: '#0f172a', foreground: '#a3e635' },
            fontFamily: 'Menlo, monospace',
            fontSize: 12,
        });
        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);

        if (terminalRef.current) {
            term.open(terminalRef.current);
            fitAddon.fit();
        }
        termRef.current = term;

        // Cleanup saat pindah halaman
        return () => {
            wsRef.current?.close(); // Tutup koneksi kalau user pindah menu
            term.dispose();
        };
    }, []);

    // 3. Fungsi Start/Stop Streaming
    const toggleStream = () => {
        if (isPlaying) {
            wsRef.current?.close();
            setIsPlaying(false);
            termRef.current?.write('\r\n\x1b[31m[STREAM STOPPED]\x1b[0m\r\n');
        } else {
            if (!selectedSite) return alert("Pilih website dulu!");

            termRef.current?.clear();
            termRef.current?.write(`\x1b[34m[CONNECTING] Connecting to ${logType} logs for ${selectedSite}...\x1b[0m\r\n`);

            // [FIX PENTING] URL WebSocket Dinamis (Biar jalan di VPS)
            // Mengambil base URL dari .env atau window location
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            // Ganti http:// jadi ws:// dan https:// jadi wss://
            const wsBaseUrl = baseUrl.replace(/^http/, 'ws');

            const wsUrl = `${wsBaseUrl}/ws/logs/${logType}/${selectedSite}`;

            console.log("Connecting to WS:", wsUrl); // Debugging

            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onmessage = (event) => {
                termRef.current?.write(event.data);
            };

            ws.onopen = () => setIsPlaying(true);
            ws.onclose = () => {
                setIsPlaying(false);
                termRef.current?.write('\r\n\x1b[31m[CONNECTION CLOSED]\x1b[0m\r\n');
            };
            ws.onerror = (err) => {
                console.error("WS Error:", err);
                termRef.current?.write('\r\n\x1b[31m[CONNECTION ERROR] Cek Console Browser\x1b[0m\r\n');
            };
        }
    };

    return (
        <div className="h-[calc(100vh-100px)] flex flex-col space-y-4">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-white">Log Viewer</h2>
                    <p className="text-slate-400">Real-time application monitoring</p>
                </div>
            </div>

            <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 flex gap-4 items-center flex-wrap">
                <select
                    className="bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none"
                    value={selectedSite}
                    onChange={(e) => setSelectedSite(e.target.value)}
                >
                    {sites.map(s => <option key={s.id} value={s.domain}>{s.domain}</option>)}
                </select>

                <select
                    className="bg-slate-950 text-white p-2 rounded border border-slate-700 outline-none"
                    value={logType}
                    onChange={(e) => setLogType(e.target.value)}
                >
                    <option value="app">Application Logs (PM2)</option>
                    <option value="nginx">Web Server Logs (Nginx)</option>
                </select>

                <button
                    onClick={toggleStream}
                    className={`flex items-center gap-2 px-6 py-2 rounded font-bold transition-colors ${
                        isPlaying ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'
                    } text-white`}
                >
                    {isPlaying ? <><Square size={16}/> STOP</> : <><Play size={16}/> START</>}
                </button>
            </div>

            <div className="flex-1 bg-slate-950 rounded-xl overflow-hidden border border-slate-800 p-2 relative">
                <div ref={terminalRef} className="h-full w-full" />
            </div>
        </div>
    );
}