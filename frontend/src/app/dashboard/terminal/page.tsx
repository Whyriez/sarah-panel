'use client';

import { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css'; // Wajib import CSS-nya

export default function TerminalPage() {
    const terminalRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // 1. Inisialisasi Terminal dengan Setting Khusus Windows
        const term = new Terminal({
            cursorBlink: true,
            convertEol: true, // <--- PERBAIKAN 1: Wajib True buat Windows biar ga "tangga"
            rows: 30, // Default rows biar ga gepeng awal2
            theme: {
                background: '#0f172a',
                foreground: '#e2e8f0',
                cursor: '#3b82f6',
            },
            // <--- PERBAIKAN 2: Pakai font monospace standar web biar lebar huruf konsisten
            fontFamily: 'Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
            fontSize: 14,
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);

        if (terminalRef.current) {
            term.open(terminalRef.current);

            // <--- PERBAIKAN 3: Kasih jeda dikit biar CSS render dulu baru di-fit
            setTimeout(() => {
                fitAddon.fit();
            }, 100);
        }

        // 2. Konek ke WebSocket
        const token = localStorage.getItem('token');
        const wsUrl = `ws://127.0.0.1:8000/ws/terminal?token=${token}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        const sendResize = () => {
            if (ws.readyState === WebSocket.OPEN) {
                const dims = fitAddon.proposeDimensions();
                if (dims) {
                    fitAddon.fit();
                    ws.send(JSON.stringify({
                        type: 'resize',
                        cols: dims.cols,
                        rows: dims.rows
                    }));
                }
            }
        };

        ws.onopen = () => {
            term.clear();
            // [FIX] HAPUS setTimeout! Kirim langsung saat detik pertama konek.
            // Backend sekarang menunggu pesan ini sebelum memulai CMD.
            sendResize();
        };

        ws.onmessage = (event) => {
            term.write(event.data);
        };

        // Saat ngetik, bungkus jadi JSON
        term.onData((data) => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'input',
                    data: data
                }));
            }
        });

        // Handle Window Resize
        const handleResize = () => {
            sendResize(); // <--- Panggil fungsi resize kita
        };
        window.addEventListener('resize', handleResize);

        return () => {
            ws.close();
            term.dispose();
            window.removeEventListener('resize', handleResize);
        };
    }, []);

    return (
        <div className="h-[calc(100vh-100px)] flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
            <div className="bg-slate-800 px-4 py-2 flex items-center justify-between border-b border-slate-700">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="ml-2 text-xs text-slate-400 font-mono">root@alim-server:~</span>
                </div>
                <div className="text-xs text-slate-500">WebSocket Secure Shell</div>
            </div>

            {/* Container Xterm */}
            <div
                ref={terminalRef}
                className="flex-1 p-2 bg-slate-950 overflow-hidden"
                style={{ height: '100%' }}
            />
        </div>
    );
}