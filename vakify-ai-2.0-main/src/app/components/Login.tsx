import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Mail, Lock, Sparkles, BookOpen, TrendingUp } from 'lucide-react';

export function Login() {
  const { login, signup, beginGoogleLogin, beginDevAdminLogin } = useAuth();
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isSignup) {
        if (!displayName.trim()) {
          setError('Please enter your name');
          return;
        }
        await signup(email, password, displayName);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError('');
    setLoading(true);
    try {
      await beginGoogleLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google login failed. Please try again.');
      setLoading(false);
    }
  };

  const handleDevAdminLogin = async () => {
    setError('');
    setLoading(true);
    try {
      await beginDevAdminLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Admin login failed. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-background">
      <div className="hidden lg:flex lg:flex-1 bg-gradient-to-br from-[#1E3A5F] via-[#2a4a6f] to-[#1B998B] relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          {Array.from({ length: 20 }).map((_, i) => (
            <div
              key={i}
              className="absolute bg-white/20"
              style={{
                left: `${(i % 5) * 20}%`,
                top: `${Math.floor(i / 5) * 25}%`,
                width: '2px',
                height: '100%',
                transform: `rotate(${15 + i * 2}deg)`
              }}
            />
          ))}
        </div>

        <div className="relative z-10 flex flex-col justify-center h-full px-16 text-white">
          <div className="mb-12">
            <h1 className="text-5xl mb-4" style={{ fontWeight: 700 }}>
              Vakify 2.0
            </h1>
            <p className="text-xl text-white/90">
              Your adaptive learning operating system
            </p>
          </div>

          <div className="space-y-6 max-w-md">
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <Sparkles className="w-5 h-5 text-[#F4A261]" />
                <h3 className="text-lg">Platform Promise</h3>
              </div>
              <p className="text-white/80 text-sm">
                ChatGPT + Coding Lab + Adaptive Learning + Gamified Progress in one authenticated learning platform.
              </p>
            </div>

            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <BookOpen className="w-5 h-5 text-[#1B998B]" />
                <h3 className="text-lg">Learning Modes</h3>
              </div>
              <p className="text-white/80 text-sm">
                Visual, audio and kinetic learning experiences through response tabs, labs, diagrams and practice loops.
              </p>
            </div>

            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-2">
                <TrendingUp className="w-5 h-5 text-[#F4A261]" />
                <h3 className="text-lg">Track Progress</h3>
              </div>
              <p className="text-white/80 text-sm">
                XP, levels, badges, streaks and personalized insights keep you motivated and on track.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 bg-white flex items-center justify-center px-3 py-4 sm:px-6 sm:py-8 lg:p-8">
        <div className="w-full max-w-sm sm:max-w-md lg:max-w-md">
          <div className="lg:hidden mb-4 rounded-3xl bg-gradient-to-br from-[#1E3A5F] via-[#2a4a6f] to-[#1B998B] text-white p-4 sm:p-5 shadow-lg">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-white/80">
              <Sparkles className="w-4 h-4 text-[#F4A261]" />
              Vakify 2.0
            </div>
            <h1 className="mt-2 text-2xl sm:text-3xl font-bold tracking-tight leading-tight">Your adaptive learning OS</h1>
            <p className="mt-2 text-sm leading-6 text-white/85">
              Learn, chat, practice, and track progress in one place.
            </p>
          </div>

          <div className="mb-5 sm:mb-8">
            <h2 className="text-2xl sm:text-3xl mb-2 leading-tight">
              {isSignup ? 'Create Account' : 'Welcome Back'}
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground">
              {isSignup ? 'Start your learning journey' : 'Sign in to continue your progress'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5 sm:space-y-4">
            {isSignup && (
              <div>
                <label className="block text-sm mb-2">Full Name</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary text-base"
                  placeholder="Enter your name"
                  required={isSignup}
                />
              </div>
            )}

            <div>
              <label className="block text-sm mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 rounded-xl border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary text-base"
                  placeholder="Enter your email"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 rounded-xl border border-border bg-input-background focus:outline-none focus:ring-2 focus:ring-secondary text-base"
                  placeholder="Enter your password"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded-xl text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary text-primary-foreground py-3.5 rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {loading ? 'Please wait...' : (isSignup ? 'Create Account' : 'Sign In')}
            </button>

            <button
              type="button"
              onClick={handleGoogleLogin}
              disabled={loading}
              className="w-full border border-border py-3.5 rounded-xl hover:bg-muted transition-colors flex items-center justify-center gap-3 disabled:opacity-50"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Continue with Google
            </button>

            {import.meta.env.DEV && (
              <button
                type="button"
                onClick={handleDevAdminLogin}
                disabled={loading}
                className="w-full border border-emerald-200 bg-emerald-50 text-emerald-800 py-3.5 rounded-xl hover:bg-emerald-100 transition-colors flex items-center justify-center gap-3 disabled:opacity-50"
              >
                Continue as Admin (Local)
              </button>
            )}

            <div className="hidden sm:block rounded-xl border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
              Use Google for one-click sign in, or create a local account with your email and password.
            </div>
          </form>

          <div className="mt-5 sm:mt-6 text-center">
            <button
              onClick={() => setIsSignup(!isSignup)}
              className="text-secondary hover:underline"
            >
              {isSignup ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
            </button>
          </div>

          {!isSignup && (
            <div className="mt-5 sm:mt-8 p-3.5 sm:p-4 bg-muted/50 rounded-xl">
              <p className="text-sm text-muted-foreground mb-2">Sign in</p>
              <p className="text-xs text-muted-foreground">Use your own account to continue your learning progress.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
