'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import api from '@/lib/api';
// [BARU] Tambah ikon 'Archive' untuk tombol Unzip
import { Folder, FileText, ArrowLeft, Save, Upload, Trash2, Home, FilePlus, FolderPlus, Edit3, Terminal, X, Archive } from 'lucide-react';
import TerminalView from '@/components/ui/TerminalView';

export default function FileManagerPage() {
    const { id } = useParams();
    const [path, setPath] = useState(''); // Current path (relative)
    const [items, setItems] = useState<any[]>([]);

    // Editor State
    const [editingFile, setEditingFile] = useState<string | null>(null);
    const [fileContent, setFileContent] = useState('');
    const [showTerminal, setShowTerminal] = useState(false);
    const [loading, setLoading] = useState(false);

    const fetchFiles = async () => {
        try {
            // [FIX] Gunakan encodeURIComponent untuk path agar karakter aneh aman
            const res = await api.get(`/files/list/${id}`, {
                params: { path: path }
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

    // --- FITUR BARU: CREATE, RENAME, & EXTRACT ---

    const handleCreate = async (type: 'file' | 'folder') => {
        const name = prompt(`Enter new ${type} name:`);
        if (!name) return;

        try {
            await api.post(`/files/create/${id}`, {
                path: path,
                name: name,
                type: type
            });
            fetchFiles();
        } catch (err: any) {
            alert(err.response?.data?.detail || "Failed to create");
        }
    };

    const handleRename = async (e: React.MouseEvent, oldName: string) => {
        e.stopPropagation();
        const newName = prompt("Enter new name:", oldName);
        if (!newName || newName === oldName) return;

        try {
            await api.put(`/files/rename/${id}`, {
                path: path,
                old_name: oldName,
                new_name: newName
            });
            fetchFiles();
        } catch (err: any) {
            alert(err.response?.data?.detail || "Failed to rename");
        }
    };

    // [BARU] Fungsi Extract Zip
    const handleExtract = async (e: React.MouseEvent, fileName: string) => {
        e.stopPropagation();

        // Konfirmasi sederhana
        if (!confirm(`Extract ${fileName} to current folder?`)) return;

        const archivePath = path ? `${path}/${fileName}` : fileName;

        try {
            // Panggil endpoint backend baru
            await api.post(`/files/extract/${id}`, {
                archive_path: archivePath,
                destination_path: path || "" // Extract ke folder yang sedang dibuka
            });

            alert("Extraction started in background! Refresh list in a few seconds.");

            // Auto refresh setelah 2 detik
            setTimeout(fetchFiles, 2000);

        } catch (err: any) {
            alert(err.response?.data?.detail || "Failed to extract");
        }
    };

    // ------------------------------------

    // Editor Logic
    const openEditor = async (filename: string) => {
        // Cek ekstensi, jangan buka zip di editor text
        if (filename.endsWith('.zip')) {
            alert("Cannot edit zip file directly. Please extract it.");
            return;
        }

        const filePath = path ? `${path}/${filename}` : filename;
        setLoading(true);
        try {
            const res = await api.get(`/files/content/${id}`, {
                params: { path: filePath }
            });
            setFileContent(res.data.content);
            setEditingFile(filePath);
        } catch (err) { alert("Cannot read file"); }
        setLoading(false);
    };

    const saveFile = async () => {
        setLoading(true);
        try {
            await api.post(`/files/save/${id}`, { path: editingFile, content: fileContent });
            alert("File Saved!");
            setEditingFile(null);
        } catch (err) { alert("Failed to save"); }
        setLoading(false);
    };

    // Upload Logic
    const handleUpload = async (e: any) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const safePath = encodeURIComponent(path || "");

            // Pastikan URL backend bersih (hapus trailing slash jika ada)
            // const cleanBackendUrl = backendUrl.replace(/\/$/, "");
            // Anggap user sudah set env dengan benar, biasanya api.ts menghandle base url,
            // tapi untuk upload form-data manual kita fetch langsung.

            const response = await fetch(`${backendUrl}/files/upload/${id}?path=${safePath}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(JSON.stringify(errorData.detail));
            }

            alert("Upload Success!");
            fetchFiles();
        } catch (err: any) {
            console.error(err);
            alert("Upload failed:\n" + err.message);
        } finally {
            setLoading(false);
            e.target.value = null;
        }
    };

    const handleDelete = async (itemName: string) => {
        if(!confirm(`Delete ${itemName}?`)) return;
        const itemPath = path ? `${path}/${itemName}` : itemName;
        try {
            await api.delete(`/files/delete/${id}`, {
                params: { path: itemPath }
            });
            fetchFiles();
        } catch (err) { alert("Delete failed"); }
    };

    // --- RENDER EDITOR ---
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

    // --- RENDER LIST ---
    return (
        <div>
            <h2 className="text-2xl font-bold text-white mb-6">File Manager</h2>

            {/* Toolbar */}
            <div className="bg-slate-900 p-4 rounded-xl border border-slate-800 mb-6 flex flex-wrap justify-between items-center gap-4">
                <div className="flex items-center gap-2 text-slate-400 font-mono text-sm overflow-hidden text-ellipsis whitespace-nowrap max-w-[50%]">
                    <button onClick={() => setPath('')} className="hover:text-white"><Home size={16}/></button>
                    <span>/</span>
                    <span>{path}</span>
                </div>
                <div className="flex gap-2">
                    <button onClick={() => handleCreate('folder')} className="bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded text-sm flex items-center gap-2 transition-colors">
                        <FolderPlus size={16}/> New Folder
                    </button>
                    <button onClick={() => handleCreate('file')} className="bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded text-sm flex items-center gap-2 transition-colors">
                        <FilePlus size={16}/> New File
                    </button>
                    <button
                        onClick={() => setShowTerminal(true)}
                        className="bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded text-sm flex items-center gap-2 transition-colors border border-slate-700"
                    >
                        <Terminal size={16}/> Terminal
                    </button>
                    <label className="cursor-pointer bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm flex items-center gap-2 transition-colors">
                        <Upload size={16}/> Upload
                        <input type="file" className="hidden" onChange={handleUpload}/>
                    </label>
                </div>
            </div>

            {/* List */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden min-h-[400px]">
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
                        className="px-6 py-3 border-b border-slate-800 hover:bg-slate-800/50 flex justify-between items-center group transition-colors"
                    >
                        <div
                            onClick={() => handleOpen(item)}
                            className="flex items-center gap-3 cursor-pointer flex-1"
                        >
                            {item.type === 'folder' ? (
                                <Folder className="text-yellow-500" size={20}/>
                            ) : (
                                // Ubah ikon jika itu file ZIP
                                item.name.endsWith('.zip') ? (
                                    <Archive className="text-orange-400" size={20}/>
                                ) : (
                                    <FileText className="text-blue-400" size={20}/>
                                )
                            )}
                            <span className={`text-sm ${item.type === 'folder' ? 'text-white font-medium' : 'text-slate-300'}`}>
                                {item.name}
                            </span>
                        </div>

                        <div className="flex items-center gap-4">
                            <span className="text-slate-500 text-xs font-mono hidden sm:block">
                                {item.type === 'file' && (item.size / 1024).toFixed(1) + ' KB'}
                            </span>

                            {/* [BARU] Tombol Extract (Hanya muncul kalau file zip) */}
                            {item.type === 'file' && item.name.endsWith('.zip') && (
                                <button
                                    onClick={(e) => handleExtract(e, item.name)}
                                    className="text-slate-600 hover:text-orange-400 opacity-0 group-hover:opacity-100 transition-opacity"
                                    title="Extract Here"
                                >
                                    <Archive size={16}/>
                                </button>
                            )}

                            <button
                                onClick={(e) => handleRename(e, item.name)}
                                className="text-slate-600 hover:text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Rename"
                            >
                                <Edit3 size={16}/>
                            </button>

                            <button
                                onClick={(e) => { e.stopPropagation(); handleDelete(item.name); }}
                                className="text-slate-600 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                title="Delete"
                            >
                                <Trash2 size={16}/>
                            </button>
                        </div>
                    </div>
                ))}
                {items.length === 0 && (
                    <div className="p-8 text-center text-slate-500">Folder Empty</div>
                )}
            </div>

            {showTerminal && (
                <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
                    <div className="w-full max-w-6xl relative">
                        <div className="flex justify-between items-center mb-2 bg-slate-900/80 p-2 rounded-t-xl border-x border-t border-slate-700">
                            <h3 className="text-white font-mono flex items-center gap-2 px-2">
                                <Terminal size={18} className="text-green-500"/>
                                Quick Terminal
                            </h3>
                            <button onClick={() => setShowTerminal(false)} className="text-slate-400 hover:text-white p-1.5"><X size={20}/></button>
                        </div>
                        <div className="bg-slate-950 rounded-b-xl overflow-hidden border border-slate-700 shadow-2xl">
                            <TerminalView siteId={Array.isArray(id) ? id[0] : id} />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}