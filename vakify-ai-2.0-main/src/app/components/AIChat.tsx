import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Send,
  Sparkles,
  Copy,
  RotateCcw,
  ThumbsUp,
  ThumbsDown,
  Plus,
  PanelLeftOpen,
  Clock3,
  Trash2,
  PenLine,
  ImagePlus,
  Volume2,
  X,
} from 'lucide-react';
import { apiFetch, apiFetchBlob } from '../lib/api';

type ConfidenceLevel = 'High' | 'Medium' | 'Low';

type ChatPayload = {
  title?: string;
  summary?: string;
  answer?: string;
  text?: string;
  key_points?: string[];
  example?: string;
  code_sample?: string;
  practice?: string;
  quiz_question?: string;
  quiz_options?: string[];
  follow_up_prompts?: string[];
  next_step?: string;
  response_type?: string;
  confidence?: ConfidenceLevel;
  mode?: string;
  style?: string;
  chat_id?: number;
  thread_id?: number;
  thread_title?: string;
  image_url?: string;
  image_prompt?: string;
  attached_to_text?: boolean;
  audio_download_id?: number;
  audio_download_url?: string;
};

type ThreadSummary = {
  thread_id: number;
  title: string;
  preview?: string | null;
  message_count: number;
  is_archived?: boolean;
  last_message_at?: string | null;
};

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  confidence?: ConfidenceLevel;
  timestamp: Date;
  chatId?: number;
  followUps?: string[];
  structured?: ChatPayload;
}

