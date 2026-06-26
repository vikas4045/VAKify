import { useEffect, useMemo, useState } from 'react';
import { Brain, CheckCircle2, ChevronLeft, ChevronRight, Loader2, Sparkles } from 'lucide-react';
import { apiFetch } from '../lib/api';

type AssessmentQuestion = {
  id: string;
  prompt: string;
  options: string[];
  topic: string;
};

type AssessmentResult = {
  learning_style: 'visual' | 'auditory' | 'kinesthetic';
  visual_score: number;
  auditory_score: number;
  kinesthetic_score: number;
  total: number;
  percentage: number;
  weak_topics: string[];
  recommended_level?: string;
};

type AssessmentPayload = {
  assessment: AssessmentResult;
};

interface AssessmentWizardProps {
  title: string;
  description: string;
  showSkip?: boolean;
  skipLabel?: string;
  continueLabel?: string;
  onCompleted: (assessment: AssessmentResult) => void | Promise<void>;
  onSkip?: () => void;
}

export function AssessmentWizard({
  title,
  description,
  showSkip = true,
  skipLabel = 'Skip for now',
  continueLabel = 'Continue',
  onCompleted,
  onSkip,
}: AssessmentWizardProps) {
  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [assessmentResult, setAssessmentResult] = useState<AssessmentResult | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadQuestions = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await apiFetch<{ questions: AssessmentQuestion[]; saved?: boolean; assessment?: AssessmentResult }>('/api/assessment/questions');
        if (cancelled) {
          return;
        }
        const nextQuestions = response.questions || [];
        setQuestions(nextQuestions);
        setAnswers((current) => {
          const next = { ...current };
          nextQuestions.forEach((question) => {
            if (!(question.id in next)) {
              next[question.id] = -1;
            }
          });
          return next;
        });
        if (response.saved && response.assessment) {
          setAssessmentResult(response.assessment);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Unable to load assessment questions.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadQuestions();
    return () => {
      cancelled = true;
    };
  }, []);

  const answeredCount = useMemo(
    () => Object.values(answers).filter((value) => value !== -1 && value !== undefined).length,
    [answers],
  );

  const currentQuestion = questions[currentIndex] || null;
  const currentAnswer = currentQuestion ? answers[currentQuestion.id] : -1;
  const totalQuestions = questions.length;
  const progressPercent = totalQuestions ? Math.round((answeredCount / totalQuestions) * 100) : 0;

  const submitAssessment = async () => {
    if (!questions.length || answeredCount < questions.length || saving) {
      return;
    }

    setSaving(true);
    setError('');
    try {
      const response = await apiFetch<AssessmentPayload>('/api/assessment/submit', {
        method: 'POST',
        body: JSON.stringify({
          answers,
        }),
      });
      setAssessmentResult(response.assessment);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save assessment.');
    } finally {
      setSaving(false);
    }
  };

  const currentStyle = assessmentResult?.learning_style || 'visual';

  return (
    <div className="space-y-5">
      <div className="rounded-[28px] border border-border bg-gradient-to-br from-card to-muted/30 p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-secondary/10 flex items-center justify-center">
                <Brain className="w-6 h-6 text-secondary" />
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Learning Style Assessment</div>
                <h2 className="mt-1 text-2xl sm:text-3xl font-semibold tracking-tight">{title}</h2>
              </div>
            </div>
            <p className="mt-3 max-w-2xl text-sm sm:text-base leading-6 text-muted-foreground">
              {description}
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-background px-4 py-3 text-sm text-muted-foreground shadow-sm">
            <div className="text-xs uppercase tracking-[0.2em]">Progress</div>
            <div className="mt-1 text-base font-medium text-foreground">
              {assessmentResult ? 'Completed' : `${Math.min(currentIndex + 1, totalQuestions || 1)} / ${Math.max(totalQuestions, 1)}`}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-2 rounded-2xl border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading your assessment...
        </div>
      )}

      {!loading && !assessmentResult && currentQuestion && (
        <div className="rounded-[28px] border border-border bg-card p-5 sm:p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4 mb-5">
            <div>
              <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Question {currentIndex + 1} of {totalQuestions}
              </div>
              <h3 className="mt-2 text-lg sm:text-xl font-semibold leading-snug">{currentQuestion.prompt}</h3>
            </div>
            <div className="hidden sm:inline-flex rounded-full bg-secondary/10 px-3 py-1 text-xs font-medium text-secondary">
              {currentQuestion.topic}
            </div>
          </div>

          <div className="mb-4 h-2 rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-secondary transition-all"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {currentQuestion.options.map((option, optionIndex) => {
              const selected = currentAnswer === optionIndex;
              return (
                <button
                  key={`${currentQuestion.id}-${optionIndex}`}
                  type="button"
                  onClick={() =>
                    setAnswers((current) => ({
                      ...current,
                      [currentQuestion.id]: optionIndex,
                    }))
                  }
                  className={`rounded-2xl border px-4 py-4 text-left text-sm transition-all ${
                    selected
                      ? 'border-secondary bg-secondary/5 text-foreground shadow-sm'
                      : 'border-border bg-background hover:border-secondary/50'
                  }`}
                >
                  {option}
                </button>
              );
            })}
          </div>

          <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setCurrentIndex((current) => Math.max(0, current - 1))}
                disabled={currentIndex === 0}
                className="inline-flex items-center gap-2 rounded-2xl border border-border bg-background px-4 py-3 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </button>
              {showSkip && currentIndex === 0 && (
                <button
                  type="button"
                  onClick={onSkip}
                  className="inline-flex items-center gap-2 rounded-2xl border border-border bg-background px-4 py-3 text-sm font-medium hover:bg-muted transition-colors"
                >
                  Skip for now
                </button>
              )}
            </div>

            <button
              type="button"
              onClick={() => {
                if (currentIndex === questions.length - 1) {
                  void submitAssessment();
                  return;
                }
                setCurrentIndex((current) => Math.min(questions.length - 1, current + 1));
              }}
              disabled={currentAnswer === -1 || saving}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-5 py-3.5 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {currentIndex === questions.length - 1 ? (saving ? 'Saving...' : 'Submit assessment') : 'Next'}
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {assessmentResult && (
        <div className="rounded-[28px] border border-secondary/20 bg-secondary/5 p-5 sm:p-6 shadow-sm">
          <div className="flex items-center gap-2 text-secondary">
            <CheckCircle2 className="h-5 w-5" />
            <span className="font-medium">Assessment saved</span>
          </div>
          <div className="mt-3 space-y-3 text-sm text-muted-foreground">
            <p>
              Your strongest learning mode is{' '}
              <span className="font-medium text-foreground capitalize">{currentStyle}</span>.
              Vakify will use this to adapt explanations and practice.
            </p>
            <p>
              Score: {assessmentResult.visual_score} visual, {assessmentResult.auditory_score} auditory, {assessmentResult.kinesthetic_score} kinesthetic.
            </p>
          </div>
          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={() => void onCompleted(assessmentResult)}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-primary px-5 py-3.5 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity"
            >
              {continueLabel}
              <Sparkles className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
