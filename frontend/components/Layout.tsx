import Link from 'next/link';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';
import { useState } from 'react';

interface LayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

const navigation = [
  { href: '/dashboard', label: 'Overview', icon: '◈' },
  { href: '/visitors/new', label: 'Create visitor', icon: '+' },
  { href: '/approvals', label: 'Approvals', icon: '✓' },
  { href: '/reports', label: 'Reports', icon: '▤' },
  { href: '/admin/users', label: 'User management', icon: '◎', admin: true },
  { href: '/settings', label: 'Settings', icon: '⚙' }
];

export default function Layout({ children, title, subtitle }: LayoutProps) {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const isAdmin = user?.role === 'SUPER_ADMIN';

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
        <div className="brand"><span className="brand-mark">G</span><span>gatekeeper</span></div>
        <div className="workspace"><span className="location-dot" /> {user?.location || 'All locations'} <span className="chevron">⌄</span></div>
        <nav aria-label="Main navigation">
          <span className="nav-label">Workspace</span>
          {navigation.map((item) => {
            if (item.admin && !isAdmin) return null;
            const active = router.pathname === item.href || router.pathname.startsWith(`${item.href}/`);
            return <Link key={item.href} href={item.href} className={`nav-link ${active ? 'active' : ''}`} onClick={() => setOpen(false)}><span className="nav-icon">{item.icon}</span>{item.label}{item.href === '/approvals' && <span className="nav-badge">8</span>}</Link>;
          })}
        </nav>
        <div className="sidebar-footer"><div className="help-box"><strong>Need help?</strong><span>Visit the operations guide</span><a href="mailto:support@gatekeeper.app">Contact support →</a></div><button className="logout" onClick={logout}>↗ Sign out</button></div>
      </aside>
      <div className="main-area">
        <header className="topbar"><button className="mobile-menu" aria-label="Open navigation" onClick={() => setOpen(!open)}>☰</button><div className="topbar-actions"><button className="icon-button" aria-label="Notifications">♢<span className="notification-dot" /></button><div className="user-menu"><span className="avatar">{user?.name?.slice(0, 2).toUpperCase() || 'AK'}</span><span className="user-name">{user?.name || 'Alex Kim'}<small>{user?.role === 'SUPER_ADMIN' ? 'Super Admin' : 'Approver'}</small></span><span>⌄</span></div></div></header>
        <main className="content"><div className="page-heading"><div><span className="eyebrow">{user?.location || 'OPERATIONS'}</span><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>{router.pathname === '/dashboard' && <button className="button primary" onClick={() => router.push('/visitors/new')}>＋ New visitor</button>}</div>{children}</main>
      </div>
    </div>
  );
}
