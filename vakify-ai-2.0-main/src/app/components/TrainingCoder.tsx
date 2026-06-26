import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import {
  Play,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Code2,
  Terminal,
  RotateCcw,
  CircleDashed,
  BookOpen,
} from 'lucide-react';
import { apiFetch } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

type RunResponse = {
  status: string;
  stdout: string;
  stderr: string;
  runner: string;
  note: string;
  tests: Array<{ name: string; passed: boolean }>;
  passed_tests: number;
  total_tests: number;
  score: number;
  submission_id?: number;
};

type DailyTaskPayload = {
  task_id: number;
  title: string;
  description: string;
  task_type: string;
  difficulty: string;
  status: string;
  points_reward: number;
  due_date: string;
  content: {
    mode?: string;
    language?: string;
    language_label?: string;
    task_key?: string;
    starter_code?: string;
    sample_input?: string;
    expected_output?: string;
    hint?: string;
    validation_json?: string[];
  };
};

type WorkspaceState = {
  workspace: {
    state_id?: number | null;
    workspace_type: string;
    language: string;
    task_id?: number | null;
    code: string;
    stdin: string;
    last_output: string;
    last_error: string;
    last_tests_json: Array<{ name: string; passed: boolean }>;
    last_score: number;
    last_status: string;
  };
};

const languages = [
  { id: 'python', name: 'Python' },
  { id: 'javascript', name: 'JavaScript' },
  { id: 'java', name: 'Java' },
  { id: 'cpp', name: 'C++' },
  { id: 'c', name: 'C' },
];

