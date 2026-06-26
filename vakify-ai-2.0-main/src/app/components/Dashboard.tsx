import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import {
  TrendingUp,
  Flame,
  Target,
  Award,
  ChevronRight,
  Clock,
  BookOpen,
  Code,
  Trophy,
  Zap
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { useAuth } from '../contexts/AuthContext';
import { apiFetch } from '../lib/api';

type TimelineRow = { date: string; count: number };

type DashboardSummary = {
  mastery_score: number;
  streak_days: number;
  recommended_topic: string;
  daily_chat: TimelineRow[];
  daily_practice: TimelineRow[];
  daily_downloads: TimelineRow[];
  topic_confidence: Array<{ topic: string; confidence: number; trend: string }>;
  learning_style_breakdown: Array<{ subject: string; value: number }>;
  weak_topics: Array<{ name: string; score: number; priority: string; color: string }>;
  performance_over_time: Array<{ week: string; score: number }>;
  skill_distribution: Array<{ name: string; value: number }>;
};

type RewardSummary = {
  wallet: { current_xp: number; level: number; reward_points: number };
  streak: { current_streak: number; longest_streak: number; last_active_date: string | null };
  earned_badges?: Array<{ name: string; description: string; icon: string; earned: boolean }>;
  recent_xp_events: Array<{ event_id: number; source: string; points: number; created_at: string }>;
};

type TaskRow = {
  task_id: number;
  title: string;
  description: string;
  task_type: string;
  difficulty: string;
  status: string;
  points_reward: number;
};

type QuizResponse = {
  quiz: {
    quiz_id: number;
    title: string;
    week_start: string;
    week_end: string;
    difficulty: string;
    questions: Array<{ id: number }>;
  };
  attempts: number;
  best_score: number;
};

type LeaderboardResponse = {
  rows: Array<{ rank: number; name: string; score: number }>;
  me: { rank: number | null; score: number };
};

export function Dashboard() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [rewards, setRewards] = useState<RewardSummary | null>(null);
  const [tasks, setTasks] = useState<TaskRow[]>([]);
  const [quiz, setQuiz] = useState<QuizResponse['quiz'] | null>(null);
  const [quizAttempts, setQuizAttempts] = useState(0);
  const [quizBestScore, setQuizBestScore] = useState(0);
  const [leaderboard, setLeaderboard] = useState<LeaderboardResponse['rows']>([]);
  const [myRank, setMyRank] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const results = await Promise.allSettled([
          apiFetch<DashboardSummary>('/api/dashboard/insights'),
          apiFetch<RewardSummary>('/api/rewards/summary'),
          apiFetch<{ tasks: TaskRow[] }>('/api/tasks/today'),
          apiFetch<QuizResponse>('/api/quiz/weekly'),
          apiFetch<LeaderboardResponse>('/api/leaderboard?scope=weekly'),
        ]);

        if (cancelled) {
          return;
        }

        const [summaryRes, rewardsRes, tasksRes, quizRes, leaderboardRes] = results;
        if (summaryRes.status === 'fulfilled') setSummary(summaryRes.value);
        if (rewardsRes.status === 'fulfilled') setRewards(rewardsRes.value);
        if (tasksRes.status === 'fulfilled') setTasks(tasksRes.value.tasks || []);
        if (quizRes.status === 'fulfilled') {
          setQuiz(quizRes.value.quiz);
          setQuizAttempts(quizRes.value.attempts);
          setQuizBestScore(quizRes.value.best_score);
        }
        if (leaderboardRes.status === 'fulfilled') {
          setLeaderboard(leaderboardRes.value.rows || []);
          setMyRank(leaderboardRes.value.me.rank);
        }
      } catch {
        if (!cancelled) {
          setSummary(null);
          setRewards(null);
          setTasks([]);
          setQuiz(null);
          setLeaderboard([]);
          setMyRank(null);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const xpData = (() => {
    if (!summary) {
      return [];
    }
    const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const totals = new Map<string, number>();
    [...summary.daily_chat, ...summary.daily_practice, ...summary.daily_downloads].forEach((row) => {
      const parsed = new Date(`${row.date}T00:00:00`);
      const label = labels[parsed.getDay() === 0 ? 6 : parsed.getDay() - 1];
      totals.set(label, (totals.get(label) || 0) + row.count);
    });

    return labels.map((day, idx) => ({
      day,
      xp: (totals.get(day) || 0) * 40 + (idx + 1) * 15,
    }));
  })();

  const languageProgress = summary?.learning_style_breakdown || [];

  const leaderboardRows = leaderboard;
  const earnedBadges = rewards?.earned_badges?.filter((badge) => badge.earned) || [];
  const lockedBadges = rewards?.earned_badges?.filter((badge) => !badge.earned) || [];
  const badgeCount = earnedBadges.length;

  const completedTasks = tasks.filter((task) => task.status === 'completed').length;
  const dailyTask = tasks[0]
    ? {
        title: tasks[0].title,
        description: tasks[0].description,
        progress: completedTasks,
        total: Math.max(tasks.length, 1),
        xp: tasks[0].points_reward,
      }
    : null;

  const weeklyQuiz = quiz
    ? {
        title: quiz.title,
        questions: quiz.questions?.length || 0,
        timeLimit: '30 min',
        xp: quizBestScore >= 80 ? 200 : 150,
        available: true,
        attempts: quizAttempts,
        bestScore: quizBestScore,
      }
    : {
        title: 'No weekly quiz available yet',
        questions: 0,
        timeLimit: '30 min',
        xp: 0,
        available: false,
        attempts: 0,
        bestScore: 0,
      };

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl mb-2">
          Welcome back, {user?.displayName}!
        </h1>
        <p className="text-muted-foreground">
          Let&apos;s continue your learning journey
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-gradient-to-br from-secondary to-secondary/80 text-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <TrendingUp className="w-8 h-8" />
            <div className="px-3 py-1 bg-white/20 rounded-full text-xs">
              Level {rewards?.wallet.level ?? user?.level}
            </div>
          </div>
          <div className="text-3xl mb-1">{rewards?.wallet.current_xp ?? user?.xp ?? 0} XP</div>
          <div className="text-white/80 text-sm">Total Experience</div>
          <div className="mt-4 bg-white/20 rounded-full h-2">
            <div
              className="bg-white h-full rounded-full"
              style={{ width: `${((rewards?.wallet.current_xp ?? user?.xp ?? 0) % 500) / 5}%` }}
            />
          </div>
          <div className="text-xs text-white/60 mt-1">
            {500 - ((rewards?.wallet.current_xp ?? user?.xp ?? 0) % 500)} XP to next level
          </div>
        </div>

        <div className="bg-gradient-to-br from-accent to-accent/80 text-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <Flame className="w-8 h-8" />
            <div className="px-3 py-1 bg-white/20 rounded-full text-xs">
              On Fire!
            </div>
          </div>
          <div className="text-3xl mb-1">{rewards?.streak.current_streak ?? user?.streak ?? 0} Days</div>
          <div className="text-white/80 text-sm">Current Streak</div>
          <div className="mt-4 text-xs text-white/90">
            Keep going! You&apos;re on a roll
          </div>
        </div>

        <div className="bg-gradient-to-br from-primary to-primary/80 text-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <Target className="w-8 h-8" />
            <div className="px-3 py-1 bg-white/20 rounded-full text-xs">
              Great!
            </div>
          </div>
          <div className="text-3xl mb-1">{user?.accuracy ?? summary?.mastery_score ?? 0}%</div>
          <div className="text-white/80 text-sm">Accuracy Rate</div>
          <div className="mt-4 text-xs text-white/90">
            You&apos;re doing excellent
          </div>
        </div>

        <div className="bg-gradient-to-br from-destructive to-destructive/80 text-white rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <Award className="w-8 h-8" />
            <div className="px-3 py-1 bg-white/20 rounded-full text-xs">
              {badgeCount > 0 ? 'Earned' : 'Starting out'}
            </div>
          </div>
          <div className="text-3xl mb-1">{badgeCount}</div>
          <div className="text-white/80 text-sm">Total Badges</div>
          <div className="mt-4 text-xs text-white/90">
            {badgeCount > 0
              ? `${lockedBadges.length} more to unlock`
              : 'Complete tasks and quizzes to earn your first badge'}
          </div>
        </div>
      </div>

      <div className="mb-8 rounded-2xl border border-border bg-card p-5 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Vakify assessment</div>
            <h2 className="mt-2 text-xl font-semibold">
              {user?.learningStyle ? `Your learning style: ${user.learningStyle}` : 'Take your learning style test'}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground max-w-2xl">
              This 20-question test helps Vakify adapt explanations, tasks, and recommendations to your visual, auditory, or kinesthetic preference.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              to="/assessment"
              className="inline-flex items-center justify-center rounded-2xl bg-primary px-5 py-3 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
            >
              {user?.learningStyle ? 'Retake assessment' : 'Start assessment'}
            </Link>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h3 className="text-lg mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-secondary" />
              XP Progress This Week
            </h3>
            {xpData.length ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={xpData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="day" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Line type="monotone" dataKey="xp" stroke="#1B998B" strokeWidth={3} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
                Complete tasks and quizzes to populate your weekly XP chart.
              </div>
            )}
          </div>

          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h3 className="text-lg mb-4 flex items-center gap-2">
              <Code className="w-5 h-5 text-primary" />
              Learning Style Mix
            </h3>
            {languageProgress.length ? (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={languageProgress}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="subject" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Bar dataKey="value" fill="#1E3A5F" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
                Complete your onboarding style survey to see your live learning mix.
              </div>
            )}
          </div>

          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-accent" />
                Daily Task
              </h3>
              {dailyTask && (
                <span className="text-sm text-muted-foreground">
                  +{dailyTask.xp} XP
                </span>
              )}
            </div>
              {dailyTask ? (
                <>
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-base">{dailyTask.title}</h4>
                      <span className="text-sm text-muted-foreground">
                        {dailyTask.progress}/{dailyTask.total}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-3">
                      {dailyTask.description}
                    </p>
                    <div className="bg-muted rounded-full h-2">
                      <div
                        className="bg-secondary h-full rounded-full transition-all"
                        style={{ width: `${Math.min(100, (dailyTask.progress / dailyTask.total) * 100)}%` }}
                      />
                    </div>
                  </div>
                  <Link
                    to="/tasks"
                    className="inline-flex items-center gap-2 text-secondary hover:underline"
                  >
                    Continue Task
                    <ChevronRight className="w-4 h-4" />
                  </Link>
                </>
              ) : (
                <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                  No daily task available yet. Open Tasks & Quizzes to generate today&apos;s work.
                </div>
              )}
            </div>
          </div>

        <div className="space-y-6">
          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg flex items-center gap-2">
                <Clock className="w-5 h-5 text-destructive" />
                Weekly Quiz
              </h3>
              {weeklyQuiz.available && (
                <div className="px-2 py-1 bg-secondary/10 text-secondary text-xs rounded">
                  Available
                </div>
              )}
            </div>
            <h4 className="text-base mb-3">{weeklyQuiz.title}</h4>
            <div className="space-y-2 mb-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Questions</span>
                <span>{weeklyQuiz.questions}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Time Limit</span>
                <span>{weeklyQuiz.timeLimit}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Reward</span>
                <span className="text-accent">+{weeklyQuiz.xp} XP</span>
              </div>
            </div>
            {weeklyQuiz.available ? (
              <Link
                to="/tasks"
                className="w-full block text-center bg-primary text-primary-foreground py-3 rounded-lg hover:opacity-90 transition-opacity"
              >
                Start Quiz
              </Link>
            ) : (
              <div className="w-full block text-center bg-muted text-muted-foreground py-3 rounded-lg">
                Quiz not ready yet
              </div>
            )}
          </div>

          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <h3 className="text-lg mb-4 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-accent" />
              Leaderboard
            </h3>
            {leaderboardRows.length ? (
              <div className="space-y-2">
                {leaderboardRows.slice(0, 5).map((entry) => (
                  <div
                    key={entry.rank}
                    className={`flex items-center justify-between p-3 rounded-lg ${
                      entry.rank === myRank
                        ? 'bg-secondary/10 border border-secondary'
                        : 'bg-muted/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-sm">
                        {entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : entry.rank}
                      </div>
                      <div>
                        <div className="text-sm">{entry.name}</div>
                        <div className="text-xs text-muted-foreground">{entry.score} XP</div>
                      </div>
                    </div>
                    {entry.rank === myRank && (
                      <Zap className="w-4 h-4 text-secondary" />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                No leaderboard activity yet. Start earning XP to appear here.
              </div>
            )}
            <Link
              to="/rewards"
              className="mt-4 inline-flex items-center gap-2 text-secondary hover:underline"
            >
              View All Rewards
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
