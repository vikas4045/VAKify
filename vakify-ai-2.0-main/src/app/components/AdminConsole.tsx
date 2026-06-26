import { useEffect, useMemo, useState } from 'react';
import { Activity, Bot, ChartColumn, RefreshCw, Save, Search, Shield, Sparkles, Trophy, Users } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiFetch } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

type AdminSummary = {
  metrics: {
    users: number;
    learning_styles: number;
    chat_messages: number;
    practice_submissions: number;
    downloads: number;
  };
  latest_users: Array<{ user_id: number; name: string; email: string; created_at: string; is_admin: boolean }>;
  latest_chats: Array<{ chat_id: number; user_id: number; question: string; response_type: string; timestamp: string }>;
};

type AdminUser = {
  user_id: number;
  name: string;
  email: string;
  role: 'learner' | 'moderator' | 'admin';
  is_admin: boolean;
  learning_style: string | null;
  created_at: string;
  stats: { chats: number; downloads: number; practice: number };
};

type AdminAnalytics = {
  style_distribution: Record<string, number>;
  daily_signups: Array<{ date: string; count: number }>;
  daily_chats: Array<{ date: string; count: number }>;
  daily_feedback: Array<{ date: string; count: number }>;
  feedback_summary: { total: number; helpful: number; needs_work: number; avg_rating: number };
};

type ChatbotConfig = {
  enabled: boolean;
  assistant_name: string;
  response_style: string;
  max_response_chars: number;
  system_prompt: string;
  updated_at?: string | null;
};

type LeaderboardRow = { rank: number; user_id: number; name: string; score: number };

type LeaderboardSection = {
  scope: string;
  week_key?: string | null;
  week_start?: string | null;
  week_end?: string | null;
  rows: LeaderboardRow[];
  snapshot_count: number;
};

type LeaderboardPayload = {
  weekly: LeaderboardSection;
  all_time: LeaderboardSection;
};

const DEFAULT_PROMPT = "You are Vakify's admin-managed AI tutor. Answer naturally, clearly, and help learners make progress.";

