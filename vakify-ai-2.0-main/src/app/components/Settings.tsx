import { useEffect, useState } from 'react';
import { User, Bell, Lock, Palette, Globe } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiFetch } from '../lib/api';

type SettingsResponse = {
  theme: 'light' | 'dark' | 'system';
  language: string;
  notifications: {
    daily_tasks?: boolean;
    weekly_quiz?: boolean;
    achievements?: boolean;
    streak_alerts?: boolean;
  };
};

function formatOtherDetails(value: unknown): string {
  if (!value) {
    return '';
  }
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const notes = record.notes;
    if (typeof notes === 'string') {
      return notes;
    }
    try {
      return JSON.stringify(value, null, 0);
    } catch {
      return '';
    }
  }
  return '';
}

export function Settings() {
  const { user, updateUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.displayName || '');
  const [phoneNumber, setPhoneNumber] = useState(user?.phoneNumber || '');
  const [otherDetails, setOtherDetails] = useState(formatOtherDetails(user?.otherDetails));
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>('light');
  const [language, setLanguage] = useState('English');
  const [notifications, setNotifications] = useState({
    daily_tasks: true,
    weekly_quiz: true,
    achievements: true,
    streak_alerts: true,
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const data = await apiFetch<SettingsResponse>('/api/settings/me');
        if (cancelled) {
          return;
        }
        setTheme(data.theme || 'light');
        setLanguage(data.language || 'English');
        setNotifications({
          daily_tasks: data.notifications?.daily_tasks ?? true,
          weekly_quiz: data.notifications?.weekly_quiz ?? true,
          achievements: data.notifications?.achievements ?? true,
          streak_alerts: data.notifications?.streak_alerts ?? true,
        });
      } catch {
        if (!cancelled) {
          setTheme('light');
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setDisplayName(user?.displayName || '');
    setPhoneNumber(user?.phoneNumber || '');
    setOtherDetails(formatOtherDetails(user?.otherDetails));
  }, [user?.displayName, user?.phoneNumber, user?.otherDetails]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const detailsPayload = otherDetails.trim() ? { notes: otherDetails.trim() } : null;
      const detailsChanged =
        formatOtherDetails(user?.otherDetails) !== otherDetails;
      const phoneChanged = phoneNumber.trim() !== (user?.phoneNumber || '');
      const nameChanged = displayName.trim() !== (user?.displayName || '');

      if (nameChanged || phoneChanged || detailsChanged) {
        await updateUser({
          displayName: displayName.trim() || user?.displayName || '',
          phoneNumber: phoneNumber.trim(),
          otherDetails: detailsPayload,
        });
      }

      await apiFetch('/api/settings/me', {
        method: 'PUT',
        body: JSON.stringify({
          theme,
          language,
          notifications,
        }),
      });
      setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl mb-2">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account preferences and privacy settings
        </p>
      </div>

      <div className="space-y-6">
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <User className="w-5 h-5 text-primary" />
            <h3 className="text-lg">Profile Information</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm mb-2">Display Name</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
              />
            </div>
            <div>
              <label className="block text-sm mb-2">Email</label>
              <input
                type="email"
                defaultValue={user?.email}
                className="w-full px-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
                disabled
              />
              <p className="text-xs text-muted-foreground mt-1">Email cannot be changed</p>
            </div>
            <div>
              <label className="block text-sm mb-2">Phone Number</label>
              <input
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
                placeholder="Your phone number"
              />
            </div>
            <div>
              <label className="block text-sm mb-2">Other Details</label>
              <textarea
                value={otherDetails}
                onChange={(e) => setOtherDetails(e.target.value)}
                className="w-full min-h-28 px-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
                placeholder="Tell Vakify anything else we should know"
              />
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <Bell className="w-5 h-5 text-accent" />
            <h3 className="text-lg">Notifications</h3>
          </div>

          <div className="space-y-4">
            {[
              { key: 'daily_tasks' as const, label: 'Daily task reminders', description: 'Get notified about new daily tasks' },
              { key: 'weekly_quiz' as const, label: 'Weekly quiz availability', description: 'Receive alerts when new quizzes are available' },
              { key: 'achievements' as const, label: 'Achievement unlocked', description: 'Celebrate when you earn new badges' },
              { key: 'streak_alerts' as const, label: 'Streak alerts', description: 'Reminders to maintain your learning streak' },
            ].map((item) => (
              <div key={item.label} className="flex items-start justify-between">
                <div>
                  <div className="text-sm mb-1">{item.label}</div>
                  <div className="text-xs text-muted-foreground">{item.description}</div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifications[item.key]}
                    onChange={(e) => setNotifications((prev) => ({ ...prev, [item.key]: e.target.checked }))}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-muted rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-secondary"></div>
                </label>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <Lock className="w-5 h-5 text-destructive" />
            <h3 className="text-lg">Privacy & Security</h3>
          </div>

          <div className="space-y-4">
            <div>
              <button className="text-primary hover:underline text-sm">
                Change Password
              </button>
            </div>
            <div>
              <button className="text-primary hover:underline text-sm">
                Two-Factor Authentication
              </button>
            </div>
            <div>
              <button className="text-destructive hover:underline text-sm">
                Delete Account
              </button>
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <Palette className="w-5 h-5 text-secondary" />
            <h3 className="text-lg">Appearance</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm mb-2">Theme</label>
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value as typeof theme)}
                className="w-full px-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System</option>
              </select>
            </div>
          </div>
        </div>

        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-3 mb-6">
            <Globe className="w-5 h-5 text-accent" />
            <h3 className="text-lg">Language & Region</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm mb-2">Preferred Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full px-4 py-3 rounded-lg border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary"
              >
                <option>English</option>
                <option>Spanish</option>
                <option>French</option>
                <option>German</option>
              </select>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => void handleSave()}
            disabled={saving}
            className="bg-primary text-primary-foreground px-6 py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {saving ? 'Saving...' : saved ? 'Saved' : 'Save Changes'}
          </button>
          <button className="border border-border px-6 py-3 rounded-lg hover:bg-muted transition-colors">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
