'use client';

import { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

// [BARU] Terima props siteId (opsional)
export default function TerminalView({ siteId }: { siteId?: string }) {
    const terminalRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // 1. Inisialisasi Terminal
        const term = new Terminal({
            cursorBlink: true,
            convertEol: true,
            rows: 30,
            theme: {
                background: '#0f172a',
                foreground: '#e2e8f0',
                cursor: '#3b82f6',
            },
            fontFamily: 'Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
            fontSize: 14,
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);

        if (terminalRef.current) {
            term.open(terminalRef.current);
            setTimeout(() => {
                fitAddon.fit();
            }, 100);
        }

        // 2. Konek ke WebSocket
        const token = localStorage.getItem('token');
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const wsBaseUrl = baseUrl.replace(/^http/, 'ws');

        // [BARU] Tambahkan site_id ke Query Param jika ada
        let wsUrl = `${wsBaseUrl}/ws/terminal?token=${token}`;
        if (siteId) {
            wsUrl += `&site_id=${siteId}`;
        }

        console.log("Connecting Terminal to:", wsUrl);

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
            sendResize();
        };

        ws.onmessage = (event) => {
            term.write(event.data);
        };

        term.onData((data) => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'input',
                    data: data
                }));
            }
        });

        const handleResize = () => {
            sendResize();
        };
        window.addEventListener('resize', handleResize);

        return () => {
            ws.close();
            term.dispose();
            window.removeEventListener('resize', handleResize);
        };
    }, [siteId]); // [PENTING] Re-run jika siteId berubah

    return (
        <div className="h-[calc(100vh-100px)] flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
            <div className="bg-slate-800 px-4 py-2 flex items-center justify-between border-b border-slate-700">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="ml-2 text-xs text-slate-400 font-mono">
                        {siteId ? `site-${siteId}@server:~/www` : 'root@server:~'}
                    </span>
                </div>
                <div className="text-xs text-slate-500">WebSocket SSH</div>
            </div>

            <div
                ref={terminalRef}
                className="flex-1 p-2 bg-slate-950 overflow-hidden"
                style={{ height: '100%' }}
            />
        </div>
    );
}