import { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Send, Loader2, MessageSquare, Zap, Check, RotateCcw, AlertCircle } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, STORAGE_KEYS } from '../../lib/constants';
import { ResizablePanel } from '../UI/ResizablePanel';
import type { AIMessageResponse } from '../../types/template';

type ChatMode = 'brainstorm' | 'action';

interface SidebarChatProps {
  projectId: string;
  phase: string;
  subsectionKey: string;
  contextItemId?: string;
}

export function SidebarChat({ projectId, phase, subsectionKey, contextItemId }: SidebarChatProps) {
  const queryClient = useQueryClient();
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<ChatMode>('brainstorm');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [errorText, setErrorText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const userScrolledUp = useRef(false);
  const prevContextRef = useRef({ projectId, phase, subsectionKey, contextItemId });

  // Try to resume an existing session, otherwise create a new one
  const initSession = useCallback(async () => {
    try {
      const existing = await api.lookupAISession(projectId, phase, subsectionKey, contextItemId);
      if (existing) {
        setSessionId(existing.id);
        return;
      }
    } catch {
      // No existing session found — fall through to create
    }
    try {
      const session = await api.createAISession({
        project_id: projectId,
        phase,
        subsection_key: subsectionKey,
        context_item_id: contextItemId,
      });
      setSessionId(session.id);
    } catch {
      // ignore creation errors
    }
  }, [projectId, phase, subsectionKey, contextItemId]);

  // Init session on mount and when context changes
  useEffect(() => {
    const prev = prevContextRef.current;
    const contextChanged =
      prev.projectId !== projectId ||
      prev.phase !== phase ||
      prev.subsectionKey !== subsectionKey ||
      prev.contextItemId !== contextItemId;

    if (contextChanged) {
      setSessionId(null);
    }

    prevContextRef.current = { projectId, phase, subsectionKey, contextItemId };
    initSession();
  }, [projectId, phase, subsectionKey, contextItemId, initSession]);

  const { data: messages = [] } = useQuery({
    queryKey: QUERY_KEYS.AI_MESSAGES(sessionId || ''),
    queryFn: () => api.getAIMessages(sessionId!),
    enabled: !!sessionId,
    refetchInterval: false,
  });

  // Auto-scroll unless user has scrolled up
  useEffect(() => {
    if (!userScrolledUp.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamingText]);

  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    // Consider "at bottom" if within 40px of the bottom
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    userScrolledUp.current = !atBottom;
  }, []);

  const handleSend = async () => {
    if (!input.trim() || !sessionId || isStreaming) return;
    const content = input.trim();
    setInput('');
    setIsStreaming(true);
    setStreamingText('');
    setErrorText('');
    userScrolledUp.current = false;

    try {
      await api.sendAIMessageStream(
        sessionId,
        content,
        mode,
        // onChunk — accumulate streaming text
        (chunk) => {
          setStreamingText((prev) => prev + chunk);
        },
        // onDone — refresh messages and handle field updates
        (data) => {
          if (data.metadata?.applied && data.metadata?.field_updates &&
              Object.keys(data.metadata.field_updates).length > 0) {
            queryClient.invalidateQueries({
              queryKey: QUERY_KEYS.SUBSECTION_DATA(projectId, phase, subsectionKey),
            });
            if (contextItemId) {
              queryClient.invalidateQueries({
                queryKey: QUERY_KEYS.LIST_ITEM(contextItemId),
              });
            }
          }
        },
      );
    } catch (err) {
      console.error('AI chat error:', err);
      setErrorText(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setStreamingText('');
      setIsStreaming(false);
      // Refresh messages from server to get the saved version
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.AI_MESSAGES(sessionId!) });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClear = async () => {
    if (!sessionId || isStreaming) return;
    try { await api.deleteAISession(sessionId); } catch { /* ignore */ }
    setSessionId(null);
    // Create a fresh session (don't lookup — we just deleted it)
    try {
      const session = await api.createAISession({
        project_id: projectId,
        phase,
        subsection_key: subsectionKey,
        context_item_id: contextItemId,
      });
      setSessionId(session.id);
    } catch { /* ignore */ }
  };

  const hasFieldUpdates = (msg: AIMessageResponse) =>
    msg.message_type === 'action' &&
    msg.metadata?.applied &&
    msg.metadata?.field_updates &&
    Object.keys(msg.metadata.field_updates).length > 0;

  return (
    <ResizablePanel
      defaultWidth={320}
      minWidth={280}
      maxWidth={600}
      storageKey={STORAGE_KEYS.SIDEBAR_CHAT_WIDTH}
    >
    <div className="flex flex-col h-full border-l border-border bg-card/30">
      {/* Header with mode toggle */}
      <div className="px-4 py-3 border-b border-border flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">AI Chat</h3>
          {(messages.length > 0 || streamingText) && (
            <button
              onClick={handleClear}
              disabled={isStreaming}
              title="Clear conversation"
              className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors disabled:opacity-30"
            >
              <RotateCcw className="h-3 w-3" />
            </button>
          )}
        </div>
        <div className="flex gap-1 bg-muted/30 rounded-lg p-0.5">
          <button
            onClick={() => setMode('brainstorm')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-medium transition-all ${
              mode === 'brainstorm'
                ? 'bg-card text-foreground shadow-sm border border-border'
                : 'text-muted-foreground hover:text-foreground/70'
            }`}
          >
            <MessageSquare className="h-3 w-3" />
            Brainstorm
          </button>
          <button
            onClick={() => setMode('action')}
            className={`flex-1 flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-medium transition-all ${
              mode === 'action'
                ? 'bg-amber-500/15 text-amber-300 shadow-sm border border-amber-500/20'
                : 'text-muted-foreground hover:text-foreground/70'
            }`}
          >
            <Zap className="h-3 w-3" />
            Do stuff
          </button>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollContainerRef} onScroll={handleScroll} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && !streamingText && (
          <div className="text-center py-8">
            <p className="text-xs text-muted-foreground leading-relaxed">
              {mode === 'brainstorm'
                ? 'Discuss ideas freely. The AI has context about your current work.'
                : 'Ask the AI to fill in or modify fields. Changes will be applied directly.'}
            </p>
          </div>
        )}

        {messages.map((msg: AIMessageResponse) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className="max-w-[85%]">
              <div
                className={`
                  rounded-xl px-3.5 py-2.5 text-sm leading-relaxed
                  ${msg.role === 'user'
                    ? 'bg-amber-500/15 text-amber-100 border border-amber-500/10'
                    : hasFieldUpdates(msg)
                      ? 'bg-amber-500/5 text-foreground/80 border border-amber-500/15'
                      : 'bg-muted/50 text-foreground/80 border border-border'
                  }
                `}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
              {/* Field updates indicator */}
              {hasFieldUpdates(msg) && (
                <div className="flex items-center gap-1 mt-1 ml-1">
                  <Check className="h-3 w-3 text-amber-400" />
                  <span className="text-[10px] text-amber-400/80 font-medium">
                    Fields updated
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Streaming response */}
        {streamingText && (
          <div className="flex justify-start">
            <div className="max-w-[85%]">
              <div className="rounded-xl px-3.5 py-2.5 text-sm leading-relaxed bg-muted/50 text-foreground/80 border border-border">
                <p className="whitespace-pre-wrap">{streamingText}</p>
              </div>
              {/* "Applying changes" indicator during phase 2 extraction */}
              {isStreaming && mode === 'action' && (
                <div className="flex items-center gap-1.5 ml-2 mt-1">
                  <Loader2 className="h-3 w-3 animate-spin text-amber-400" />
                  <span className="text-[10px] text-amber-400/80 font-medium">
                    Applying changes...
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Loading indicator (before streaming starts) */}
        {isStreaming && !streamingText && (
          <div className="flex justify-start">
            <div className="bg-muted/50 border border-border rounded-xl px-3.5 py-2.5">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          </div>
        )}

        {/* Error display */}
        {errorText && (
          <div className="flex justify-start">
            <div className="max-w-[85%]">
              <div className="rounded-xl px-3.5 py-2.5 text-sm leading-relaxed bg-destructive/10 text-destructive border border-destructive/20">
                <div className="flex items-center gap-1.5 mb-1">
                  <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
                  <span className="font-medium text-xs">Error</span>
                </div>
                <p className="whitespace-pre-wrap text-xs">{errorText}</p>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-border flex-shrink-0">
        {mode === 'action' && (
          <div className="flex items-center gap-1.5 mb-2 px-1">
            <Zap className="h-3 w-3 text-amber-400/60" />
            <span className="text-[10px] text-amber-400/60 font-medium">
              AI can modify fields
            </span>
          </div>
        )}
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={mode === 'brainstorm' ? 'Ask the AI...' : 'Tell the AI what to change...'}
            rows={1}
            className="flex-1 bg-input border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-amber-500/20 resize-none"
            disabled={!sessionId || isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || !sessionId || isStreaming}
            className="px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:bg-amber-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex-shrink-0"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
    </ResizablePanel>
  );
}
