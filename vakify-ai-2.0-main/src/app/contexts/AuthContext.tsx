import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { apiFetch, setAuthToken, getAuthToken } from '../lib/api';

export type UserRole = 'learner' | 'moderator' | 'admin';

export interface User {
  id: string;
  email: string;
  displayName: string;
  avatar?: string;
  role: UserRole;
  xp: number;
  level: number;
  streak: number;
  accuracy: number;
  learningLevel?: string;
  learningStyle?: 'visual' | 'auditory' | 'kinesthetic';
  preferredLanguage?: string;
  visualWeight?: number;
  auditoryWeight?: number;
  kinestheticWeight?: number;
  weakTopics?: string[];
  phoneNumber?: string;
  otherDetails?: Record<string, unknown> | string | null;
  onboarded: boolean;
}

interface AuthContextType {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  beginDevAdminLogin: () => Promise<void>;
  beginGoogleLogin: () => Promise<void>;
  completeGoogleLogin: (code: string, state?: string | null) => Promise<User>;
  signup: (email: string, password: string, displayName: string) => Promise<void>;
  completeOnboarding: (updates: Partial<User> & { phoneNumber?: string; otherDetails?: Record<string, unknown> | string | null }) => Promise<void>;
  logout: () => void;
  updateUser: (updates: Partial<User>) => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const restoreSession = async () => {
      const token = getAuthToken();
      if (!token) {
        setReady(true);
        return;
      }

      try {
        const response = await apiFetch<Record<string, any>>('/api/auth/me');
        setUser(mapUser(response));
      } catch {
        setAuthToken(null);
        setUser(null);
      } finally {
        setReady(true);
      }
    };