export function TrainingCoder() {
  const { refreshUser } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedLanguage, setSelectedLanguage] = useState('python');
  const [task, setTask] = useState<DailyTaskPayload | null>(null);
  const [loadingTask, setLoadingTask] = useState(false);
  const [code, setCode] = useState('');
  const [stdin, setStdin] = useState('');
  const [output, setOutput] = useState('');
  const [tests, setTests] = useState<Array<{ name: string; passed: boolean }>>([]);
  const [running, setRunning] = useState(false);
  const [workspaceReady, setWorkspaceReady] = useState(false);

  useEffect(() => {
    const taskId = searchParams.get('task_id');
    if (!taskId) {
      setTask(null);
      return;
    }

    let cancelled = false;
    const loadTask = async () => {
      setLoadingTask(true);
      try {
        const data = await apiFetch<DailyTaskPayload>(`/api/tasks/${taskId}`);
        if (cancelled) {
          return;
        }
        setTask(data);
        if (data.content?.language) {
          setSelectedLanguage(data.content.language);
        }
        setWorkspaceReady(false);
        setCode(data.content?.starter_code ?? '');
        setStdin(data.content?.sample_input ?? '');
        setOutput('');
        setTests([]);
      } catch {
        if (!cancelled) {
          setTask(null);
          setWorkspaceReady(false);
        }
      } finally {
        if (!cancelled) {
          setLoadingTask(false);
        }
      }
    };

    void loadTask();
    return () => {
      cancelled = true;
    };
  }, [searchParams]);

  useEffect(() => {
    let cancelled = false;
    const loadWorkspace = async () => {
      setWorkspaceReady(false);
      try {
        const params = new URLSearchParams({
          workspace_type: 'training',
          language: selectedLanguage,
        });
        if (task?.task_id) {
          params.set('task_id', String(task.task_id));
        }
        const data = await apiFetch<WorkspaceState>(`/api/lab/workspace?${params.toString()}`);
        if (cancelled) {
          return;
        }
        const workspace = data.workspace;
        if (workspace?.state_id != null) {
          setCode(workspace.code ?? '');
          setStdin(workspace.stdin ?? '');
          setOutput(workspace.last_output ?? '');
          setTests(workspace.last_tests_json || []);
        } else if (task) {
          setCode(task.content?.starter_code ?? '');
          setStdin(task.content?.sample_input ?? '');
          setOutput('');
          setTests([]);
        } else {
          setCode('');
          setStdin('');
          setOutput('');
          setTests([]);
        }
      } catch {
        // fall back to starter code / blank editor if the backend is unavailable
      } finally {
        if (!cancelled) {
          setWorkspaceReady(true);
        }
      }
    };

    void loadWorkspace();
    return () => {
      cancelled = true;
    };
  }, [selectedLanguage, task?.task_id]);

  useEffect(() => {
    if (!workspaceReady) {
      return;
    }

    const timer = window.setTimeout(() => {
      void apiFetch('/api/lab/workspace', {
        method: 'PUT',
        body: JSON.stringify({
          workspace_type: 'training',
          language: selectedLanguage,
          task_id: task?.task_id ?? null,
          code,
          stdin,
          source_task_key: task?.content?.task_key ?? null,
        }),
      }).catch(() => {
        // keep local editing responsive if the autosave request fails
      });
    }, 500);

    return () => window.clearTimeout(timer);
  }, [code, stdin, selectedLanguage, task?.task_id, task?.content?.task_key, workspaceReady]);

  const resetBlank = () => {
    setCode('');
    setStdin('');
    setOutput('');
    setTests([]);
    void apiFetch('/api/lab/workspace', {
      method: 'PUT',
      body: JSON.stringify({
        workspace_type: 'training',
        language: selectedLanguage,
        task_id: task?.task_id ?? null,
        code: '',
        stdin: '',
        source_task_key: task?.content?.task_key ?? null,
        last_output: '',
        last_error: '',
        last_tests_json: [],
        last_score: 0,
        last_status: 'draft',
      }),
    }).catch(() => {});
    if (task?.task_id) {
      setSearchParams({});
      setTask(null);
    }
  };

  const handleLanguageChange = (language: string) => {
    if (task) {
      setTask(null);
      setSearchParams({});
      setCode('');
      setStdin('');
      setOutput('');
      setTests([]);
    }
    setSelectedLanguage(language);
  };

  const handleRun = async () => {
    setRunning(true);
    setOutput(task ? `Running ${task.title}...\n` : 'Running code...\n');
    try {
      const response = await apiFetch<RunResponse>('/api/lab/run', {
        method: 'POST',
        body: JSON.stringify({
          language: selectedLanguage,
          source_code: code,
          stdin,
          task_id: task?.task_id ?? null,
          challenge_key: task?.content?.task_key ?? undefined,
          title: task?.title ?? undefined,
        }),
      });

      if (task?.task_id) {
        const submitResponse = await apiFetch<{ xp_awarded: number; passed: boolean; score: number }>(
          `/api/tasks/${task.task_id}/submit`,
          {
            method: 'POST',
            body: JSON.stringify({
              submission: code,
              score: response.score ?? 0,
            }),
          },
        );
        if (submitResponse.passed) {
          await refreshUser();
        }
      }

      setOutput(
        `${response.stdout || '(no stdout)'}\n${response.stderr ? `\n${response.stderr}` : ''}\n\nTests Passed: ${response.passed_tests}/${response.total_tests}\nScore: ${response.score}%\nRunner: ${response.runner}\n${response.note ? `\n${response.note}` : ''}`,
      );
      setTests(response.tests || []);
    } catch (error) {
      setOutput(error instanceof Error ? error.message : 'Unable to run code right now.');
      setTests([
        { name: 'Program compiled or executed', passed: false },
        { name: 'Blank editor is usable', passed: false },
        { name: 'Program input accepted', passed: false },
        { name: 'Output panel updated', passed: false },
      ]);
    } finally {
      setRunning(false);
    }
  };

  const passedTests = tests.filter((test) => test.passed).length;
  const totalTests = tests.length;
  const passRate = totalTests > 0 ? (passedTests / totalTests) * 100 : 0;

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col p-6 max-w-7xl mx-auto gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl mb-2">{task ? 'Challenge Runner' : 'Training Coder'}</h1>
          <p className="text-muted-foreground max-w-4xl">
            {task
              ? 'A loaded task from your daily queue. Edit the code, run it, and earn points when it passes.'
              : 'A clean editor for practice, experiments, and freeform coding. Nothing is auto-filled.'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {task ? (
            <div className="rounded-xl border border-secondary/20 bg-secondary/10 px-4 py-3 text-sm text-secondary inline-flex items-center gap-2">
              <BookOpen className="w-4 h-4" />
              {loadingTask ? 'Loading task...' : task.title}
            </div>
          ) : null}
          <button
            onClick={resetBlank}
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-3 text-sm font-medium hover:bg-muted transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            {task ? 'Clear Task' : 'Reset Blank'}
          </button>
        </div>
      </div>

      {task ? (
        <div className="rounded-3xl border border-border bg-card p-6 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-sm uppercase tracking-[0.3em] text-muted-foreground">Loaded task</div>
              <h2 className="text-2xl mt-2">{task.title}</h2>
              <p className="text-muted-foreground mt-3 max-w-4xl">{task.description}</p>
            </div>
            <div className="text-right">
              <div className="rounded-full bg-secondary/10 text-secondary px-3 py-1 text-sm inline-flex">
                +{task.points_reward} XP
              </div>
              <div className="text-sm text-muted-foreground mt-3">
                {task.content?.language_label || selectedLanguage}
              </div>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
            <div className="rounded-2xl bg-muted/40 border border-border p-4">
              <div className="text-muted-foreground mb-1">Mode</div>
              <div className="font-medium capitalize">{task.task_type}</div>
            </div>
            <div className="rounded-2xl bg-muted/40 border border-border p-4">
              <div className="text-muted-foreground mb-1">Sample Input</div>
              <div className="font-mono whitespace-pre-wrap">{task.content?.sample_input || 'No sample input'}</div>
            </div>
            <div className="rounded-2xl bg-muted/40 border border-border p-4">
              <div className="text-muted-foreground mb-1">Hint</div>
              <div>{task.content?.hint || 'No hint provided'}</div>
            </div>
          </div>
        </div>
      ) : null}

      <div className="rounded-3xl border border-border bg-card p-6 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          {languages.map((lang) => (
            <button
              key={lang.id}
              onClick={() => handleLanguageChange(lang.id)}
              className={`px-4 py-2 rounded-xl transition-colors ${
                selectedLanguage === lang.id
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-card border border-border hover:bg-muted'
              }`}
            >
              {lang.name}
            </button>
          ))}
          <div className="flex-1" />
          <div className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground inline-flex items-center gap-2">
            <CircleDashed className="w-4 h-4" />
            {task ? 'Task workspace' : 'Blank workspace'}
          </div>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,0.85fr)] gap-4 min-h-0">
        <div className="flex flex-col gap-4 min-h-0">
          <div className="flex flex-col bg-card border border-border rounded-2xl overflow-hidden min-h-0 shadow-sm">
            <div className="flex items-center justify-between p-4 border-b border-border bg-muted/30">
              <div className="flex items-center gap-2">
                <Code2 className="w-5 h-5 text-primary" />
                <h3>Code Editor</h3>
              </div>
              <span className="text-sm text-muted-foreground">{selectedLanguage}</span>
            </div>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="flex-1 min-h-[680px] p-5 font-mono text-sm leading-6 bg-primary/5 resize-none focus:outline-none"
              placeholder={task ? task.content?.starter_code || '// Start from the loaded task...' : '// Start from scratch...'}
              spellCheck={false}
            />
          </div>

          <div className="flex flex-col bg-card border border-border rounded-2xl overflow-hidden shadow-sm">
            <div className="flex items-center justify-between p-4 border-b border-border bg-muted/30">
              <div className="flex items-center gap-2">
                <Terminal className="w-5 h-5 text-secondary" />
                <h3>Program Input</h3>
              </div>
              <span className="text-sm text-muted-foreground">stdin</span>
            </div>
            <textarea
              value={stdin}
              onChange={(e) => setStdin(e.target.value)}
              className="min-h-[180px] p-5 font-mono text-sm leading-6 bg-muted/20 resize-none focus:outline-none"
              placeholder="Enter input for your code..."
            />
          </div>
        </div>

        <div className="flex flex-col gap-4 min-h-0">
          <button
            onClick={() => void handleRun()}
            disabled={running}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-secondary px-6 py-3 text-secondary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            <Play className="w-5 h-5" />
            {running ? 'Running...' : 'Run Code'}
          </button>

          <div className="flex-1 bg-card border border-border rounded-2xl overflow-hidden flex flex-col shadow-sm min-h-[320px]">
            <div className="flex items-center gap-2 p-4 border-b border-border bg-muted/30">
              <Terminal className="w-5 h-5 text-secondary" />
              <h3>Output</h3>
            </div>
            <div className="flex-1 p-4 font-mono text-sm bg-muted/20 overflow-auto whitespace-pre-wrap min-h-[280px]">
              {output || 'Click "Run Code" to see output...'}
            </div>
          </div>

          <div className="bg-card border border-border rounded-2xl p-4 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-secondary" />
                Test Results
              </h3>
              <span className="text-sm text-muted-foreground">
                {totalTests > 0 ? `${passedTests}/${totalTests} Passed` : '0 checks ready'}
              </span>
            </div>

            <div className="mb-4">
              <div className="bg-muted rounded-full h-2 mb-2">
                <div
                  className="bg-secondary h-full rounded-full transition-all"
                  style={{ width: `${passRate}%` }}
                />
              </div>
              <div className="text-xs text-muted-foreground">
                {totalTests > 0 ? `${passRate.toFixed(0)}% Tests Passing` : 'Run your code to generate feedback.'}
              </div>
            </div>

            <div className="space-y-2">
              {tests.length ? (
                tests.map((test, index) => (
                  <div
                    key={index}
                    className={`flex items-center gap-3 p-3 rounded-xl ${
                      test.passed ? 'bg-secondary/10' : 'bg-destructive/10'
                    }`}
                  >
                    {test.passed ? (
                      <CheckCircle2 className="w-4 h-4 text-secondary flex-shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-destructive flex-shrink-0" />
                    )}
                    <span className="text-sm">{test.name}</span>
                  </div>
                ))
              ) : (
                <div className="rounded-xl border border-dashed border-border bg-muted/20 px-4 py-5 text-sm text-muted-foreground">
                  {task
                    ? 'Run the loaded task to check your solution and award points when it passes.'
                    : 'A clean blank editor for practice, experiments, and freeform coding. Nothing is auto-filled.'}
                </div>
              )}
            </div>

            {passedTests < totalTests && totalTests > 0 && (
              <div className="mt-4 p-3 bg-accent/10 border border-accent/20 rounded-xl flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
                <div className="text-sm text-accent">
                  Try editing the code and rerun to see how the result changes.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
