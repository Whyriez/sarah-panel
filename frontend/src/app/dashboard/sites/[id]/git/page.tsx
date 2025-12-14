'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import api from '@/lib/api';
import { GitBranch, Link2, Save, Webhook } from 'lucide-react';

export default function GitPage() {
    const { id } = useParams();
    const [repoUrl, setRepoUrl] = useState('');
    const [branch, setBranch] = useState('main');
    const [webhookUrl, setWebhookUrl] = useState('');
    const [loading, setLoading] = useState(false);

    const handleConnect = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await api.post(`/git/setup/${id}`,
                { repo_url: repoUrl, branch: branch },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setWebhookUrl(res.data.webhook_url);
            alert("Repository Terhubung! Sekarang folder website berisi kode dari Git.");
        } catch (err: any) {
            alert("Gagal: " + err.response?.data?.detail);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-2xl">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                <GitBranch className="text-orange-500"/> Git Deployment
            </h2>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">

                {/* Input Repo */}
                <div>
                    <label className="text-slate-400 text-sm mb-2 block">Repository URL (HTTPS)</label>
                    <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded px-3 py-2">
                        <Link2 size={16} className="text-slate-500"/>
                        <input
                            type="text"
                            placeholder="https://github.com/username/repo.git"
                            className="bg-transparent flex-1 outline-none text-white"
                            value={repoUrl}
                            onChange={(e) => setRepoUrl(e.target.value)}
                        />
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Pastikan repository Public (atau gunakan Token Auth di URL)</p>
                </div>

                {/* Input Branch */}
                <div>
                    <label className="text-slate-400 text-sm mb-2 block">Branch</label>
                    <input
                        type="text"
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-white outline-none focus:border-blue-500"
                        value={branch}
                        onChange={(e) => setBranch(e.target.value)}
                    />
                </div>

                <button
                    onClick={handleConnect}
                    disabled={loading}
                    className="w-full bg-orange-600 hover:bg-orange-700 text-white py-2 rounded font-medium transition-colors flex justify-center items-center gap-2"
                >
                    {loading ? 'Cloning...' : <><Save size={18}/> Save & Clone</>}
                </button>

                {/* Webhook Info (Muncul setelah save) */}
                {webhookUrl && (
                    <div className="mt-8 pt-6 border-t border-slate-800 animate-in fade-in slide-in-from-top-4">
                        <h3 className="text-white font-bold flex items-center gap-2 mb-2">
                            <Webhook className="text-blue-400"/> Webhook Integration
                        </h3>
                        <p className="text-sm text-slate-400 mb-4">
                            Copy URL ini ke <b>GitHub Repo Settings {'>'} Webhooks</b>.
                            Set Content-Type ke <code>application/json</code>.
                        </p>
                        <div className="bg-slate-950 p-3 rounded border border-blue-900/50 text-blue-100 font-mono text-xs break-all select-all">
                            {webhookUrl}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}