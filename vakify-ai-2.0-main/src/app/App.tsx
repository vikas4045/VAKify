import { Component, type ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Landing } from './components/Landing';
import { Login } from './components/Login';
import { GoogleCallback } from './components/GoogleCallback';
import { Onboarding } from './components/Onboarding';
import { AssessmentPage } from './components/AssessmentPage';
import { Layout } from './components/Layout';
import { Dashboard } from './components/Dashboard';
import { AIChat } from './components/AIChat';
import { CodingLab } from './components/CodingLab';
import { TrainingCoder } from './components/TrainingCoder';
import { TasksQuiz } from './components/TasksQuiz';
import { Rewards } from './components/Rewards';
import { Insights } from './components/Insights';
import { AdminConsole } from './components/AdminConsole';
import { Moderation } from './components/Moderation';
import { Settings } from './components/Settings';

class AppErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4">
          <div className="max-w-lg rounded-3xl border border-border bg-card p-8 text-center shadow-sm">
            <div className="text-xl font-semibold text-foreground">Vakify needs a quick refresh</div>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              A screen rendering issue was caught before the page could finish loading. Your data is still safe.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-6 inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-3 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth();

  if (!ready) {
    return null;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!user.onboarded) {
    return <Navigate to="/onboarding" replace />;
  }

  return <Layout>{children}</Layout>;
}

function LearnerRoute({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth();

  if (!ready) {
    return null;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role === 'admin') {
    return <Navigate to="/admin" replace />;
  }

  if (!user.onboarded) {
    return <Navigate to="/onboarding" replace />;
  }

  return <Layout>{children}</Layout>;
}

function AdminRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, ready } = useAuth();

  if (!ready) {
    return null;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  return <Layout>{children}</Layout>;
}

function RoleRoute({
  children,
  allow,
}: {
  children: React.ReactNode;
  allow: Array<'admin' | 'moderator'>;
}) {
  const { user, ready } = useAuth();

  if (!ready) {
    return null;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!allow.includes(user.role as 'admin' | 'moderator')) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Layout>{children}</Layout>;
}

function AppRoutes() {
  const { user, ready } = useAuth();

  if (!ready) {
    return <div className="min-h-screen flex items-center justify-center bg-background text-muted-foreground">Loading Vakify...</div>;
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace /> : <Login />} />
      <Route path="/auth/google/callback" element={<GoogleCallback />} />
      <Route path="/onboarding" element={
        user && !user.onboarded && user.role !== 'admin'
          ? <Onboarding />
          : <Navigate to={user?.role === 'admin' ? '/admin' : '/dashboard'} replace />
      } />
      <Route path="/assessment" element={<LearnerRoute><AssessmentPage /></LearnerRoute>} />

      <Route path="/dashboard" element={<LearnerRoute><Dashboard /></LearnerRoute>} />
      <Route path="/chat" element={<LearnerRoute><AIChat /></LearnerRoute>} />
      <Route path="/lab" element={<LearnerRoute><CodingLab /></LearnerRoute>} />
      <Route path="/playground" element={<LearnerRoute><TrainingCoder /></LearnerRoute>} />
      <Route path="/tasks" element={<LearnerRoute><TasksQuiz /></LearnerRoute>} />
      <Route path="/rewards" element={<LearnerRoute><Rewards /></LearnerRoute>} />
      <Route path="/insights" element={<LearnerRoute><Insights /></LearnerRoute>} />
      <Route path="/moderation" element={<RoleRoute allow={['admin', 'moderator']}><Moderation /></RoleRoute>} />
      <Route path="/admin" element={<AdminRoute><AdminConsole /></AdminRoute>} />
      <Route path="/settings" element={<LearnerRoute><Settings /></LearnerRoute>} />

      <Route path="/" element={user ? <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace /> : <Landing />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppErrorBoundary>
          <AppRoutes />
        </AppErrorBoundary>
      </AuthProvider>
    </BrowserRouter>
  );
}
