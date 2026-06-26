import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { CheckCircle2, Clock, Trophy, Play, ChevronRight, Code2, Sparkles, Star } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

type TaskContent = {
  mode?: 'code' | 'quiz';
  language?: string;
  language_label?: string;
  task_key?: string;
  starter_code?: string;
  sample_input?: string;
  expected_output?: string;
  hint?: string;
  validation_json?: string[];
  questions?: Array<{
    id: number;
    question: string;
    options: string[];
    answer: string;
  }>;
};

type TaskRow = {
  task_id: number;
  title: string;
  description: string;
  task_type: 'code' | 'quiz' | string;
  difficulty: string;
  status: string;
  points_reward: number;
  due_date: string;
  content: TaskContent;
};

type QuizResponse = {
  quiz: {
    quiz_id: number;
    title: string;
    week_start: string;
    week_end: string;
    difficulty: string;
    language: string;
    language_label: string;
    questions: Array<{
      id: number;
      question: string;
      options: string[];
      answer: string;
    }>;
  };
  attempts: number;
  best_score: number;
};

type RewardSummary = {
  wallet: { current_xp: number; level: number; reward_points: number };
  streak: { current_streak: number; longest_streak: number; last_active_date: string | null };
  recent_xp_events: Array<{ event_id: number; source: string; points: number; created_at: string }>;
};

type QuizModalState = {
  kind: 'daily' | 'weekly';
  title: string;
  points: number;
  questions: Array<{
    id: number;
    question: string;
    options: string[];
    answer: string;
  }>;
  submitId: number;
  summary: string;
};

