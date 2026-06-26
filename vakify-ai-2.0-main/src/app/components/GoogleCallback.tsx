import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '../contexts/AuthContext';

export function GoogleCallback() {
  const { completeGoogleLogin } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');

  useEffect(() => {
    const run = async () => {
      const url = new URL(window.location.href);
      const code = url.searchParams.get('code');
      const state = url.searchParams.get('state');
      const errorParam = url.searchParams.get('error');
      if (errorParam) {
        setError(`Google login failed: ${errorParam}`);
        return;
      }
      if (!code) {
        setError('Google login callback is missing the authorization code.');
        return;
      }

      try {
        const nextUser = await completeGoogleLogin(code, state);
        navigate(nextUser.role === 'admin' ? '/admin' : '/dashboard', { replace: true });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to complete Google login.');
      }
    };

    void run();
  }, [completeGoogleLogin, navigate]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-6">
        <div className="max-w-md w-full rounded-2xl border border-border bg-card p-6 shadow-sm">
          <h1 className="text-2xl mb-2">Google login failed</h1>
          <p className="text-muted-foreground text-sm">{error}</p>
          <button
            onClick={() => navigate('/login', { replace: true })}
            className="mt-6 w-full rounded-xl bg-primary px-4 py-3 text-primary-foreground"
          >
            Back to login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-muted-foreground">Completing Google sign in...</div>
    </div>
  );
}
