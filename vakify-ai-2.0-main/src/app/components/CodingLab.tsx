import { useEffect, useState } from 'react';
import {
  Play,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Code2,
  Terminal,
  RefreshCcw,
  Database,
  MessageSquareText,
  ChevronDown,
} from 'lucide-react';
import { apiFetch } from '../lib/api';

type LabTask = {
  task_id?: number | null;
  language: string;
  task_key: string;
  title: string;
  description: string;
  starter_code: string;
  sample_input: string;
  expected_output: string;
  hint: string;
  source_chat_id?: number | null;
  source_thread_id?: number | null;
  source_question?: string | null;
  source_answer?: string | null;
  validation_json?: string[];
  is_active?: boolean;
};

type RunResponse = {
  status: string;
  stdout: string;
  stderr: string;
  runner: string;
  note: string;
  challenge?: LabTask;
  task?: LabTask | null;
  tests: Array<{ name: string; passed: boolean }>;
  passed_tests: number;
  total_tests: number;
  score: number;
  submission_id?: number;
};

type ThreadSummary = {
  thread_id: number;
  title: string;
  preview?: string | null;
  message_count: number;
  last_message_at?: string | null;
};

type ThreadHistoryItem = {
  chat_id: number;
  question: string;
  response: string;
  timestamp: string;
};