export function AIChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<number | null>(null);
  const [generatingImage, setGeneratingImage] = useState(false);
  const [assetAction, setAssetAction] = useState<{ chatId: number; kind: 'image' | 'audio' } | null>(null);
  const [audioUrls, setAudioUrls] = useState<Record<number, string>>({});
  const audioUrlsRef = useRef<Record<number, string>>({});

  useEffect(() => {
    let cancelled = false;

    const loadThreads = async () => {
      try {
        const data = await apiFetch<{ threads: ThreadSummary[]; active_thread_id?: number | null }>('/api/chat/threads');

        if (cancelled) {
          return;
        }

        setThreads(data.threads || []);
        const preferredThreadId = data.active_thread_id || data.threads?.[0]?.thread_id || null;
        if (preferredThreadId) {
          await loadThreadHistory(preferredThreadId, false);
          setActiveThreadId(preferredThreadId);
        } else {
          setMessages([]);
          setActiveThreadId(null);
        }
      } catch {
        if (!cancelled) {
          setThreads([]);
          setActiveThreadId(null);
          setMessages([]);
        }
      }
    };

    void loadThreads();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loading = new Set<number>();

    const hydrateAudio = async () => {
      const targets = messages.filter((message) => message.role === 'assistant' && message.chatId && message.structured?.audio_download_url);
      for (const message of targets) {
        const chatId = message.chatId as number;
        if (audioUrlsRef.current[chatId] || loading.has(chatId)) {
          continue;
        }
        loading.add(chatId);
        try {
          const blob = await apiFetchBlob(message.structured?.audio_download_url || '');
          if (cancelled) {
            continue;
          }
          const objectUrl = window.URL.createObjectURL(blob);
          audioUrlsRef.current[chatId] = objectUrl;
          setAudioUrls((prev) => ({
            ...prev,
            [chatId]: objectUrl,
          }));
        } catch {
          if (!cancelled) {
            // ignore and keep the audio action available for retry
          }
        }
      }
    };

    void hydrateAudio();

    return () => {
      cancelled = true;
    };
  }, [messages]);

  useEffect(() => {
    return () => {
      Object.values(audioUrlsRef.current).forEach((url) => window.URL.revokeObjectURL(url));
      audioUrlsRef.current = {};
    };
  }, []);

  const latestAssistant = useMemo(
    () => [...messages].reverse().find((message) => message.role === 'assistant') || null,
    [messages],
  );
  const activeThread = useMemo(
    () => threads.find((thread) => thread.thread_id === activeThreadId) || null,
    [activeThreadId, threads],
  );
  const hasConversation = useMemo(() => messages.some((message) => message.id !== 'starter'), [messages]);

  const suggestionChips = latestAssistant?.followUps?.length ? latestAssistant.followUps : [];

  const loadThreadHistory = async (threadId: number, focusThread = true) => {
    const data = await apiFetch<{
      thread: ThreadSummary;
      messages: Array<{
        chat_id: number;
        question: string;
        response: string;
        response_json?: ChatPayload | null;
        response_type: string;
        timestamp: string;
        feedback?: { rating: number; comment?: string | null } | null;
      }>;
    }>(`/api/chat/threads/${threadId}/history`);

    const rows = data.messages || [];
    const restored = buildMessagesFromRows(rows);
    setMessages(restored);
    setThreads((prev) =>
      prev.map((thread) =>
        thread.thread_id === threadId
          ? {
              ...thread,
              ...data.thread,
            }
          : thread,
      ),
    );
    if (focusThread) {
      setActiveThreadId(threadId);
    }
  };

  const startNewChat = async () => {
    const thread = await apiFetch<ThreadSummary>('/api/chat/threads', {
      method: 'POST',
      body: JSON.stringify({ title: 'New Chat' }),
    });
    setThreads((prev) => [thread, ...prev.filter((item) => item.thread_id !== thread.thread_id)]);
    setActiveThreadId(thread.thread_id);
    setMessages([]);
    setInput('');
    setCopiedId(null);
  };

  const selectThread = async (threadId: number) => {
    if (threadId === activeThreadId) return;
    setActiveThreadId(threadId);
    await loadThreadHistory(threadId, true);
  };

  const deleteThread = async (threadId: number, keepBlankAfterDelete = false) => {
    const response = await apiFetch<{ message: string; thread_id: number; threads: ThreadSummary[]; active_thread_id?: number | null }>(
      `/api/chat/threads/${threadId}`,
      { method: 'DELETE' },
    );
    setThreads(response.threads || []);
    if (keepBlankAfterDelete || !response.active_thread_id) {
      setMessages([]);
      setActiveThreadId(null);
      setInput('');
      return;
    }
    await loadThreadHistory(response.active_thread_id, true);
  };

  const handleSend = async (value?: string) => {
    const text = (value ?? input).trim();
    if (!text || sending) return;

    const userMessage: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setSending(true);

    try {
      let threadId = activeThreadId;
      if (!threadId) {
        const createdThread = await apiFetch<ThreadSummary>('/api/chat/threads', {
          method: 'POST',
          body: JSON.stringify({ title: text.slice(0, 80) || 'New Chat' }),
        });
        threadId = createdThread.thread_id;
        setThreads((prev) => [createdThread, ...prev.filter((item) => item.thread_id !== createdThread.thread_id)]);
        setActiveThreadId(threadId);
      }

      const response = await apiFetch<ChatPayload>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({ question: text, thread_id: threadId }),
      });

      const assistantMessage: Message = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: response.answer || response.text || 'I could not generate a response right now.',
        confidence: response.confidence || 'High',
        timestamp: new Date(),
        followUps: response.follow_up_prompts?.slice(0, 4) || [],
        chatId: response.chat_id,
        structured: response,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      if (response.thread_id && response.thread_id !== threadId) {
        setActiveThreadId(response.thread_id);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          content: error instanceof Error ? error.message : 'Sorry, the assistant is temporarily unavailable.',
          confidence: 'Low',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleGenerateImage = async () => {
    const prompt = input.trim();
    if (!prompt || sending || generatingImage) return;

    const userMessage: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setGeneratingImage(true);

    try {
      let threadId = activeThreadId;
      if (!threadId) {
        const createdThread = await apiFetch<ThreadSummary>('/api/chat/threads', {
          method: 'POST',
          body: JSON.stringify({ title: prompt.slice(0, 80) || 'New Chat' }),
        });
        threadId = createdThread.thread_id;
        setThreads((prev) => [createdThread, ...prev.filter((item) => item.thread_id !== createdThread.thread_id)]);
        setActiveThreadId(threadId);
      }

      const response = await apiFetch<ChatPayload>('/api/chat/image', {
        method: 'POST',
        body: JSON.stringify({ prompt, thread_id: threadId }),
      });

      const assistantMessage: Message = {
        id: `img-${Date.now()}`,
        role: 'assistant',
        content: response.summary || response.image_prompt || response.answer || 'Image generated successfully.',
        confidence: response.confidence || 'High',
        timestamp: new Date(),
        chatId: response.chat_id,
        followUps: response.follow_up_prompts?.slice(0, 4) || [],
        structured: response,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      if (response.thread_id && response.thread_id !== threadId) {
        setActiveThreadId(response.thread_id);
      }
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: `img-${Date.now()}`,
          role: 'assistant',
          content: error instanceof Error ? error.message : 'Sorry, the image generator is temporarily unavailable.',
          confidence: 'Low',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setGeneratingImage(false);
    }
  };

  const mergeStructuredMessage = (chatId: number, next: ChatPayload) => {
    const shouldReplaceContent = next.response_type !== 'visual' && next.mode !== 'image';
    setMessages((prev) =>
      prev.map((message) => {
        if (message.chatId !== chatId || message.role !== 'assistant') {
          return message;
        }
        const mergedStructured = {
          ...(message.structured || {}),
          ...next,
        };
        return {
          ...message,
          content: shouldReplaceContent ? (next.answer || next.text || message.content) : message.content,
          confidence: next.confidence || message.confidence,
          followUps: next.follow_up_prompts?.slice(0, 4) || message.followUps,
          structured: mergedStructured,
        };
      }),
    );
  };

  const generateAssistantAudio = async (message: Message) => {
    if (!message.chatId || assetAction) return;
    setAssetAction({ chatId: message.chatId, kind: 'audio' });
    try {
      const response = await apiFetch<ChatPayload>('/api/chat/audio', {
        method: 'POST',
        body: JSON.stringify({ chat_id: message.chatId }),
      });
      mergeStructuredMessage(message.chatId, response);
      if (response.audio_download_url) {
        try {
          const blob = await apiFetchBlob(response.audio_download_url);
          const objectUrl = window.URL.createObjectURL(blob);
          audioUrlsRef.current[message.chatId as number] = objectUrl;
          setAudioUrls((prev) => ({
            ...prev,
            [message.chatId as number]: objectUrl,
          }));
        } catch {
          // keep the audio card visible even if inline playback fails
        }
      }
    } finally {
      setAssetAction(null);
    }
  };

  const generateAssistantImage = async (message: Message) => {
    if (!message.chatId || assetAction) return;
    setAssetAction({ chatId: message.chatId, kind: 'image' });
    try {
      const response = await apiFetch<ChatPayload>('/api/chat/image', {
        method: 'POST',
        body: JSON.stringify({ chat_id: message.chatId, thread_id: activeThreadId }),
      });
      mergeStructuredMessage(message.chatId, response);
    } finally {
      setAssetAction(null);
    }
  };

  const copyMessage = async (message: Message) => {
    await navigator.clipboard.writeText(buildClipboardText(message));
    setCopiedId(message.id);
    window.setTimeout(() => setCopiedId(null), 1200);
  };

  const feedback = async (message: Message, rating: 1 | -1) => {
    if (!message.chatId) return;
    await apiFetch('/api/chat/feedback', {
      method: 'POST',
      body: JSON.stringify({
        chat_id: message.chatId,
        rating,
      }),
    });
  };

  function buildMessagesFromRows(rows: Array<{
    chat_id: number;
    question: string;
    response: string;
    response_json?: ChatPayload | null;
    response_type: string;
    timestamp: string;
  }>): Message[] {
    const chronological = [...rows].reverse();
    const restored: Message[] = [];
    chronological.forEach((row) => {
      restored.push({
        id: `q-${row.chat_id}`,
        role: 'user',
        content: row.question,
        timestamp: new Date(row.timestamp),
        chatId: row.chat_id,
      });
      const parsed = row.response_json || safeParseChatPayload(row.response);
      restored.push({
        id: `a-${row.chat_id}`,
        role: 'assistant',
        content: parsed?.answer || parsed?.text || row.response || 'Assistant response',
        confidence: parsed?.confidence || confidenceFromResponseType(row.response_type),
        timestamp: new Date(row.timestamp),
        chatId: row.chat_id,
        followUps: parsed?.follow_up_prompts?.slice(0, 4) || [],
        structured: parsed || undefined,
      });
    });
    return restored;
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] max-w-[1700px] mx-auto gap-4 px-4 py-4">
      <aside className="hidden lg:flex w-[330px] shrink-0 rounded-3xl border border-border/70 bg-gradient-to-b from-card to-muted/30 shadow-[0_12px_40px_-22px_rgba(15,23,42,0.45)] overflow-hidden">
        <div className="flex h-full w-full flex-col">
          <div className="px-5 pt-5 pb-4 border-b border-border/60 bg-background/50 backdrop-blur">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold text-muted-foreground">Quick Start</div>
                <div className="text-xs text-muted-foreground mt-1">Your saved conversations</div>
              </div>
              <button
                onClick={() => void startNewChat()}
                className="inline-flex items-center gap-2 rounded-full bg-primary px-3 py-2 text-xs font-medium text-primary-foreground shadow-sm hover:opacity-90 transition-opacity"
              >
                <Plus className="w-3.5 h-3.5" />
                New Chat
              </button>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                onClick={() => void startNewChat()}
                className="flex items-center justify-center gap-2 rounded-2xl border border-border bg-background px-3 py-3 text-sm font-medium hover:bg-muted transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
              <button
                onClick={() => {
                  if (activeThreadId) {
                    void selectThread(activeThreadId);
                  }
                }}
                className="flex items-center justify-center gap-2 rounded-2xl border border-border bg-background px-3 py-3 text-sm font-medium hover:bg-muted transition-colors"
              >
                <Clock3 className="w-4 h-4" />
                Resume
              </button>
            </div>
          </div>

          {suggestionChips.length ? (
            <div className="px-5 py-4 border-b border-border/60">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-muted-foreground">Suggested prompts</h3>
                <PanelLeftOpen className="w-4 h-4 text-muted-foreground" />
              </div>
              <div className="space-y-2">
                {suggestionChips.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => setInput(prompt)}
                    className="w-full text-left rounded-2xl border border-transparent bg-background/70 px-4 py-3 text-sm hover:border-border hover:bg-background transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="flex-1 px-5 py-4 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-muted-foreground">Recent chats</h3>
              <span className="text-xs text-muted-foreground">{threads.length} threads</span>
            </div>
            <div className="space-y-2 overflow-y-auto pr-1">
              {threads.length ? (
                threads.map((thread) => {
                  const isActive = activeThreadId === thread.thread_id;
                  return (
                    <div
                      key={thread.thread_id}
                      className={`rounded-2xl border px-4 py-3 transition-all ${
                        isActive
                          ? 'border-primary bg-primary text-primary-foreground shadow-md shadow-primary/10'
                          : 'border-border bg-background hover:border-secondary/50 hover:shadow-sm'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => void selectThread(thread.thread_id)}
                        className="w-full text-left"
                        aria-label={`Open ${thread.title}`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="text-sm font-semibold truncate">{thread.title}</div>
                            <div className={`mt-1 text-xs ${isActive ? 'text-primary-foreground/75' : 'text-muted-foreground'}`}>
                              {thread.preview || `${thread.message_count} saved message${thread.message_count === 1 ? '' : 's'}`}
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <div className={`rounded-full px-2.5 py-1 text-[11px] font-medium ${isActive ? 'bg-white/15' : 'bg-muted text-muted-foreground'}`}>
                              {thread.message_count}
                            </div>
                          </div>
                        </div>
                      </button>
                      <div className="mt-3 flex justify-end">
                        <button
                          type="button"
                          onClick={() => void deleteThread(thread.thread_id, isActive)}
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-medium transition-colors ${
                            isActive
                              ? 'bg-white/15 text-primary-foreground hover:bg-white/25'
                              : 'bg-muted text-muted-foreground hover:bg-destructive/10 hover:text-destructive'
                          }`}
                          title="Delete chat"
                        >
                          <X className="w-3 h-3" />
                          Delete
                        </button>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="rounded-2xl border border-dashed border-border bg-background/60 p-4 text-sm text-muted-foreground">
                  No saved chats yet. Start a new thread to save history.
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col rounded-3xl border border-border/70 bg-background shadow-[0_18px_60px_-28px_rgba(15,23,42,0.38)] overflow-hidden">
        <div className="border-b border-border/70 bg-gradient-to-r from-card to-muted/30 backdrop-blur px-5 py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-11 h-11 rounded-2xl bg-secondary/10 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-secondary" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold truncate">{activeThread?.title || 'AI Chat'}</h2>
                <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-700">
                  Live
                </span>
              </div>
              <p className="text-xs text-muted-foreground truncate">
                {hasConversation
                  ? 'Your conversation is saved and can continue later.'
                  : 'A clean workspace for natural, context-aware conversations.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => void startNewChat()}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-3.5 py-2 text-sm font-medium hover:bg-muted transition-colors"
            >
              <PenLine className="w-4 h-4" />
              New
            </button>
            <button
              onClick={() => {
                if (!activeThreadId) {
                  void startNewChat();
                  return;
                }
                void deleteThread(activeThreadId, true);
              }}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-background px-3.5 py-2 text-sm font-medium hover:bg-muted transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Clear
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 md:p-6 bg-[radial-gradient(circle_at_top_right,rgba(94,234,212,0.08),transparent_32%),linear-gradient(180deg,rgba(255,255,255,0.4),rgba(248,250,252,0.92))]">
          {!hasConversation ? (
            <div className="max-w-4xl mx-auto mb-6">
              <div className="rounded-[28px] border border-border/70 bg-card/90 p-6 md:p-8 shadow-sm">
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-secondary/10 flex items-center justify-center shrink-0">
                    <Sparkles className="w-6 h-6 text-secondary" />
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-2xl font-semibold tracking-tight">Ask anything, naturally.</h3>
                    <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
                      This chat keeps context, saves conversations as threads, and formats long answers so they read cleanly.
                    </p>
                  </div>
                </div>
                <div className="mt-5 rounded-2xl border border-dashed border-border bg-background/80 px-4 py-4 text-sm text-muted-foreground">
                  Start typing below to begin a new conversation.
                </div>
              </div>
            </div>
          ) : null}

          <div className="space-y-5">
          {messages.map((message) => (
            <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {message.role === 'assistant' ? (
                <div className="max-w-4xl w-full">
                  <div className="rounded-[28px] border border-border/70 bg-card/95 p-5 md:p-6 shadow-[0_12px_40px_-26px_rgba(15,23,42,0.45)]">
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-10 h-10 rounded-2xl bg-secondary/10 flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-secondary" />
                      </div>
                      <div>
                        <div className="text-sm font-semibold">AI Assistant</div>
                        <div className="text-xs text-muted-foreground">Natural conversation mode</div>
                      </div>
                    </div>

                    {renderStructuredAssistant(message, (prompt) => void handleSend(prompt), message.chatId ? audioUrls[message.chatId] : null)}

                    <div className="flex items-center gap-3 pt-4 mt-5 border-t border-border/70 flex-wrap">
                      <button
                        onClick={() => void copyMessage(message)}
                        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <Copy className="w-4 h-4" />
                        {copiedId === message.id ? 'Copied' : 'Copy'}
                      </button>
                      <button
                        onClick={() => void generateAssistantAudio(message)}
                        disabled={assetAction?.chatId === message.chatId}
                        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                      >
                        <Volume2 className="w-4 h-4" />
                        {assetAction?.chatId === message.chatId && assetAction.kind === 'audio' ? 'Creating audio...' : 'Audio'}
                      </button>
                      <button
                        onClick={() => void generateAssistantImage(message)}
                        disabled={assetAction?.chatId === message.chatId}
                        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
                      >
                        <ImagePlus className="w-4 h-4" />
                        {assetAction?.chatId === message.chatId && assetAction.kind === 'image' ? 'Creating image...' : 'Image'}
                      </button>
                      <button
                        onClick={() => void feedback(message, 1)}
                        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <ThumbsUp className="w-4 h-4" />
                        Helpful
                      </button>
                      <button
                        onClick={() => void feedback(message, -1)}
                        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        <ThumbsDown className="w-4 h-4" />
                        Not helpful
                      </button>
                      <div className="flex-1"></div>
                      <span className="text-xs text-muted-foreground">Confidence: {message.confidence || 'High'}</span>
                    </div>

                    {message.followUps?.length ? (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {message.followUps.map((prompt) => (
                          <button
                            key={prompt}
                            onClick={() => void handleSend(prompt)}
                            className="px-3 py-2 rounded-full text-xs border border-border bg-background hover:bg-muted transition-colors"
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : (
                <div className="max-w-[44rem] rounded-[24px] bg-primary text-primary-foreground px-5 py-4 shadow-sm">
                  <div className="text-xs uppercase tracking-[0.2em] text-primary-foreground/70 mb-2">You</div>
                  <div className="whitespace-pre-wrap text-[15px] leading-7">{message.content}</div>
                </div>
              )}
            </div>
          ))}
          </div>
        </div>

        <div className="border-t border-border/70 bg-card/95 backdrop-blur p-4 md:p-5">
          <div className="mx-auto max-w-4xl">
            <div className="text-xs text-muted-foreground mb-2">
              Ask naturally. The assistant keeps the conversation context.
            </div>
            <div className="flex flex-wrap items-end gap-3 rounded-[28px] border border-border/70 bg-background p-3 shadow-[0_8px_30px_-22px_rgba(15,23,42,0.35)]">
              <button
                onClick={() => void handleGenerateImage()}
                disabled={!input.trim() || sending || generatingImage}
                className="inline-flex items-center gap-2 rounded-2xl border border-border bg-background px-4 py-4 text-sm font-medium hover:bg-muted transition-colors disabled:opacity-50"
                title="Generate an image from the prompt"
              >
                <ImagePlus className="w-4 h-4" />
                {generatingImage ? 'Creating...' : 'Image'}
              </button>
              <div className="flex-1 min-w-[14rem]">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      void handleSend();
                    }
                  }}
                  className="min-h-[56px] w-full resize-none bg-transparent px-2 py-2 text-[15px] leading-6 focus:outline-none"
                  placeholder="Ask anything..."
                  rows={1}
                />
              </div>
              <button
                onClick={() => void handleSend()}
                disabled={!input.trim() || sending}
                className="inline-flex min-w-[112px] items-center justify-center gap-2 rounded-2xl bg-primary px-5 py-4 text-sm font-medium text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                {sending ? 'Thinking...' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function buildClipboardText(message: Message) {
  const structured = message.structured;
  if (!structured) {
    return message.content;
  }

  const lines: string[] = [];
  if (structured.title) lines.push(structured.title, '');
  if (structured.summary) lines.push(`Summary: ${structured.summary}`, '');
  if (structured.answer) lines.push(`Answer:\n${structured.answer}`, '');
  if (structured.key_points?.length) {
    lines.push('Key points:');
    structured.key_points.forEach((point, index) => lines.push(`${index + 1}. ${point}`));
    lines.push('');
  }
  if (structured.example) lines.push(`Example:\n${structured.example}`, '');
  if (structured.code_sample) lines.push(`Code sample:\n${structured.code_sample}`, '');
  if (structured.practice) lines.push(`Practice:\n${structured.practice}`, '');
  if (structured.quiz_question) lines.push(`Quick check:\n${structured.quiz_question}`, '');
  if (structured.next_step) lines.push(`Next step:\n${structured.next_step}`, '');
  if (structured.image_prompt) lines.push(`Image prompt:\n${structured.image_prompt}`, '');
  if (structured.image_url) lines.push(`Image URL:\n${structured.image_url}`, '');
  if (structured.audio_download_url) lines.push(`Audio URL:\n${structured.audio_download_url}`, '');
  if (structured.follow_up_prompts?.length) {
    lines.push('Follow-up prompts:');
    structured.follow_up_prompts.forEach((prompt, index) => lines.push(`${index + 1}. ${prompt}`));
  }
  return lines.join('\n').trim();
}

function renderStructuredAssistant(message: Message, onFollowUpPrompt: (prompt: string) => void, audioSrc?: string | null) {
  const structured = message.structured;
  if (!structured) {
    return <div className="space-y-4 text-sm leading-7 text-foreground/95">{renderRichContent(message.content)}</div>;
  }

  const keyPoints = toStringArray(structured.key_points);
  const followUps = toStringArray(structured.follow_up_prompts);
  const quizOptions = toStringArray(structured.quiz_options);
  const hasExample = Boolean(asString(structured.example).trim());
  const hasCode = Boolean(asString(structured.code_sample).trim());
  const hasPractice = Boolean(asString(structured.practice).trim());
  const hasQuiz = Boolean(asString(structured.quiz_question).trim() || quizOptions.length);
  const hasNextStep = Boolean(asString(structured.next_step).trim());
  const hasImagePrompt = Boolean(asString(structured.image_prompt).trim());
  const hasImage = Boolean(asString(structured.image_url).trim());
  const isAttachedImage = Boolean(structured.attached_to_text);
  const titleText = asString(structured.title).trim() || 'Structured response';
  const summaryText = asString(structured.summary).trim() || 'A concise overview with answer, examples, and next steps.';
  const imageUrl = asString(structured.image_url).trim();
  const imagePrompt = asString(structured.image_prompt).trim();
  const quizQuestion = asString(structured.quiz_question).trim() || 'Quick check';
  const codeSample = asString(structured.code_sample);

  return (
    <div className="space-y-5 text-sm leading-7 text-foreground/95">
      <div className="rounded-3xl border border-border/70 bg-gradient-to-r from-secondary/10 via-card to-background px-4 py-4 md:px-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Assistant Response</div>
            <div className="mt-1 text-lg font-semibold leading-tight text-foreground">
              {titleText}
            </div>
            <div className="mt-2 text-sm text-muted-foreground">
              {summaryText}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 text-xs">
            <span className="rounded-full bg-emerald-500/10 px-3 py-1 font-medium text-emerald-700">
              Confidence: {message.confidence || structured.confidence || 'High'}
            </span>
          </div>
        </div>
      </div>

      <div className="rounded-3xl border border-border/70 bg-card px-4 py-4 md:px-5">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Main Answer</div>
            <div className="text-sm text-muted-foreground">A natural explanation, written clearly and directly.</div>
          </div>
        </div>
        <div className="space-y-4">
          {renderRichContent(isAttachedImage ? message.content : (structured.answer || message.content))}
        </div>
      </div>

          {hasImage ? (
        <div className="rounded-3xl border border-border/70 bg-card px-4 py-4 md:px-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Image Result</div>
              <div className="text-sm text-muted-foreground">{summaryText || 'Generated visual response.'}</div>
            </div>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-medium text-primary">
              Visual
            </span>
          </div>
          <div className="mt-4 overflow-hidden rounded-3xl border border-border/70 bg-muted/20">
            <img
              src={imageUrl}
              alt={imagePrompt || titleText || 'Generated visual'}
              className="h-auto w-full max-h-[28rem] object-cover"
            />
          </div>
          {isAttachedImage ? (
            <div className="mt-4 rounded-2xl border border-dashed border-emerald-500/30 bg-emerald-500/5 px-4 py-3 text-sm text-emerald-900">
              This image is attached to your original answer and uses the saved prompt from the database.
            </div>
          ) : null}
          {hasImagePrompt ? (
            <div className="mt-4 rounded-2xl border border-border/70 bg-muted/10 px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <div className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Image Prompt</div>
                <button
                  onClick={() => void navigator.clipboard.writeText(structured.image_prompt || '')}
                  className="rounded-full border border-border bg-background px-3 py-2 text-xs font-medium text-foreground hover:bg-muted transition-colors shrink-0"
                >
                  Copy
                </button>
              </div>
              <p className="mt-3 text-sm leading-7 text-foreground/90">{imagePrompt}</p>
            </div>
          ) : null}
        </div>
      ) : null}

      {audioSrc ? (
        <div className="rounded-3xl border border-border/70 bg-card px-4 py-4 md:px-5">
          <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Audio Result</div>
          <div className="mt-3">
            <audio controls className="w-full" src={audioSrc} />
          </div>
        </div>
      ) : null}

      <details className="rounded-3xl border border-border/70 bg-card px-4 py-4 md:px-5">
        <summary className="cursor-pointer list-none text-[11px] uppercase tracking-[0.28em] text-muted-foreground">
          More details
        </summary>
        <div className="mt-4 space-y-4">
          <div className="grid gap-4 xl:grid-cols-12">
            <div className="rounded-3xl border border-border/70 bg-background px-4 py-4 md:px-5 xl:col-span-7">
              <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Key Takeaways</div>
              <div className="mt-3 space-y-3">
                {keyPoints.length ? (
                  keyPoints.slice(0, 5).map((point, index) => (
                    <div key={index} className="flex gap-3 rounded-2xl border border-border/60 bg-muted/20 px-3 py-3">
                      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-secondary/10 text-xs font-semibold text-secondary">
                        {index + 1}
                      </div>
                      <div className="text-sm leading-6 text-foreground/90">{renderInline(point)}</div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-border/70 px-3 py-4 text-sm text-muted-foreground">
                    No key points were returned for this answer.
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-4 xl:col-span-5">
              {hasExample ? (
                <div className="rounded-3xl border border-border/70 bg-card px-4 py-4 md:px-5">
                  <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Example</div>
                  <div className="mt-3 text-sm leading-7 text-foreground/90">{renderRichContent(structured.example || '')}</div>
                </div>
              ) : null}

              {hasNextStep ? (
                <div className="rounded-3xl border border-border/70 bg-gradient-to-br from-secondary/10 to-background px-4 py-4 md:px-5">
                  <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Next Step</div>
                  <div className="mt-3 text-sm leading-7 text-foreground/90">{renderRichContent(structured.next_step || '')}</div>
                </div>
              ) : null}
            </div>
          </div>

          {hasCode ? (
            <div className="rounded-3xl border border-border/70 bg-slate-950 text-slate-50 px-4 py-4 md:px-5 shadow-[0_10px_30px_-22px_rgba(15,23,42,0.7)]">
              <div className="flex items-center justify-between gap-3 mb-3">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.28em] text-slate-300/70">Code Sample</div>
                  <div className="text-sm text-slate-300/90">Copy, edit, and run this snippet in the lab.</div>
                </div>
                <button
                  onClick={() => void navigator.clipboard.writeText(codeSample)}
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-100 hover:bg-white/10 transition-colors"
                >
                  Copy code
                </button>
              </div>
              <pre className="overflow-x-auto text-xs leading-6 text-slate-100">
                <code>{codeSample}</code>
              </pre>
            </div>
          ) : null}

          <div className="grid gap-4 xl:grid-cols-2">
            {hasPractice ? (
              <div className="rounded-3xl border border-border/70 bg-card px-4 py-4 md:px-5">
                <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Practice</div>
                <div className="mt-3 text-sm leading-7 text-foreground/90">{renderRichContent(structured.practice || '')}</div>
              </div>
            ) : null}

            {hasQuiz ? (
              <div className="rounded-3xl border border-border/70 bg-card px-4 py-4 md:px-5">
                <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Quick Check</div>
                <div className="mt-3 text-base font-semibold text-foreground">{quizQuestion}</div>
                {quizOptions.length ? (
                  <div className="mt-4 space-y-2">
                    {quizOptions.map((option) => (
                      <button
                        key={option}
                        className="w-full rounded-2xl border border-border/70 bg-muted/20 px-4 py-3 text-left text-sm hover:border-primary/40 hover:bg-primary/5 transition-colors"
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          {followUps.length ? (
            <div className="rounded-3xl border border-border/70 bg-background px-4 py-4 md:px-5">
              <div className="text-[11px] uppercase tracking-[0.28em] text-muted-foreground">Follow-up prompts</div>
              <div className="mt-3 flex flex-wrap gap-2">
                {followUps.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => onFollowUpPrompt(prompt)}
                    className="rounded-full border border-border bg-card px-3 py-2 text-xs font-medium text-foreground hover:border-primary/40 hover:bg-primary/5 transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </details>
    </div>
  );
}

function renderRichContent(content: unknown) {
  const safeContent = asString(content);
  const blocks = parseBlocks(safeContent);
  return blocks.map((block, index) => {
    if (block.type === 'heading') {
      return (
        <div key={index} className="text-base font-semibold text-foreground">
          {renderInline(block.text)}
        </div>
      );
    }

    if (block.type === 'code') {
      return (
        <pre key={index} className="rounded-xl bg-slate-950 text-slate-50 p-4 overflow-x-auto text-xs leading-6">
          <code>{block.text}</code>
        </pre>
      );
    }

    if (block.type === 'quote') {
      return (
        <div key={index} className="border-l-4 border-secondary bg-secondary/5 rounded-r-xl p-4 text-muted-foreground">
          {renderInline(block.text)}
        </div>
      );
    }

    if (block.type === 'list') {
      return (
        <ul key={index} className="space-y-2">
          {block.items.map((item, itemIndex) => (
            <li key={itemIndex} className="flex gap-3">
              <span className="mt-2 h-1.5 w-1.5 rounded-full bg-secondary flex-shrink-0" />
              <span>{renderInline(item)}</span>
            </li>
          ))}
        </ul>
      );
    }

    if (block.type === 'ordered') {
      return (
        <ol key={index} className="space-y-3 pl-5 list-decimal">
          {block.items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item)}</li>
          ))}
        </ol>
      );
    }

    if (block.type === 'table') {
      return (
        <div key={index} className="overflow-x-auto rounded-xl border border-border">
          <table className="min-w-full text-sm">
            <tbody>
              {block.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className={rowIndex === 0 ? 'bg-muted/60 font-medium' : 'border-t border-border'}>
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex} className="px-4 py-3 align-top">
                      {renderInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    return (
      <p key={index} className="whitespace-pre-wrap">
        {renderInline(block.text)}
      </p>
    );
  });
}

function renderInline(text: string) {
  const html = escapeHtml(asString(text))
    .replace(/`([^`]+)`/g, '<code class="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.85em]">$1</code>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\[(.*?)\]\((https?:\/\/[^\s)]+)\)/g, '<a class="text-secondary underline" href="$2" target="_blank" rel="noreferrer">$1</a>');

  return <span dangerouslySetInnerHTML={{ __html: html }} />;
}

function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function parseBlocks(content: unknown): Array<
  | { type: 'paragraph'; text: string }
  | { type: 'heading'; text: string }
  | { type: 'quote'; text: string }
  | { type: 'list'; items: string[] }
  | { type: 'ordered'; items: string[] }
  | { type: 'code'; text: string }
  | { type: 'table'; rows: string[][] }
> {
  const safeContent = asString(content);
  const lines = safeContent.replace(/\r\n/g, '\n').split('\n');
  const blocks: Array<any> = [];
  let buffer: string[] = [];
  let codeBuffer: string[] | null = null;
  let listBuffer: string[] = [];
  let orderedBuffer: string[] = [];
  let tableBuffer: string[] = [];

  const flushParagraph = () => {
    const text = buffer.join(' ').trim();
    if (text) blocks.push({ type: 'paragraph', text });
    buffer = [];
  };
  const flushList = () => {
    if (listBuffer.length) blocks.push({ type: 'list', items: listBuffer });
    listBuffer = [];
  };
  const flushOrdered = () => {
    if (orderedBuffer.length) blocks.push({ type: 'ordered', items: orderedBuffer });
    orderedBuffer = [];
  };
  const flushTable = () => {
    if (tableBuffer.length >= 2) {
      const rows = tableBuffer.map((row) =>
        row
          .split('|')
          .map((cell) => cell.trim())
          .filter(Boolean),
      );
      blocks.push({ type: 'table', rows });
    }
    tableBuffer = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    if (line.startsWith('```')) {
      if (codeBuffer) {
        blocks.push({ type: 'code', text: codeBuffer.join('\n') });
        codeBuffer = null;
      } else {
        flushParagraph();
        flushList();
        flushOrdered();
        flushTable();
        codeBuffer = [];
      }
      continue;
    }

    if (codeBuffer) {
      codeBuffer.push(rawLine);
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      flushList();
      flushOrdered();
      flushTable();
      continue;
    }

    if (/^#{1,3}\s+/.test(line)) {
      flushParagraph();
      flushList();
      flushOrdered();
      flushTable();
      blocks.push({ type: 'heading', text: line.replace(/^#{1,3}\s+/, '').trim() });
      continue;
    }

    if (/^>\s+/.test(line)) {
      flushParagraph();
      flushList();
      flushOrdered();
      flushTable();
      blocks.push({ type: 'quote', text: line.replace(/^>\s+/, '').trim() });
      continue;
    }

    if (/^(\-|\*|•)\s+/.test(line)) {
      flushParagraph();
      flushOrdered();
      flushTable();
      listBuffer.push(line.replace(/^(\-|\*|•)\s+/, '').trim());
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      flushParagraph();
      flushList();
      flushTable();
      orderedBuffer.push(line.replace(/^\d+\.\s+/, '').trim());
      continue;
    }

    if (line.includes('|') && line.split('|').length > 2) {
      flushParagraph();
      flushList();
      flushOrdered();
      tableBuffer.push(line);
      continue;
    }

    buffer.push(line);
  }

  if (codeBuffer) {
    blocks.push({ type: 'code', text: codeBuffer.join('\n') });
  }
  flushParagraph();
  flushList();
  flushOrdered();
  flushTable();

  return blocks.length ? blocks : [{ type: 'paragraph', text: safeContent }];
}

function asString(value: unknown): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (value == null) return '';
  try {
    return JSON.stringify(value);
  } catch {
    return '';
  }
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => asString(item).trim())
    .filter(Boolean);
}

function safeParseChatPayload(raw: string): ChatPayload | null {
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? (parsed as ChatPayload) : null;
  } catch {
    return null;
  }
}

function confidenceFromResponseType(responseType: string): ConfidenceLevel {
  if (responseType === 'visual') return 'High';
  if (responseType === 'auditory') return 'Medium';
  return 'High';
}
