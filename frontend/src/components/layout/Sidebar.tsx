'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
    LayoutDashboard,
    Globe,
    Database,
    Settings,
    LogOut,
    Terminal,
    LucideLogs,
    Store,
    Archive,
    Clock,
    Users
} from 'lucide-react';
import clsx from 'clsx'; // Utility buat gabungin class tailwind conditional

const menuItems = [
    { name: 'Overview', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Websites', href: '/dashboard/sites', icon: Globe },
    { name: 'Databases', href: '/dashboard/databases', icon: Database },
    { name: 'Terminal', href: '/dashboard/terminal', icon: Terminal },
    { name: 'Users', href: '/dashboard/users', icon: Users },
    { name: 'Logs', href: '/dashboard/logs', icon: LucideLogs },
    { name: 'App Store', href: '/dashboard/marketplace', icon: Store },
    { name: 'Cron Jobs', href: '/dashboard/cron', icon: Clock },
    { name: 'Backups', href: '/dashboard/backups', icon: Archive },
    { name: 'Settings', href: '/dashboard/settings', icon: Settings },
];

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();

    const handleLogout = () => {
        localStorage.removeItem('token');
        router.push('/login');
    };

    return (
        <aside className="w-64 bg-slate-900 border-r border-slate-800 h-screen fixed left-0 top-0 flex flex-col">
            <div className="p-6 border-b border-slate-800">
                <h1 className="text-xl font-bold text-white tracking-wider">
                    Sarah<span className="text-blue-500">Panel</span>
                </h1>
            </div>

            <nav className="flex-1 p-4 space-y-2">
                {menuItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = pathname === item.href;
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={clsx(
                                'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                                isActive
                                    ? 'bg-blue-600/10 text-blue-500'
                                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                            )}
                        >
                            <Icon size={20} />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            <div className="p-4 border-t border-slate-800">
                <button
                    onClick={handleLogout}
                    className="flex items-center gap-3 px-4 py-3 w-full text-sm font-medium text-red-400 hover:bg-red-900/10 rounded-lg transition-colors"
                >
                    <LogOut size={20} />
                    Logout
                </button>
            </div>
        </aside>
    );
}