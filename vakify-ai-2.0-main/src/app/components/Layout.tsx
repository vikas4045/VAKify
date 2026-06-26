import { ReactNode } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Link, useLocation } from 'react-router';
import {
  LayoutDashboard,
  MessageSquare,
  Code,
  CheckSquare,
  Trophy,
  TrendingUp,
  Settings,
  LogOut,
  Shield,
  Users,
  Menu,
  X
} from 'lucide-react';
import { useState } from 'react';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isAdmin = user?.role === 'admin';
  const isModerator = user?.role === 'moderator' || isAdmin;

  const learnerNav = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/dashboard' },
    { icon: MessageSquare, label: 'AI Chat', path: '/chat' },
    { icon: Code, label: 'Chat Sync Lab', path: '/lab' },
    { icon: Code, label: 'Training Coder', path: '/playground' },
    { icon: CheckSquare, label: 'Tasks & Quiz', path: '/tasks' },
    { icon: Trophy, label: 'Rewards', path: '/rewards' },
    { icon: TrendingUp, label: 'Insights', path: '/insights' },
  ];

  const moderatorNav = [
    { icon: Shield, label: 'Moderation', path: '/moderation' },
  ];

  const adminNav = [
    { icon: Users, label: 'Admin Console', path: '/admin' },
  ];

  const allNav = isAdmin
    ? adminNav
    : [
        ...learnerNav,
        ...(isModerator ? moderatorNav : []),
      ];

  return (
    <div className="flex h-screen bg-background">
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-64 bg-card border-r border-border transform transition-transform ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col h-full">
          <div className="p-6 border-b border-border">
            <div className="flex items-center justify-between">
              <h1 className="text-xl" style={{ fontWeight: 700 }}>
                Vakify
              </h1>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="lg:hidden"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="mt-4">
              <p className="text-sm">{user?.displayName}</p>
              <div className="flex items-center gap-2 mt-1">
                <div className="px-2 py-0.5 rounded text-xs bg-secondary text-secondary-foreground">
                  Level {user?.level}
                </div>
                <div className="text-xs text-muted-foreground">
                  {user?.xp} XP
                </div>
              </div>
              {isAdmin && (
                <div className="mt-3 inline-flex rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                  Admin workspace
                </div>
              )}
            </div>
          </div>

          <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
            {allNav.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-muted text-foreground'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="p-4 border-t border-border space-y-1">
            <Link
              to="/settings"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-muted transition-colors text-foreground"
            >
              <Settings className="w-5 h-5" />
              <span>Settings</span>
            </Link>
            <button
              onClick={logout}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-muted transition-colors text-foreground"
            >
              <LogOut className="w-5 h-5" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </aside>

      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <main className="flex-1 overflow-auto">
        <div className="sticky top-0 z-30 lg:hidden bg-card border-b border-border px-4 py-3">
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="p-2 hover:bg-muted rounded-lg"
          >
            <Menu className="w-6 h-6" />
          </button>
        </div>
        {children}
      </main>
    </div>
  );
}