    void restoreSession();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await apiFetch<Record<string, any>>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
      skipAuth: true,
    });
    setAuthToken(response.access_token ? String(response.access_token) : null);
    setUser(mapUser(response.user));
  };

  const beginDevAdminLogin = async () => {
    const response = await apiFetch<Record<string, any>>('/api/auth/dev-login-admin', {
      method: 'POST',
      skipAuth: true,
    });
    setAuthToken(response.access_token ? String(response.access_token) : null);
    setUser(mapUser(response.user));
  };

  const beginGoogleLogin = async () => {
    const config = await apiFetch<Record<string, any>>('/api/auth/google/config', { skipAuth: true });
    const clientId = String(config.client_id || '').trim();
    const redirectUri = String(config.redirect_uri || '').trim();
    if (!clientId || !redirectUri) {
      throw new Error('Google login is not configured yet.');
    }

    const state = crypto.randomUUID();
    window.sessionStorage.setItem('vakify.google_oauth_state', state);
    window.sessionStorage.setItem('vakify.google_oauth_redirect', redirectUri);

    const params = new URLSearchParams({
      client_id: clientId,
      redirect_uri: redirectUri,
      response_type: 'code',
      scope: 'openid email profile',
      prompt: 'select_account',
      access_type: 'offline',
      state,
    });
    window.location.assign(`https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`);
  };

  const completeGoogleLogin = async (code: string, state?: string | null) => {
    const expectedState = window.sessionStorage.getItem('vakify.google_oauth_state');
    const redirectUri = window.sessionStorage.getItem('vakify.google_oauth_redirect') || `${window.location.origin}/auth/google/callback`;
    if (expectedState && state && expectedState !== state) {
      throw new Error('Google login state did not match. Please try again.');
    }

    const response = await apiFetch<Record<string, any>>('/api/auth/google/exchange', {
      method: 'POST',
      body: JSON.stringify({ code, redirect_uri: redirectUri }),
      skipAuth: true,
    });
    window.sessionStorage.removeItem('vakify.google_oauth_state');
    window.sessionStorage.removeItem('vakify.google_oauth_redirect');
    setAuthToken(response.access_token ? String(response.access_token) : null);
    const nextUser = mapUser(response.user);
    setUser(nextUser);
    return nextUser;
  };

  const signup = async (email: string, password: string, displayName: string) => {
    const response = await apiFetch<Record<string, any>>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
      skipAuth: true,
    });
    setAuthToken(response.access_token ? String(response.access_token) : null);
    setUser(mapUser(response.user));
  };

  const completeOnboarding = async (
    updates: Partial<User> & { phoneNumber?: string; otherDetails?: Record<string, unknown> | string | null },
  ) => {
    const response = await apiFetch<Record<string, any>>('/api/auth/onboarding/complete', {
      method: 'POST',
      body: JSON.stringify({
        name: updates.displayName,
        email: updates.email,
        preferred_language: updates.preferredLanguage,
        phone_number: updates.phoneNumber,
        other_details: updates.otherDetails,
      }),
    });
    setUser(mapUser(response.user));
  };

  const logout = async () => {
    try {
      await apiFetch('/api/auth/logout', { method: 'POST' });
    } catch {
      // Logout should still clear local state if the token is already expired.
    }
    setAuthToken(null);
    setUser(null);
  };

  const updateUser = async (updates: Partial<User>) => {
    if (user) {
      const payload: Record<string, unknown> = {};
      if (updates.displayName !== undefined) payload.name = updates.displayName;
      if (updates.learningLevel !== undefined) payload.learning_level = updates.learningLevel;
      if (updates.preferredLanguage !== undefined) payload.preferred_language = updates.preferredLanguage;
      if (updates.weakTopics !== undefined) payload.weak_topics = updates.weakTopics;
      if (updates.visualWeight !== undefined) payload.visual_weight = updates.visualWeight;
      if (updates.auditoryWeight !== undefined) payload.auditory_weight = updates.auditoryWeight;
      if (updates.kinestheticWeight !== undefined) payload.kinesthetic_weight = updates.kinestheticWeight;
      if (updates.phoneNumber !== undefined) payload.phone_number = updates.phoneNumber;
      if (updates.otherDetails !== undefined) payload.other_details = updates.otherDetails;
      if (updates.xp !== undefined) payload.xp = updates.xp;
      if (updates.level !== undefined) payload.level = updates.level;
      if (updates.streak !== undefined) payload.streak = updates.streak;
      if (updates.accuracy !== undefined) payload.accuracy = updates.accuracy;

      let nextUser: User = { ...user, ...updates };
      if (Object.keys(payload).length > 0) {
        const response = await apiFetch<Record<string, any>>('/api/auth/me', {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
        nextUser = {
          ...mapUser(response.user || response),
          ...updates,
        };
      }
      setUser(nextUser);
    }
  };

  const refreshUser = async () => {
    if (!getAuthToken()) {
      return;
    }
    const response = await apiFetch<Record<string, any>>('/api/auth/me');
    setUser(mapUser(response));
  };

  return (
    <AuthContext.Provider value={{ user, ready, login, beginDevAdminLogin, beginGoogleLogin, completeGoogleLogin, signup, completeOnboarding, logout, updateUser, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

function mapUser(data: Record<string, any>): User {
  return {
    id: String(data.id ?? data.user_id ?? ''),
    email: String(data.email ?? ''),
    displayName: String(data.displayName ?? data.name ?? data.email ?? 'Learner'),
    avatar: data.avatar ?? undefined,
    role: (data.role === 'admin' || data.role === 'moderator' ? data.role : 'learner') as User['role'],
    xp: Number(data.xp ?? 0),
    level: Number(data.level ?? 1),
    streak: Number(data.streak ?? 0),
    accuracy: Number(data.accuracy ?? 0),
    learningLevel: data.learningLevel ?? data.learning_level ?? undefined,
    learningStyle: data.learningStyle ?? data.learning_style ?? undefined,
    preferredLanguage: data.preferredLanguage ?? data.preferred_language ?? undefined,
    visualWeight: data.visualWeight ?? data.visual_weight ?? undefined,
    auditoryWeight: data.auditoryWeight ?? data.auditory_weight ?? undefined,
    kinestheticWeight: data.kinestheticWeight ?? data.kinesthetic_weight ?? undefined,
    weakTopics: data.weakTopics ?? data.weak_topics ?? undefined,
    phoneNumber: data.phoneNumber ?? data.phone_number ?? undefined,
    otherDetails: data.otherDetails ?? data.other_details ?? data.other_details_json ?? undefined,
    onboarded: Boolean(data.onboarded),
  };
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