export function TasksQuiz() {
  const { user, refreshUser } = useAuth();
  const [activeTab, setActiveTab] = useState<'daily' | 'weekly'>('daily');
  const [dailyTasks, setDailyTasks] = useState<TaskRow[]>([]);
  const [weeklyQuiz, setWeeklyQuiz] = useState<QuizResponse['quiz'] | null>(null);
  const [weeklyAttempts, setWeeklyAttempts] = useState(0);
  const [weeklyBestScore, setWeeklyBestScore] = useState(0);
  const [rewards, setRewards] = useState<RewardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [quizModal, setQuizModal] = useState<QuizModalState | null>(null);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, string>>({});
  const [quizResult, setQuizResult] = useState<{ score: number; total: number; xp_awarded: number; passed: boolean } | null>(null);
  const [submittingQuiz, setSubmittingQuiz] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        apiFetch<{ tasks: TaskRow[]; preferred_language: string }>('/api/tasks/today'),
        apiFetch<QuizResponse>('/api/quiz/weekly'),
        apiFetch<RewardSummary>('/api/rewards/summary'),
      ]);

      const [tasksRes, quizRes, rewardRes] = results;
      if (tasksRes.status === 'fulfilled') {
        setDailyTasks(tasksRes.value.tasks || []);
      }
      if (quizRes.status === 'fulfilled') {
        setWeeklyQuiz(quizRes.value.quiz);
        setWeeklyAttempts(quizRes.value.attempts);
        setWeeklyBestScore(quizRes.value.best_score);
      }
      if (rewardRes.status === 'fulfilled') {
        setRewards(rewardRes.value);
      }
    } catch {
      setDailyTasks([]);
      setWeeklyQuiz(null);
      setRewards(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const openQuiz = (kind: 'daily' | 'weekly', title: string, points: number, questions: QuizModalState['questions'], submitId: number, summary: string) => {
    if (!questions.length) {
      setQuizModal({
        kind,
        title,
        points,
        questions: [],
        submitId,
        summary: 'This quiz does not have any questions yet. Refresh the page or sync the task again.',
      });
      setQuizAnswers({});
      setQuizResult(null);
      return;
    }
    setQuizModal({ kind, title, points, questions, submitId, summary });
    setQuizAnswers({});
    setQuizResult(null);
  };

  const submitQuiz = async () => {
    if (!quizModal) {
      return;
    }
    setSubmittingQuiz(true);
    try {
      const endpoint = quizModal.kind === 'daily'
        ? `/api/tasks/${quizModal.submitId}/submit`
        : `/api/quiz/${quizModal.submitId}/submit`;
      const response = await apiFetch<Record<string, any>>(endpoint, {
        method: 'POST',
        body: JSON.stringify({ answers: quizAnswers }),
      });

      const passed = quizModal.kind === 'daily' ? Boolean(response.passed) : Number(response.percentage || 0) >= 70;
      const score = quizModal.kind === 'daily'
        ? Number(response.score ?? 0)
        : Number(response.percentage ?? 0);
      const xp_awarded = Number(response.xp_awarded ?? 0);
      setQuizResult({
        score,
        total: quizModal.questions.length,
        xp_awarded,
        passed,
      });
      await refreshUser();
      await loadData();
      if (passed) {
        setQuizModal(null);
      }
    } catch (error) {
      setQuizResult({
        score: 0,
        total: quizModal.questions.length,
        xp_awarded: 0,
        passed: false,
      });
      if (error instanceof Error) {
        setQuizModal((current) => current ? { ...current, summary: error.message } : current);
      }
    } finally {
      setSubmittingQuiz(false);
    }
  };

  const dailyTaskCards = dailyTasks;
  const weeklyQuestionCount = weeklyQuiz?.questions?.length || 7;
  const currentPreferredLanguage = user?.preferredLanguage || dailyTasks[0]?.content?.language_label || 'Your language';

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl mb-2">Tasks & Quizzes</h1>
        <p className="text-muted-foreground">
          Daily tasks and weekly quizzes adapt to your preferred language and award real XP.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="text-sm text-muted-foreground mb-2">Preferred Language</div>
          <div className="text-2xl">{currentPreferredLanguage}</div>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="text-sm text-muted-foreground mb-2">Reward Points</div>
          <div className="text-2xl text-secondary">{rewards?.wallet.reward_points ?? user?.xp ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
          <div className="text-sm text-muted-foreground mb-2">Current Streak</div>
          <div className="text-2xl text-accent">{rewards?.streak.current_streak ?? user?.streak ?? 0} days</div>
        </div>
      </div>

      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setActiveTab('daily')}
          className={`px-6 py-3 rounded-lg transition-colors ${
            activeTab === 'daily'
              ? 'bg-primary text-primary-foreground'
              : 'bg-card border border-border hover:bg-muted'
          }`}
        >
          Daily Tasks
        </button>
        <button
          onClick={() => setActiveTab('weekly')}
          className={`px-6 py-3 rounded-lg transition-colors ${
            activeTab === 'weekly'
              ? 'bg-primary text-primary-foreground'
              : 'bg-card border border-border hover:bg-muted'
          }`}
        >
          Weekly Quiz
        </button>
      </div>

      {activeTab === 'daily' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {loading && !dailyTaskCards.length ? (
              <div className="col-span-full rounded-2xl border border-border bg-card p-6 text-muted-foreground">
                Loading today&apos;s tasks...
              </div>
            ) : null}

            {dailyTaskCards.map((task) => {
              const isQuiz = task.task_type === 'quiz';
              const isCode = task.task_type === 'code';
              const isCompleted = task.status === 'completed';
              return (
                <div key={task.task_id} className="bg-card border border-border rounded-xl p-6 shadow-sm">
                  <div className="flex items-start justify-between mb-4 gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        {isCode ? <Code2 className="w-5 h-5 text-primary" /> : <Sparkles className="w-5 h-5 text-secondary" />}
                        <h3 className="text-lg">{task.title}</h3>
                        {isCompleted && <CheckCircle2 className="w-5 h-5 text-secondary" />}
                      </div>
                      <p className="text-sm text-muted-foreground">{task.description}</p>
                    </div>
                    <div className="px-3 py-1 bg-accent/10 text-accent rounded-full text-sm shrink-0">
                      +{task.points_reward} XP
                    </div>
                  </div>

                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-muted-foreground">Progress</span>
                      <span className="text-sm">{task.status === 'completed' ? '1/1' : '0/1'}</span>
                    </div>
                    <div className="bg-muted rounded-full h-2">
                      <div
                        className="bg-secondary h-full rounded-full transition-all"
                        style={{ width: isCompleted ? '100%' : '0%' }}
                      />
                    </div>
                  </div>

                  {isCode && task.content?.starter_code ? (
                    <div className="rounded-xl bg-muted/30 border border-border p-4 mb-4">
                      <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground mb-2">Preview</div>
                      <pre className="text-xs font-mono whitespace-pre-wrap overflow-hidden line-clamp-6">
                        {task.content.starter_code}
                      </pre>
                    </div>
                  ) : null}

                  {isQuiz ? (
                    <div className="rounded-xl bg-muted/30 border border-border p-4 mb-4">
                      <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground mb-2">Quiz Ready</div>
                      <div className="text-sm">
                        {task.content?.questions?.length || 5} MCQs about {task.content?.language_label || currentPreferredLanguage}.
                      </div>
                    </div>
                  ) : null}

                  <div className="flex items-center gap-2">
                    {isCode ? (
                      <Link
                        to={`/playground?task_id=${task.task_id}`}
                        className="flex-1 bg-primary text-primary-foreground py-3 rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                      >
                        <Play className="w-5 h-5" />
                        {isCompleted ? 'Review in Playground' : 'Open in Playground'}
                      </Link>
                    ) : (
                      <button
                        onClick={() =>
                          openQuiz(
                            'daily',
                            task.title,
                            task.points_reward,
                            task.content?.questions || [],
                            task.task_id,
                            task.content?.language_label || currentPreferredLanguage,
                          )
                        }
                        disabled={!task.content?.questions?.length}
                        className="flex-1 bg-primary text-primary-foreground py-3 rounded-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Play className="w-5 h-5" />
                        {isCompleted ? 'Review Quiz' : 'Start Quiz'}
                      </button>
                    )}
                    <button className="px-4 py-3 bg-card border border-border rounded-lg hover:bg-muted transition-colors">
                      <Star className="w-5 h-5 text-accent" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="bg-gradient-to-r from-secondary/10 to-accent/10 border border-secondary/20 rounded-xl p-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-secondary/20 flex items-center justify-center">
                <Trophy className="w-8 h-8 text-secondary" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg mb-1">Daily Streak Bonus!</h3>
                <p className="text-sm text-muted-foreground">
                  Complete the code task and quiz to keep your streak alive and earn bonus XP.
                </p>
              </div>
              <div className="text-right">
                <div className="text-2xl text-secondary">+50</div>
                <div className="text-xs text-muted-foreground">Bonus XP</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'weekly' && (
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-primary to-secondary text-white rounded-xl p-8 shadow-lg">
            <div className="flex items-start justify-between mb-6">
              <div>
                <h2 className="text-2xl mb-2">{weeklyQuiz?.title || 'Weekly Quiz'}</h2>
                <p className="text-white/80">
                  Test your knowledge and earn big XP rewards
                </p>
              </div>
              <div className="px-4 py-2 bg-white/20 backdrop-blur-sm rounded-lg text-sm">
                {weeklyQuiz?.difficulty || 'Beginner'}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                <div className="text-white/60 text-sm mb-1">Questions</div>
                <div className="text-2xl">{weeklyQuestionCount}</div>
              </div>
              <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                <div className="text-white/60 text-sm mb-1">Time Limit</div>
                <div className="text-2xl">30 min</div>
              </div>
              <div className="bg-white/10 backdrop-blur-sm rounded-lg p-4">
                <div className="text-white/60 text-sm mb-1">Reward</div>
                <div className="text-2xl">+{weeklyBestScore >= 80 ? 120 : 100}</div>
              </div>
            </div>

            <div className="mb-6">
              <div className="text-sm text-white/60 mb-2">Topics Covered:</div>
              <div className="flex flex-wrap gap-2">
                {(weeklyQuiz?.questions || []).slice(0, 4).map((question) => (
                  <div key={question.id} className="px-3 py-1 bg-white/10 rounded-full text-sm">
                    {question.question.slice(0, 28)}
                    {question.question.length > 28 ? '…' : ''}
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() =>
                weeklyQuiz &&
                openQuiz(
                  'weekly',
                  weeklyQuiz.title,
                  weeklyBestScore >= 80 ? 120 : 100,
                  weeklyQuiz.questions,
                  weeklyQuiz.quiz_id,
                  weeklyQuiz.language_label,
                )
              }
              disabled={!weeklyQuiz?.questions?.length}
              className="w-full bg-white text-primary py-4 rounded-lg hover:bg-white/90 transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Clock className="w-5 h-5" />
              {weeklyAttempts > 0 ? 'Retake Weekly Quiz' : 'Start Quiz Now'}
              </button>
          </div>

          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg">Previous Quiz Attempts</h3>
              <span className="text-sm text-muted-foreground">
                {weeklyAttempts} completed
              </span>
            </div>

            <div className="space-y-3">
              {weeklyAttempts > 0 ? (
                <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50">
                  <div className="w-12 h-12 rounded-full bg-secondary/10 flex items-center justify-center">
                    <Trophy className="w-6 h-6 text-secondary" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm mb-1">{weeklyQuiz?.title || 'Weekly Quiz'}</h4>
                    <div className="text-xs text-muted-foreground">Best score: {weeklyBestScore}%</div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg text-secondary">+{weeklyBestScore >= 80 ? 120 : 100} XP</div>
                    <div className="text-xs text-muted-foreground">{weeklyAttempts} attempts</div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-muted-foreground" />
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-border bg-muted/20 px-4 py-5 text-sm text-muted-foreground">
                  Your first weekly quiz will appear here once you start the current challenge.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {quizModal ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-3xl bg-card border border-border shadow-2xl flex flex-col">
            <div className="flex items-start justify-between gap-4 p-6 border-b border-border">
              <div>
                <div className="text-xs uppercase tracking-[0.35em] text-muted-foreground mb-2">
                  {quizModal.kind === 'daily' ? 'Daily Quiz' : 'Weekly Quiz'}
                </div>
                <h3 className="text-2xl">{quizModal.title}</h3>
                <p className="text-muted-foreground mt-2">{quizModal.summary}</p>
              </div>
              <button
                onClick={() => setQuizModal(null)}
                className="rounded-full border border-border px-4 py-2 text-sm hover:bg-muted"
              >
                Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {!quizModal.questions.length ? (
                <div className="rounded-2xl border border-dashed border-border bg-muted/20 p-6 text-sm text-muted-foreground">
                  {quizModal.summary}
                </div>
              ) : null}

              {quizModal.questions.map((question, index) => (
                <div key={question.id} className="rounded-2xl border border-border bg-muted/20 p-4">
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div>
                      <div className="text-xs uppercase tracking-[0.3em] text-muted-foreground mb-1">
                        Question {index + 1}
                      </div>
                      <h4 className="text-lg">{question.question}</h4>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {question.options.map((option) => (
                      <label
                        key={option}
                        className={`flex items-center gap-3 rounded-xl border px-4 py-3 cursor-pointer transition-colors ${
                          quizAnswers[String(question.id)] === option
                            ? 'border-secondary bg-secondary/10'
                            : 'border-border bg-card hover:bg-muted'
                        }`}
                      >
                        <input
                          type="radio"
                          name={`question-${question.id}`}
                          value={option}
                          checked={quizAnswers[String(question.id)] === option}
                          onChange={() =>
                            setQuizAnswers((current) => ({
                              ...current,
                              [String(question.id)]: option,
                            }))
                          }
                        />
                        <span>{option}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t border-border p-6">
              {quizResult ? (
                <div className="mb-4 rounded-2xl border border-secondary/20 bg-secondary/10 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="text-sm text-secondary">Quiz Result</div>
                      <div className="text-2xl">{quizResult.score}%</div>
                      <div className="text-sm text-muted-foreground">
                        {quizResult.passed ? 'Great work. Points added to your wallet.' : 'You can try again and improve the score.'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-muted-foreground">XP Earned</div>
                      <div className="text-2xl text-secondary">+{quizResult.xp_awarded}</div>
                    </div>
                  </div>
                </div>
              ) : null}
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm text-muted-foreground">
                  {Object.keys(quizAnswers).length}/{quizModal.questions.length} answered
                </div>
                <div className="flex items-center gap-3">
                  {quizResult ? (
                    <>
                      {!quizResult.passed ? (
                        <button
                          onClick={() => {
                            setQuizAnswers({});
                            setQuizResult(null);
                          }}
                          className="rounded-xl border border-border px-4 py-3 hover:bg-muted"
                        >
                          Retry Quiz
                        </button>
                      ) : null}
                      <button
                        onClick={() => setQuizModal(null)}
                        className="rounded-xl bg-primary px-5 py-3 text-primary-foreground hover:opacity-90"
                      >
                        Close
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => setQuizModal(null)}
                        className="rounded-xl border border-border px-4 py-3 hover:bg-muted"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => void submitQuiz()}
                        disabled={submittingQuiz || quizModal.questions.length === 0}
                        className="rounded-xl bg-primary px-5 py-3 text-primary-foreground hover:opacity-90 disabled:opacity-50"
                      >
                        {submittingQuiz ? 'Submitting...' : 'Submit Answers'}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
