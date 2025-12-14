'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import api from '@/lib/api';
import { Folder, FileText, ArrowLeft, Save, Upload, Trash2, Home } from 'lucide-react';

export default function FileManagerPage() {
    const { id } = useParams();
    const [path, setPath] = useState(''); // Current path (relative)
    const [items, setItems] = useState<any[]>([]);

    // Editor State
    const [editingFile, setEditingFile] = useState<string | null>(null);
    const [fileContent, setFileContent] = useState('');
    const [loading, setLoading] = useState(false);

    const fetchFiles = async () => {
        try {
            const token = localStorage.getItem('token');
            const res = await api.get(`/files/list/${id}`, {
                params: { path },
                headers: { Authorization: `Bearer ${token}` }
            });
            setItems(res.data);
        } catch (err) { console.error(err); }
    };

    useEffect(() => {
        if (!editingFile) fetchFiles();
    }, [id, path, editingFile]);

    // Navigate Folder
    const handleOpen = (item: any) => {
        if (item.type === 'folder') {
            setPath(path ? `${path}/${item.name}` : item.name);
        } else {
            openEditor(item.name);
        }
    };

    const goUp = () => {
        if (!path) return;
        const parts = path.split('/');
        parts.pop();
        setPath(parts.join('/'));
    };

    // Editor Logic
    const openEditor = async (filename: string) => {
        const filePath = path ? `${path}/${filename}` : filename;
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await api.get(`/files/content/${id}`, {
                params: { path: filePath },
                headers: { Authorization: `Bearer ${token}` }
            });
            setFileContent(res.data.content);
            setEditingFile(filePath);
        } catch (err) { alert("Cannot read file"); }
        setLoading(false);
    };

    const saveFile = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            await api.post(`/files/save/${id}`,
                { path: editingFile, content: fileContent },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            alert("File Saved!");
            setEditingFile(null); // Close editor
        } catch (err) { alert("Failed to save"); }
        setLoading(false);
    };

    // Upload Logic
    const handleUpload = async (e: any) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        // Ingat: path kita kirim lewat URL, file lewat Body
        formData.append('file', file);

        setLoading(true);
        try {
            const token = localStorage.getItem('token');

            // [SOLUSI] Pakai fetch bawaan browser (Bukan api.post)
            // Ganti URL 'http://localhost:8000' sesuai port backend Abang
            const backendUrl = 'http://localhost:8000';

            // Encode path biar aman kalau ada spasi (misal: "assets/img baru")
            const safePath = encodeURIComponent(path || "");

            const response = await fetch(`${backendUrl}/files/upload/${id}?path=${safePath}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    // JANGAN SET CONTENT-TYPE SAMA SEKALI DI SINI!
                    // Browser akan otomatis set: multipart/form-data; boundary=----WebKit...
                },
                body: formData
            });

            if (!response.ok) {
                // Kalau gagal, baca pesan error dari backend
                const errorData = await response.json();
                throw new Error(JSON.stringify(errorData.detail));
            }

            alert("Upload Success!");
            fetchFiles(); // Refresh list
        } catch (err: any) {
            console.error(err);
            alert("Upload failed:\n" + err.message);
        } finally {
            setLoading(false);
            e.target.value = null; // Reset input
        }
    };

    const handleDelete = async (itemName: string) => {
        if(!confirm(`Delete ${itemName}?`)) return;
        const itemPath = path ? `${path}/${itemName}` : itemName;
        try {
            const token = localStorage.getItem('token');
            await api.delete(`/files/delete/${id}`, {
                params: { path: itemPath },
                headers: { Authorization: `Bearer ${token}` }
            });
            fetchFiles();
        } catch (err) { alert("Delete failed"); }
    };

    // --- RENDER EDITOR VIEW ---
    if (editingFile) {
        return (
            <div className="h-[calc(100vh-100px)] flex flex-col">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-white font-mono text-sm break-all">Editing: {editingFile}</h3>
                    <div className="flex gap-2">
                        <button onClick={() => setEditingFile(null)} className="px-3 py-1 bg-slate-800 text-white rounded">Cancel</button>
                        <button onClick={saveFile} className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white rounded flex items-center gap-2">
                            <Save size={16}/> Save
                        </button>
                    </div>
                </div>
                <textarea
                    className="flex-1 bg-slate-950 text-green-400 font-mono text-sm p-4 rounded border border-slate-800 outline-none resize-none"
                    value={fileContent}
                    onChange={(e) => setFileContent(e.target.value)}
                />
            </div>
        );
    }

    // --- RENDER FILE LIST VIEW ---
    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-6">File Manager</h2>

            {/* Toolbar */}
            <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 mb-6 flex justify-between items-center">
                <div className="flex items-center gap-2 text-slate-400 font-mono text-sm">
                    <button onClick={() => setPath('')} className="hover:text-white"><Home size={16}/></button>
                    <span>/</span>
                    <span>{path}</span>
                </div>
                <div className="flex gap-2">
                    <label className="cursor-pointer bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm flex items-center gap-2">
                        <Upload size={16}/> Upload
                        <input type="file" className="hidden" onChange={handleUpload}/>
                    </label>
                </div>
            </div>

            {/* List */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                {path && (
                    <div
                        onClick={goUp}
                        className="px-6 py-3 border-b border-slate-800 text-slate-400 hover:bg-slate-800/50 cursor-pointer flex items-center gap-3"
                    >
                        <ArrowLeft size={16}/> .. (Go Up)
                    </div>
                )}

                {items.map((item, idx) => (
                    <div
                        key={idx}
                        className="px-6 py-3 border-b border-slate-800 hover:bg-slate-800/50 flex justify-between items-center group"
                    >
                        <div
                            onClick={() => handleOpen(item)}
                            className="flex items-center gap-3 cursor-pointer flex-1"
                        >
                            {item.type === 'folder' ? (
                                <Folder className="text-yellow-500" size={20}/>
                            ) : (
                                <FileText className="text-blue-400" size={20}/>
                            )}
                            <span className={`text-sm ${item.type === 'folder' ? 'text-white font-medium' : 'text-slate-300'}`}>
                          {item.name}
                      </span>
                        </div>

                        <div className="text-slate-500 text-xs font-mono mr-4">
                            {item.type === 'file' && (item.size / 1024).toFixed(1) + ' KB'}
                        </div>

                        <button
                            onClick={() => handleDelete(item.name)}
                            className="text-slate-600 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                            <Trash2 size={16}/>
                        </button>
                    </div>
                ))}
                {items.length === 0 && (
                    <div className="p-8 text-center text-slate-500">Folder Empty</div>
                )}
            </div>
        </div>
    );
}