export function AdminConsole() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'users' | 'chatbot' | 'leaderboard' | 'system'>('users');
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [chatbotConfig, setChatbotConfig] = useState<ChatbotConfig | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardPayload | null>(null);
  const [query, setQuery] = useState('');
  const [grantUserId, setGrantUserId] = useState<number | ''>('');
  const [grantPoints, setGrantPoints] = useState(50);
  const [grantReason, setGrantReason] = useState('Great progress');
  const [savingConfig, setSavingConfig] = useState(false);
  const [refreshingLeaderboard, setRefreshingLeaderboard] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [summaryRes, usersRes, analyticsRes, chatbotRes, leaderboardRes] = await Promise.all([
          apiFetch<AdminSummary>('/api/admin/summary'),
          apiFetch<AdminUser[]>('/api/admin/users'),
          apiFetch<AdminAnalytics>('/api/admin/analytics'),
          apiFetch<ChatbotConfig>('/api/admin/chatbot-config'),
          apiFetch<LeaderboardPayload>('/api/admin/leaderboard'),
        ]);
        if (cancelled) {
          return;
        }
        setSummary(summaryRes);
        setUsers(usersRes);
        setAnalytics(analyticsRes);
        setChatbotConfig(chatbotRes);
        setLeaderboard(leaderboardRes);
      } catch {
        if (!cancelled) {
          setSummary(null);
          setUsers([]);
          setAnalytics(null);
          setChatbotConfig(null);
          setLeaderboard(null);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const filteredUsers = useMemo(
    () => users.filter((item) => `${item.name} ${item.email}`.toLowerCase().includes(query.toLowerCase())),
    [query, users],
  );

  const platformStats = [
    { label: 'Total Users', value: String(summary?.metrics.users ?? 0), change: `+${summary?.latest_users.length ?? 0}`, icon: Users, color: 'text-secondary' },
    { label: 'Chats Today', value: String(summary?.metrics.chat_messages ?? 0), change: '+live data', icon: Activity, color: 'text-accent' },
    { label: 'Chatbot Mode', value: chatbotConfig?.enabled ? 'Enabled' : 'Disabled', change: chatbotConfig?.response_style || 'friendly', icon: Bot, color: 'text-primary' },
    { label: 'Leaderboard Rows', value: String((leaderboard?.weekly.rows.length ?? 0) + (leaderboard?.all_time.rows.length ?? 0)), change: 'snapshot-based', icon: Trophy, color: 'text-warning' },
  ];

  const activityData = (analytics?.daily_chats || []).map((row) => ({
    day: row.date.slice(5),
    chats: row.count,
  }));

  const handleDelete = async (userId: number) => {
    await apiFetch(`/api/admin/users/${userId}`, { method: 'DELETE' });
    const refreshed = await apiFetch<AdminUser[]>('/api/admin/users');
    setUsers(refreshed);
  };

  const handleGrantPoints = async () => {
    if (!grantUserId) {
      setStatusMessage('Choose a user first.');
      return;
    }
    setStatusMessage(null);
    await apiFetch(`/api/admin/users/${grantUserId}/grant-points`, {
      method: 'POST',
      body: JSON.stringify({
        points: grantPoints,
        reason: grantReason,
      }),
    });
    setStatusMessage(`Granted ${grantPoints} XP points.`);
  };

  const handleSaveChatbot = async () => {
    if (!chatbotConfig) {
      return;
    }
    setSavingConfig(true);
    setStatusMessage(null);
    try {
      const updated = await apiFetch<ChatbotConfig>('/api/admin/chatbot-config', {
        method: 'PUT',
        body: JSON.stringify({
          enabled: chatbotConfig.enabled,
          assistant_name: chatbotConfig.assistant_name,
          response_style: chatbotConfig.response_style,
          max_response_chars: chatbotConfig.max_response_chars,
          system_prompt: chatbotConfig.system_prompt,
        }),
      });
      setChatbotConfig(updated);
      setStatusMessage('Chatbot settings saved.');
    } finally {
      setSavingConfig(false);
    }
  };

  const handleRefreshLeaderboard = async () => {
    setRefreshingLeaderboard(true);
    setStatusMessage(null);
    try {
      await apiFetch('/api/admin/leaderboard/refresh', { method: 'POST' });
      const refreshed = await apiFetch<LeaderboardPayload>('/api/admin/leaderboard');
      setLeaderboard(refreshed);
      setStatusMessage('Leaderboard snapshots rebuilt.');
    } finally {
      setRefreshingLeaderboard(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="mb-8 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl mb-2">Admin Operations Center</h1>
          <p className="text-muted-foreground">
            Manage users, configure the chatbot, and rebuild leaderboard snapshots from one place.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-2 text-sm text-muted-foreground">
          Signed in as <span className="font-medium text-foreground">{user?.displayName}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {platformStats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <Icon className={`w-6 h-6 ${stat.color}`} />
                <span className="text-sm text-muted-foreground">{stat.change}</span>
              </div>
              <div className="text-3xl mb-1">{stat.value}</div>
              <div className="text-sm text-muted-foreground">{stat.label}</div>
            </div>
          );
        })}
      </div>

      <div className="bg-card border border-border rounded-xl p-6 shadow-sm mb-6">
        <h3 className="text-lg mb-4 flex items-center gap-2">
          <ChartColumn className="w-5 h-5 text-secondary" />
          Platform Activity
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={activityData.length ? activityData : [{ day: 'Mon', chats: 0 }]}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="day" stroke="#64748b" />
            <YAxis stroke="#64748b" />
            <Tooltip />
            <Line type="monotone" dataKey="chats" stroke="#1B998B" strokeWidth={3} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-wrap gap-4 mb-6">
        {[
          { id: 'users' as const, label: 'Users', icon: Users },
          { id: 'chatbot' as const, label: 'Chatbot', icon: Bot },
          { id: 'leaderboard' as const, label: 'Leaderboard', icon: Trophy },
          { id: 'system' as const, label: 'System', icon: Shield },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-card border border-border hover:bg-muted'
              }`}
            >
              <Icon className="w-5 h-5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {statusMessage && (
        <div className="mb-6 rounded-lg border border-secondary/20 bg-secondary/5 px-4 py-3 text-sm text-secondary">
          {statusMessage}
        </div>
      )}

      {activeTab === 'users' && (
        <div className="grid grid-cols-1 xl:grid-cols-[1.2fr_0.8fr] gap-6">
          <div className="bg-card border border-border rounded-xl shadow-sm">
            <div className="p-6 border-b border-border">
              <div className="flex items-center gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search users by name or email..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
                  />
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted/30">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm">User</th>
                    <th className="px-6 py-4 text-left text-sm">Role</th>
                    <th className="px-6 py-4 text-left text-sm">Learning Style</th>
                    <th className="px-6 py-4 text-left text-sm">Activity</th>
                    <th className="px-6 py-4 text-left text-sm">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredUsers.map((userRow) => (
                    <tr key={userRow.user_id} className="hover:bg-muted/50 transition-colors">
                      <td className="px-6 py-4">
                        <div>
                          <div className="text-sm">{userRow.name}</div>
                          <div className="text-xs text-muted-foreground">{userRow.email}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="inline-flex rounded-full bg-secondary/10 px-3 py-1 text-xs font-medium text-secondary">
                          {userRow.role}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm">{userRow.learning_style || 'n/a'}</td>
                      <td className="px-6 py-4 text-sm">
                        {userRow.stats.chats} chats · {userRow.stats.practice} tasks
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => void handleDelete(userRow.user_id)}
                            className="text-destructive hover:underline text-sm"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <h3 className="text-lg mb-4">Grant XP</h3>
              <div className="space-y-4">
                <select
                  value={grantUserId}
                  onChange={(e) => setGrantUserId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm"
                >
                  <option value="">Select user</option>
                  {filteredUsers.map((item) => (
                    <option key={item.user_id} value={item.user_id}>
                      {item.name} ({item.email})
                    </option>
                  ))}
                </select>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="number"
                    min={1}
                    value={grantPoints}
                    onChange={(e) => setGrantPoints(Number(e.target.value))}
                    className="rounded-lg border border-border bg-input-background px-3 py-2 text-sm"
                    placeholder="Points"
                  />
                  <input
                    type="text"
                    value={grantReason}
                    onChange={(e) => setGrantReason(e.target.value)}
                    className="rounded-lg border border-border bg-input-background px-3 py-2 text-sm"
                    placeholder="Reason"
                  />
                </div>
                <button
                  onClick={() => void handleGrantPoints()}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground hover:opacity-90"
                >
                  <Sparkles className="h-4 w-4" />
                  Grant Points
                </button>
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <h3 className="text-lg mb-4">Latest Users</h3>
              <div className="space-y-3">
                {(summary?.latest_users || []).map((item) => (
                  <div key={item.user_id} className="flex items-center justify-between rounded-lg bg-muted/30 px-4 py-3">
                    <div>
                      <div className="text-sm">{item.name}</div>
                      <div className="text-xs text-muted-foreground">{item.email}</div>
                    </div>
                    <div className="text-xs text-muted-foreground">{item.is_admin ? 'admin' : 'learner'}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'chatbot' && (
        <div className="grid grid-cols-1 xl:grid-cols-[1.15fr_0.85fr] gap-6">
          <div className="bg-card border border-border rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between gap-4">
              <h3 className="text-lg">Chatbot Management</h3>
              <label className="inline-flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={chatbotConfig?.enabled ?? false}
                  onChange={(e) =>
                    setChatbotConfig((current) => current ? { ...current, enabled: e.target.checked } : current)
                  }
                  className="h-4 w-4"
                />
                Enabled
              </label>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="mb-2 block text-sm">Assistant Name</label>
                <input
                  type="text"
                  value={chatbotConfig?.assistant_name || ''}
                  onChange={(e) =>
                    setChatbotConfig((current) => current ? { ...current, assistant_name: e.target.value } : current)
                  }
                  className="w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm">Response Style</label>
                <select
                  value={chatbotConfig?.response_style || 'friendly'}
                  onChange={(e) =>
                    setChatbotConfig((current) => current ? { ...current, response_style: e.target.value } : current)
                  }
                  className="w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm"
                >
                  <option value="friendly">friendly</option>
                  <option value="direct">direct</option>
                  <option value="coach">coach</option>
                  <option value="concise">concise</option>
                </select>
              </div>
            </div>

            <div>
              <label className="mb-2 block text-sm">System Prompt</label>
              <textarea
                rows={10}
                value={chatbotConfig?.system_prompt || DEFAULT_PROMPT}
                onChange={(e) =>
                  setChatbotConfig((current) => current ? { ...current, system_prompt: e.target.value } : current)
                }
                className="w-full rounded-lg border border-border bg-input-background px-3 py-3 text-sm"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-4 items-end">
              <div>
                <label className="mb-2 block text-sm">Max Response Chars</label>
                <input
                  type="number"
                  min={400}
                  max={4000}
                  value={chatbotConfig?.max_response_chars ?? 1200}
                  onChange={(e) =>
                    setChatbotConfig((current) =>
                      current ? { ...current, max_response_chars: Number(e.target.value) || 1200 } : current,
                    )
                  }
                  className="w-full rounded-lg border border-border bg-input-background px-3 py-2 text-sm"
                />
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => void handleSaveChatbot()}
                  disabled={savingConfig || !chatbotConfig}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground hover:opacity-90 disabled:opacity-50"
                >
                  <Save className="h-4 w-4" />
                  {savingConfig ? 'Saving...' : 'Save Chatbot Settings'}
                </button>
                <button
                  onClick={() =>
                    setChatbotConfig((current) =>
                      current
                        ? {
                            ...current,
                            system_prompt: DEFAULT_PROMPT,
                            assistant_name: 'Vakify AI',
                            response_style: 'friendly',
                          }
                        : current,
                    )
                  }
                  className="rounded-lg border border-border bg-card px-4 py-2 text-sm hover:bg-muted"
                >
                  Reset Draft
                </button>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <h3 className="text-lg mb-4">Active Bot Snapshot</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <span>{chatbotConfig?.enabled ? 'Enabled' : 'Disabled'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Assistant</span>
                  <span>{chatbotConfig?.assistant_name || 'Vakify AI'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Tone</span>
                  <span>{chatbotConfig?.response_style || 'friendly'}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Limit</span>
                  <span>{chatbotConfig?.max_response_chars ?? 1200} chars</span>
                </div>
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
              <h3 className="text-lg mb-4">Latest Chat Metrics</h3>
              <div className="space-y-3">
                {summary?.latest_chats.slice(0, 5).map((item) => (
                  <div key={item.chat_id} className="rounded-lg bg-muted/30 px-4 py-3">
                    <div className="text-sm line-clamp-1">{item.question}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{item.response_type}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'leaderboard' && (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-lg">Leaderboard Management</h3>
              <p className="text-sm text-muted-foreground">
                Rebuild snapshots and inspect weekly or all-time rankings.
              </p>
            </div>
            <button
              onClick={() => void handleRefreshLeaderboard()}
              disabled={refreshingLeaderboard}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              <RefreshCw className="h-4 w-4" />
              {refreshingLeaderboard ? 'Refreshing...' : 'Rebuild Snapshots'}
            </button>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {(['weekly', 'all_time'] as const).map((scope) => {
              const section = leaderboard?.[scope];
              return (
                <div key={scope} className="bg-card border border-border rounded-xl p-6 shadow-sm">
                  <div className="flex items-center justify-between gap-3 mb-4">
                    <div>
                      <h4 className="text-lg">{scope === 'weekly' ? 'Weekly' : 'All-time'} Leaderboard</h4>
                      <p className="text-sm text-muted-foreground">
                        {section?.snapshot_count ?? 0} snapshot rows saved
                      </p>
                    </div>
                    <div className="text-xs rounded-full bg-secondary/10 px-3 py-1 text-secondary">
                      {section?.week_key || 'live ranking'}
                    </div>
                  </div>
                  <div className="space-y-3">
                    {section?.rows?.length ? section.rows.map((row) => (
                      <div key={`${scope}-${row.user_id}`} className="flex items-center justify-between rounded-lg bg-muted/30 px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary text-sm font-semibold">
                            {row.rank}
                          </div>
                          <div>
                            <div className="text-sm">{row.name}</div>
                            <div className="text-xs text-muted-foreground">User #{row.user_id}</div>
                          </div>
                        </div>
                        <div className="text-sm font-medium">{row.score} XP</div>
                      </div>
                    )) : (
                      <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                        No leaderboard data yet.
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {activeTab === 'system' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h3 className="text-lg mb-4">Platform Health</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Server Uptime</span>
                <span className="text-sm">99.9%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Response Time</span>
                <span className="text-sm">125ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Error Rate</span>
                <span className="text-sm">0.1%</span>
              </div>
            </div>
          </div>

          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h3 className="text-lg mb-4">Content Statistics</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Total Chats</span>
                <span className="text-sm">{summary?.metrics.chat_messages ?? 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Lab Submissions</span>
                <span className="text-sm">{summary?.metrics.practice_submissions ?? 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Downloads</span>
                <span className="text-sm">{summary?.metrics.downloads ?? 0}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