type WorkspaceState = {
  workspace: {
    state_id?: number | null;
    workspace_type: string;
    language: string;
    task_id?: number | null;
    chat_id?: number | null;
    thread_id?: number | null;
    source_task_key?: string | null;
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

export function CodingLab() {
  const [selectedLanguage, setSelectedLanguage] = useState('python');
  const [task, setTask] = useState<LabTask | null>(null);
  const [code, setCode] = useState('');
  const [stdin, setStdin] = useState('');
  const [output, setOutput] = useState('');
  const [tests, setTests] = useState<Array<{ name: string; passed: boolean }>>([]);
  const [running, setRunning] = useState(false);
  const [loadingTask, setLoadingTask] = useState(false);
  const [syncingTask, setSyncingTask] = useState(false);
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [selectedThreadId, setSelectedThreadId] = useState<number | null>(null);
  const [threadMessages, setThreadMessages] = useState<ThreadHistoryItem[]>([]);
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null);
  const [workspaceReady, setWorkspaceReady] = useState(false);
  const selectedThread = threads.find((thread) => thread.thread_id === selectedThreadId) || null;
  const selectedChat = threadMessages.find((message) => message.chat_id === selectedChatId) || null;

  useEffect(() => {
    let cancelled = false;

    const loadTask = async () => {
      setLoadingTask(true);
      try {
        const data = await apiFetch<LabTask>(`/api/lab/task?language=${encodeURIComponent(selectedLanguage)}`);
        if (cancelled) return;
        setTask(data);
        setCode(data.starter_code || '');
        setStdin(data.sample_input || '');
        setOutput('');
        setTests([]);
        setWorkspaceReady(false);
      } catch {
        if (!cancelled) {
          setTask(null);
          setCode('');
          setStdin('');
          setOutput('Unable to load a coding task right now.');
          setTests([]);
          setWorkspaceReady(false);
        }
      } finally {
        if (!cancelled) setLoadingTask(false);
      }
    };

    const loadThreads = async () => {
      try {
        const data = await apiFetch<{ threads: ThreadSummary[]; active_thread_id?: number | null }>('/api/chat/threads');
        if (cancelled) return;
        setThreads(data.threads || []);
        setSelectedThreadId((current) => {
          if (!data.threads?.length) return null;
          if (current && data.threads.some((thread) => thread.thread_id === current)) {
            return current;
          }
          return data.active_thread_id ?? data.threads[0]?.thread_id ?? null;
        });
      } catch {
        if (!cancelled) {
          setThreads([]);
        }
      }
    };

    void loadTask();
    void loadThreads();
    return () => {
      cancelled = true;
    };
  }, [selectedLanguage]);

  useEffect(() => {
    const loadThreadMessages = async () => {
      if (!selectedThreadId) {
        setThreadMessages([]);
        setSelectedChatId(null);
        return;
      }
      try {
        const data = await apiFetch<{ messages: ThreadHistoryItem[] }>(`/api/chat/threads/${selectedThreadId}/history`);
        const rows = data.messages || [];
        setThreadMessages(rows);
        setSelectedChatId(rows[0]?.chat_id || null);
      } catch {
        setThreadMessages([]);
        setSelectedChatId(null);
      }
    };

    void loadThreadMessages();
  }, [selectedThreadId]);

  useEffect(() => {
    let cancelled = false;
    const loadWorkspace = async () => {
      setWorkspaceReady(false);
      try {
        const params = new URLSearchParams({
          workspace_type: 'chat',
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
        if (workspace.state_id != null) {
          setCode(workspace.code ?? '');
          setStdin(workspace.stdin ?? '');
          setOutput(workspace.last_output ?? '');
          setTests(workspace.last_tests_json || []);
        } else {
          setCode(task?.starter_code || '');
          setStdin(task?.sample_input || '');
          setOutput('');
          setTests([]);
        }
      } catch {
        if (!cancelled) {
          setCode(task?.starter_code || '');
          setStdin(task?.sample_input || '');
          setOutput('');
          setTests([]);
        }
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
  }, [selectedLanguage, task?.task_id, task?.starter_code, task?.sample_input]);

  useEffect(() => {
    if (!workspaceReady) {
      return;
    }

    const timer = window.setTimeout(() => {
      void apiFetch('/api/lab/workspace', {
        method: 'PUT',
        body: JSON.stringify({
          workspace_type: 'chat',
          language: selectedLanguage,
          task_id: task?.task_id ?? null,
          code,
          stdin,
          chat_id: task?.source_chat_id ?? null,
          thread_id: task?.source_thread_id ?? null,
          source_task_key: task?.task_key ?? null,
        }),
      }).catch(() => {
        // keep editing fluid even if the autosave request fails
      });
    }, 500);

    return () => window.clearTimeout(timer);
  }, [code, stdin, selectedLanguage, task?.task_id, task?.source_chat_id, task?.source_thread_id, task?.task_key, workspaceReady]);

  const syncSelectedChat = async () => {
    if (!selectedChatId) return;
    setSyncingTask(true);
    try {
      const data = await apiFetch<LabTask>('/api/lab/task/sync', {
        method: 'POST',
        body: JSON.stringify({ language: selectedLanguage, chat_id: selectedChatId }),
      });
      setTask(data);
      setCode(data.starter_code || '');
      setStdin(data.sample_input || '');
      setOutput('');
      setTests([]);
      setWorkspaceReady(false);
    } finally {
      setSyncingTask(false);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setOutput('Running code...\n');

    try {
      const response = await apiFetch<RunResponse>('/api/lab/run', {
        method: 'POST',
        body: JSON.stringify({
          language: selectedLanguage,
          source_code: code,
          stdin,
          task_id: task?.task_id,
          challenge_key: task?.task_key,
          title: task?.title,
        }),
      });

      setOutput(
        `${response.stdout || '(no stdout)'}\n${response.stderr ? `\n${response.stderr}` : ''}\n\nTests Passed: ${response.passed_tests}/${response.total_tests}\nScore: ${response.score}%\nRunner: ${response.runner}\n${response.note ? `\n${response.note}` : ''}`,
      );
      setTests(response.tests || []);
      if (response.task) {
        setTask(response.task);
      }
    } catch (error) {
      setOutput(error instanceof Error ? error.message : 'Unable to run code right now.');
      setTests([
        { name: 'Program compiled or executed', passed: false },
        { name: 'Task loaded from chat or database', passed: false },
        { name: 'Sample input wired correctly', passed: false },
        { name: 'Expected output check prepared', passed: false },
      ]);
    } finally {
      setRunning(false);
    }
  };

  const passedTests = tests.filter((t) => t.passed).length;
  const totalTests = tests.length;
  const passRate = totalTests > 0 ? (passedTests / totalTests) * 100 : 0;
  const plannedChecks = task?.validation_json?.length ?? 0;

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col p-6 max-w-7xl mx-auto gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl mb-2">Chat Sync Lab</h1>
          <p className="text-muted-foreground max-w-4xl">
            Practice coding with instant feedback, live input, and tasks you choose from your chat history.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void syncSelectedChat()}
            disabled={syncingTask || loadingTask || !selectedChatId}
            className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-4 py-3 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
          >
            <RefreshCcw className={`w-4 h-4 ${syncingTask ? 'animate-spin' : ''}`} />
            Sync selected message
          </button>
        </div>
      </div>

      <div className="rounded-3xl border border-border bg-card p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="text-sm text-muted-foreground flex items-center gap-2 uppercase tracking-[0.18em]">
              <MessageSquareText className="w-4 h-4" />
              Current Challenge
            </div>
            <div className="text-2xl font-semibold mt-2">{task?.title || 'Loading task...'}</div>
            <p className="mt-2 text-sm text-muted-foreground max-w-4xl leading-6">
              {task?.description || 'Start by selecting a chat message and syncing it into the lab.'}
            </p>
          </div>
          <div className="flex flex-col items-end gap-2 text-sm text-muted-foreground">
            <div className="rounded-full bg-secondary/10 px-3 py-1 text-secondary font-medium">
              Language: {selectedLanguage}
            </div>
            {task?.source_chat_id ? (
              <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1 text-primary">
                <Database className="w-4 h-4" />
                Synced from chat #{task.source_chat_id}
              </div>
            ) : (
              <div className="inline-flex items-center gap-2 rounded-full bg-muted px-3 py-1 text-muted-foreground">
                <Database className="w-4 h-4" />
                Default task
              </div>
            )}
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] gap-4">
          <div className="rounded-2xl border border-border bg-muted/20 p-4">
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Manual sync</div>
                <div className="text-sm text-muted-foreground mt-1">
                  Select a thread and a message. Nothing is pulled into the lab until you click sync.
                </div>
              </div>
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className="block">
                <span className="block text-xs uppercase tracking-[0.22em] text-muted-foreground mb-2">Chat thread</span>
                <select
                  value={selectedThreadId ?? ''}
                  onChange={(event) => setSelectedThreadId(event.target.value ? Number(event.target.value) : null)}
                  className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30"
                >
                  <option value="">Choose a thread</option>
                  {threads.map((thread) => (
                    <option key={thread.thread_id} value={thread.thread_id}>
                      {thread.title} ({thread.message_count} msgs)
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="block text-xs uppercase tracking-[0.22em] text-muted-foreground mb-2">Chat message</span>
                <select
                  value={selectedChatId ?? ''}
                  onChange={(event) => setSelectedChatId(event.target.value ? Number(event.target.value) : null)}
                  disabled={!threadMessages.length}
                  className="w-full rounded-xl border border-border bg-background px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-60"
                >
                  <option value="">{threadMessages.length ? 'Choose a message' : 'No messages in this thread'}</option>
                  {threadMessages.map((message) => (
                    <option key={message.chat_id} value={message.chat_id}>
                      #{message.chat_id} - {message.question.slice(0, 64)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 rounded-2xl border border-dashed border-border bg-background p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Selected message</div>
              <div className="mt-2 text-sm font-medium leading-6">
                {selectedChat?.question || 'Pick a thread and message to preview it here.'}
              </div>
              <div className="mt-3 rounded-xl bg-muted/40 p-3 text-sm text-muted-foreground leading-6 max-h-40 overflow-auto">
                {selectedChat ? summarizeSourceAnswer(selectedChat.response) : 'Your chosen chat response preview will appear here.'}
              </div>
              <div className="mt-3 text-xs text-muted-foreground">
                {selectedThread ? `Selected thread: ${selectedThread.title}` : 'No thread selected yet.'}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-background p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Task source</div>
                <div className="text-sm mt-1 text-muted-foreground">
                  {task?.source_question
                    ? 'This task was built from the synced chat message.'
                    : 'This task is the default challenge until you sync a message.'}
                </div>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              <div className="rounded-xl border border-border bg-muted/20 p-3">
                <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">What you asked</div>
                <div className="text-sm font-medium leading-6">
                  {task?.source_question || 'No chat synced yet.'}
                </div>
              </div>
              <div className="rounded-xl border border-border bg-muted/20 p-3">
                <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Task hint</div>
                <div className="text-sm text-muted-foreground leading-6">
                  {task?.hint || 'Sync a chat message to generate a tailored practice task.'}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <div className="rounded-full bg-accent/10 px-3 py-1 text-xs font-medium text-accent">
            Hint: {task?.hint || 'Use the lab input to test your solution.'}
          </div>
          <div className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            {task?.task_key || 'default-task'}
          </div>
          <div className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground">
            {task?.source_chat_id ? `Chat #${task.source_chat_id}` : 'No chat synced'}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {languages.map((lang) => (
          <button
            key={lang.id}
            onClick={() => setSelectedLanguage(lang.id)}
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
        <button
          onClick={() => void handleRun()}
          disabled={running || loadingTask}
          className="bg-secondary text-secondary-foreground px-6 py-3 rounded-xl hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
        >
          <Play className="w-5 h-5" />
          {running ? 'Running...' : 'Run Code'}
        </button>
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
              className="flex-1 min-h-[640px] p-5 font-mono text-sm leading-6 bg-primary/5 resize-none focus:outline-none"
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
              placeholder={task?.sample_input ? 'Edit the sample input or paste your own test data...' : 'Enter stdin for your program...'}
            />
          </div>
        </div>

        <div className="flex flex-col gap-4 min-h-0">
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
                {totalTests > 0 ? `${passedTests}/${totalTests} Passed` : `${plannedChecks} checks ready`}
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
                {totalTests > 0 ? `${passRate.toFixed(0)}% Tests Passing` : 'Run your solution to generate live checks.'}
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
                  Run your solution to see the live checks generated from the latest task.
                </div>
              )}
            </div>

            {passedTests < totalTests && totalTests > 0 && (
              <div className="mt-4 p-3 bg-accent/10 border border-accent/20 rounded-xl flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
                <div className="text-sm text-accent">
                  {task?.hint || 'Try using the sample input and adjust the code until the sample output matches.'}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function summarizeSourceAnswer(text: string) {
  const cleaned = text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
  if (!cleaned) return 'The chat response will be used to shape this task.';

  const sentences = cleaned.split(/(?<=[.!?])\s+/);
  const selected = sentences.slice(0, 3).join(' ');
  return selected.length > 360 ? `${selected.slice(0, 357).trim()}...` : selected;
}
