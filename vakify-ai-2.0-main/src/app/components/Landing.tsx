import { Link, Navigate } from 'react-router';
import {
  ArrowRight,
  Bot,
  Brain,
  CheckCircle2,
  Code2,
  Layers3,
  Sparkles,
  Trophy,
  TrendingUp,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const featureCards = [
  {
    icon: Bot,
    title: 'AI Chat Tutor',
    text: 'Ask naturally, get structured answers, and continue the same conversation anytime.',
  },
  {
    icon: Code2,
    title: 'Chat Sync Lab',
    text: 'Turn a chat question into a real coding task and save your work in the database.',
  },
  {
    icon: Brain,
    title: 'Daily Quizzes',
    text: 'Language-aware tasks and quizzes are generated once per day and stay saved for the user.',
  },
  {
    icon: Trophy,
    title: 'Rewards & Streaks',
    text: 'Earn XP, level up, and keep your streak alive with every completed task and quiz.',
  },
];

const stats = [
  { value: 'AI', label: 'Guided learning' },
  { value: '5', label: 'Programming languages' },
  { value: 'Daily', label: 'Saved tasks' },
  { value: 'Weekly', label: 'Saved quizzes' },
];

function TopWave() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute -top-28 right-[-8rem] h-80 w-80 rounded-full bg-secondary/20 blur-3xl" />
      <div className="absolute top-40 left-[-10rem] h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
      <div className="absolute bottom-[-8rem] right-1/4 h-72 w-72 rounded-full bg-accent/20 blur-3xl" />
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-border to-transparent" />
    </div>
  );
}

export function Landing() {
  const { user } = useAuth();

  if (user) {
    return <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace />;
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(29,78,216,0.09),transparent_34%),linear-gradient(180deg,#f8fbff_0%,#eef5ff_48%,#f7fafc_100%)]">
      <TopWave />

      <div className="relative mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex items-center justify-between rounded-full border border-border/70 bg-white/80 px-4 py-3 shadow-[0_10px_30px_-24px_rgba(15,23,42,0.35)] backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <div className="text-base font-semibold leading-tight">Vakify</div>
              <div className="text-xs text-muted-foreground">Adaptive learning platform</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/login"
              className="rounded-full border border-border bg-white px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
            >
              Sign in
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-opacity hover:opacity-90"
            >
              Get started
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </header>

        <main className="flex flex-1 flex-col justify-center py-10 lg:py-16">
          <section className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
            <div className="max-w-2xl">
              <div className="inline-flex items-center gap-2 rounded-full border border-secondary/20 bg-secondary/10 px-4 py-2 text-sm font-medium text-secondary">
                <Layers3 className="h-4 w-4" />
                AI chat, labs, quizzes, and rewards in one place
              </div>

              <h1 className="mt-6 text-5xl font-semibold tracking-tight text-foreground sm:text-6xl">
                Learn with a platform that feels like a
                <span className="text-primary"> real companion.</span>
              </h1>

              <p className="mt-5 text-lg leading-8 text-muted-foreground sm:text-xl">
                Vakify combines a natural AI tutor, a saved chat history, a coding lab, daily tasks, and weekly quizzes
                so your learning never resets when you refresh.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 rounded-2xl bg-primary px-6 py-4 text-base font-medium text-primary-foreground shadow-[0_12px_30px_-20px_rgba(29,78,216,0.6)] transition-opacity hover:opacity-90"
                >
                  Start learning
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center gap-2 rounded-2xl border border-border bg-white px-6 py-4 text-base font-medium text-foreground transition-colors hover:bg-muted"
                >
                  See the app
                </Link>
              </div>

              <div className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {stats.map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-3xl border border-border/70 bg-white/80 px-5 py-4 shadow-[0_10px_28px_-24px_rgba(15,23,42,0.35)] backdrop-blur"
                  >
                    <div className="text-3xl font-semibold text-foreground">{stat.value}</div>
                    <div className="mt-1 text-sm text-muted-foreground">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="rounded-[32px] border border-border/70 bg-white/85 p-5 shadow-[0_30px_80px_-44px_rgba(15,23,42,0.45)] backdrop-blur">
                <div className="rounded-[28px] bg-gradient-to-br from-primary to-secondary p-5 text-white shadow-lg">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="text-xs uppercase tracking-[0.3em] text-white/70">Live learning flow</div>
                      <div className="mt-2 text-2xl font-semibold">Chat to Lab to Quiz</div>
                    </div>
                    <div className="rounded-2xl bg-white/15 px-3 py-2 text-sm backdrop-blur">
                      Saved in database
                    </div>
                  </div>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-3xl bg-white/10 p-4">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Bot className="h-4 w-4" />
                        AI Chat
                      </div>
                      <p className="mt-2 text-sm text-white/80">
                        Ask a question, get a rich answer, and keep the context in your thread.
                      </p>
                    </div>
                    <div className="rounded-3xl bg-white/10 p-4">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <Code2 className="h-4 w-4" />
                        Coding Lab
                      </div>
                      <p className="mt-2 text-sm text-white/80">
                        Save code, stdin, output, and run results for both labs.
                      </p>
                    </div>
                    <div className="rounded-3xl bg-white/10 p-4">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <CheckCircle2 className="h-4 w-4" />
                        Daily Tasks
                      </div>
                      <p className="mt-2 text-sm text-white/80">
                        Tasks and quizzes are generated once per day and stay stable.
                      </p>
                    </div>
                    <div className="rounded-3xl bg-white/10 p-4">
                      <div className="flex items-center gap-2 text-sm font-medium">
                        <TrendingUp className="h-4 w-4" />
                        Rewards
                      </div>
                      <p className="mt-2 text-sm text-white/80">
                        XP, levels, and streaks update when you complete learning goals.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  {featureCards.map((card) => {
                    const Icon = card.icon;
                    return (
                      <div
                        key={card.title}
                        className="rounded-[24px] border border-border/70 bg-muted/20 p-4"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary/10 text-secondary">
                            <Icon className="h-5 w-5" />
                          </div>
                          <div>
                            <div className="font-semibold text-foreground">{card.title}</div>
                            <div className="text-sm text-muted-foreground">{card.text}</div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </section>
        </main>

        <footer className="flex flex-col gap-3 border-t border-border/70 py-5 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <div>Vakify combines AI tutoring, coding practice, quizzes, and rewards.</div>
          <div className="flex items-center gap-4">
            <Link to="/login" className="hover:text-foreground transition-colors">
              Sign in
            </Link>
            <Link to="/login" className="hover:text-foreground transition-colors">
              Create account
            </Link>
          </div>
        </footer>
      </div>
    </div>
  );
}
