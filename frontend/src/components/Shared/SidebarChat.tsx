import { useState, useRef, useEffect, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Send, Loader2, Zap, Check, RotateCcw, AlertCircle,
  BookOpen, ChevronDown, Lightbulb, Pencil,
} from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, STORAGE_KEYS } from '../../lib/constants';
import { ResizablePanel } from '../UI/ResizablePanel';
import { MarkdownContent } from './MarkdownContent';
import type { AIMessageResponse, SubsectionConfig, FieldDef, FieldGroup } from '../../types/template';
import type { Agent, ChatMessage, BookReference, ConsultedAgent } from '../../types';

type PanelMode = 'template' | 'agent';

interface SidebarChatProps {
  projectId: string;
  phase: string;
  subsectionKey: string;
  contextItemId?: string;
  subsection?: SubsectionConfig;
}

// ── Book footnotes ────────────────────────────────────────────────────────────
function BookFootnotes({ refs }: { refs: BookReference[] }) {
  const valid = refs.filter(r => r.concept_name || r.book_title || r.chapter || r.page);
  if (valid.length === 0) return null;
  return (
    <div className="mt-2 pt-2 border-t border-border/40">
      <ol className="space-y-0.5 list-none p-0 m-0">
        {valid.map((ref, i) => {
          const location = [ref.chapter, ref.page ? `p.\u2009${ref.page}` : ''].filter(Boolean).join(', ');
          return (
            <li key={i} className="flex gap-1.5 text-[11px] text-muted-foreground leading-snug">
              <span className="flex-shrink-0 font-medium opacity-50">[{i + 1}]</span>
              <span>
                {ref.concept_name && <span className="italic text-foreground/55">&ldquo;{ref.concept_name}&rdquo;</span>}
                {(ref.book_title || location) && (
                  <span className="opacity-60">
                    {ref.concept_name ? ' — ' : ''}
                    {ref.book_title && <span>{ref.book_title}</span>}
                    {location && <span>{ref.book_title ? ', ' : ''}{location}</span>}
                  </span>
                )}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

// ── Proposed changes confirmation card ────────────────────────────────────────
function ProposedChangesCard({
  updates,
  subsection,
  onApply,
  onDismiss,
  applying,
}: {
  updates: Record<string, string>;
  subsection?: SubsectionConfig;
  onApply: () => void;
  onDismiss: () => void;
  applying: boolean;
}) {
  const labelFor = (key: string) => {
    if (!subsection) return key;
    const allFields: FieldDef[] = [];
    if (subsection.fields) allFields.push(...subsection.fields);
    if (subsection.field_groups) subsection.field_groups.forEach((g: FieldGroup) => allFields.push(...g.fields));
    if (subsection.card_groups) subsection.card_groups.forEach(cg => allFields.push(...cg.fields));
    if (subsection.editor_config?.fields) allFields.push(...subsection.editor_config.fields);
    return allFields.find(f => f.key === key)?.label ?? key;
  };

  const entries = Object.entries(updates);
  if (entries.length === 0) return null;

  return (
    <div className="mx-3 mb-3 rounded-xl border border-violet-500/25 bg-violet-500/5 p-3">
      <div className="flex items-center gap-1.5 mb-2">
        <Pencil className="h-3.5 w-3.5 text-violet-400" />
        <span className="text-xs font-semibold text-violet-400 uppercase tracking-wider">Proposed changes</span>
      </div>
      <div className="space-y-2 mb-3 max-h-48 overflow-y-auto pr-1">
        {entries.map(([key, value]) => (
          <div key={key}>
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">{labelFor(key)}</p>
            <p className="text-xs text-foreground/70 leading-snug line-clamp-3">{value}</p>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button
          onClick={onApply}
          disabled={applying}
          className="flex-1 flex items-center justify-center gap-1.5 text-xs py-1.5 rounded-lg bg-violet-500/20 text-violet-300 border border-violet-500/20 hover:bg-violet-500/30 transition-colors font-medium disabled:opacity-50"
        >
          {applying ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
          Apply changes
        </button>
        <button
          onClick={onDismiss}
          disabled={applying}
          className="px-3 text-xs py-1.5 rounded-lg text-muted-foreground hover:bg-muted/50 transition-colors"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}

// ── Agent message bubble ─────────────────────────────────────────────────────
function AgentMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  const consultedAgents: ConsultedAgent[] = message.consulted_agents || [];
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
        isUser
          ? 'bg-amber-500/15 text-amber-100 border border-amber-500/10'
          : 'bg-muted/50 text-foreground/80 border border-border'
      }`}>
        {consultedAgents.length > 0 && (
          <div className="flex items-center flex-wrap gap-1.5 mb-2 pb-2 border-b border-border/60">
            <span className="text-xs text-muted-foreground">Consulted:</span>
            {consultedAgents.map((ca) => (
              <span key={ca.agent_id} className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border"
                style={{ borderColor: ca.color + '40', color: ca.color }}>
                {ca.name}
              </span>
            ))}
          </div>
        )}
        <MarkdownContent content={message.content} />
        {message.book_references && message.book_references.length > 0 && (
          <BookFootnotes refs={message.book_references} />
        )}
      </div>
    </div>
  );
}

export function SidebarChat({ projectId, phase, subsectionKey, contextItemId, subsection }: SidebarChatProps) {
  const queryClient = useQueryClient();

  // Panel mode (persisted across refreshes)
  const [panelMode, setPanelMode] = useState<PanelMode>(
    () => (localStorage.getItem(STORAGE_KEYS.SIDEBAR_CHAT_PANEL_MODE) as PanelMode) || 'template'
  );
  const handleSetPanelMode = (mode: PanelMode) => {
    setPanelMode(mode);
    localStorage.setItem(STORAGE_KEYS.SIDEBAR_CHAT_PANEL_MODE, mode);
  };

  // Template AI state
  const [input, setInput] = useState('');
  const [pendingBrainstormUpdates, setPendingBrainstormUpdates] = useState<Record<string, string> | null>(null);
  const [applyingBrainstorm, setApplyingBrainstorm] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [errorText, setErrorText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const agentMessagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const userScrolledUp = useRef(false);
  const prevContextRef = useRef({ projectId, phase, subsectionKey, contextItemId });

  // Agent state
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [agentSessionId, setAgentSessionId] = useState<string | null>(null);
  const [showAgentDropdown, setShowAgentDropdown] = useState(false);
  const [agentInput, setAgentInput] = useState('');
  const [agentStreaming, setAgentStreaming] = useState(false);
  const [agentStreamingText, setAgentStreamingText] = useState('');
  const [agentErrorText, setAgentErrorText] = useState('');
  const [pendingAgentUpdates, setPendingAgentUpdates] = useState<Record<string, string> | null>(null);
  const [applyingAgent, setApplyingAgent] = useState(false);

  // Agents query
  const { data: agents = [] } = useQuery({
    queryKey: [QUERY_KEYS.AGENTS],
    queryFn: () => api.getAgents(),
  });

  useEffect(() => {
    if (agents.length > 0 && !selectedAgentId) setSelectedAgentId(agents[0].id);
  }, [agents, selectedAgentId]);

  useEffect(() => {
    if (!selectedAgentId || !projectId) return;
    api.createChatSession({ agent_id: selectedAgentId, project_id: projectId })
      .then((s) => setAgentSessionId(s.id))
      .catch(console.error);
  }, [selectedAgentId, projectId]);

  const { data: agentMessages = [] } = useQuery({
    queryKey: QUERY_KEYS.CHAT_MESSAGES(agentSessionId || ''),
    queryFn: () => api.getChatMessages(agentSessionId!),
    enabled: !!agentSessionId,
    refetchInterval: false,
  });

  const selectedAgent = agents.find((a: Agent) => a.id === selectedAgentId);

  // Template session init
  const initSession = useCallback(async () => {
    try {
      // One continuous conversation per project — the lookup ignores sections.
      const existing = await api.lookupAISession(projectId);
      if (existing) { setSessionId(existing.id); return; }
    } catch { /* fall through */ }
    try {
      const s = await api.createAISession({ project_id: projectId, phase, subsection_key: subsectionKey, context_item_id: contextItemId });
      setSessionId(s.id);
    } catch { /* ignore */ }
    // phase/subsection only seed the CREATE (columns are non-null); they must
    // NOT re-trigger session init when the user navigates between sections.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    const prev = prevContextRef.current;
    if (prev.projectId !== projectId) setSessionId(null);
    prevContextRef.current = { projectId, phase, subsectionKey, contextItemId };
    initSession();
  }, [projectId, initSession]);

  const { data: messages = [] } = useQuery({
    queryKey: QUERY_KEYS.AI_MESSAGES(sessionId || ''),
    queryFn: () => api.getAIMessages(sessionId!),
    enabled: !!sessionId,
    refetchInterval: false,
  });

  useEffect(() => {
    if (!userScrolledUp.current) {
      const behavior = streamingText ? 'smooth' : 'auto';
      messagesEndRef.current?.scrollIntoView({ behavior });
    }
  }, [messages, streamingText, panelMode]);

  useEffect(() => {
    // Use instant scroll on panel switch / initial load, smooth during conversation
    const behavior = agentStreamingText ? 'smooth' : 'auto';
    agentMessagesEndRef.current?.scrollIntoView({ behavior });
  }, [agentMessages, agentStreamingText, panelMode]);

  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    userScrolledUp.current = el.scrollHeight - el.scrollTop - el.clientHeight >= 40;
  }, []);

  // ── Field context builder ──────────────────────────────────────────────────
  const buildFieldContext = useCallback(() => {
    if (!subsection) return undefined;
    const defs: FieldDef[] = [];
    if (subsection.fields) defs.push(...subsection.fields);
    if (subsection.cards) defs.push(...subsection.cards);
    if (subsection.field_groups) subsection.field_groups.forEach((g: FieldGroup) => defs.push(...g.fields));
    if (subsection.card_groups) subsection.card_groups.forEach(cg => defs.push(...cg.fields));
    if (subsection.editor_config?.fields) defs.push(...subsection.editor_config.fields);
    const listConfig = subsection.list_config;
    if (defs.length === 0 && !listConfig) return undefined;
    const cached = queryClient.getQueryData<any>(
      QUERY_KEYS.SUBSECTION_DATA(projectId, phase, subsectionKey)
    );
    return {
      field_definitions: defs.map(f => ({ key: f.key, label: f.label, type: f.type })),
      current_content: (cached?.content ?? {}) as Record<string, string>,
      subsection_label: subsection.name,
      ...(listConfig && {
        list_config: {
          item_type: listConfig.item_type,
          phase,
          subsection_key: subsectionKey,
        },
      }),
    };
  }, [subsection, projectId, phase, subsectionKey, queryClient]);

  // ── Apply handlers ─────────────────────────────────────────────────────────
  const applyFieldUpdates = useCallback(async (updates: Record<string, string>) => {
    if (contextItemId) {
      await api.updateListItem(contextItemId, { content: updates });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.LIST_ITEM(contextItemId) });
    } else {
      await api.updateSubsectionData(projectId, phase, subsectionKey, updates);
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.SUBSECTION_DATA(projectId, phase, subsectionKey),
      });
    }
  }, [contextItemId, projectId, phase, subsectionKey, queryClient]);

  const handleApplyAgentUpdates = async () => {
    if (!pendingAgentUpdates) return;
    setApplyingAgent(true);
    try {
      await applyFieldUpdates(pendingAgentUpdates);
    } finally {
      setApplyingAgent(false);
      setPendingAgentUpdates(null);
    }
  };

  const handleApplyBrainstormUpdates = async () => {
    if (!pendingBrainstormUpdates) return;
    setApplyingBrainstorm(true);
    try {
      await applyFieldUpdates(pendingBrainstormUpdates);
    } finally {
      setApplyingBrainstorm(false);
      setPendingBrainstormUpdates(null);
    }
  };

  // ── Template send ──────────────────────────────────────────────────────────
  const handleSend = async (override?: string) => {
    const content = override ?? input.trim();
    if (!content || !sessionId || isStreaming) return;
    setInput(''); setIsStreaming(true); setStreamingText(''); setErrorText('');
    setPendingBrainstormUpdates(null);
    userScrolledUp.current = false;
    try {
      await api.sendAIMessageStream(
        sessionId,
        content,
        { phase, subsectionKey, contextItemId },
        (chunk) => setStreamingText((prev) => prev + chunk),
        (data) => {
          const fu = data.metadata?.field_updates;
          if ((data.metadata?.list_items_created ?? 0) > 0) {
            // AI created new list items (scenes/episodes) — refresh the ordered list
            queryClient.invalidateQueries({ queryKey: ['list_items'] });
          }
          if (fu && Object.keys(fu).length > 0) {
            // Every concrete edit arrives as a proposal — applied only on click.
            setPendingBrainstormUpdates(fu);
          }
        },
      );
    } catch (err) {
      setErrorText(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setStreamingText(''); setIsStreaming(false);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.AI_MESSAGES(sessionId!) });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleYolo = () => {
    handleSend('Fill in ALL fields for this section. Generate comprehensive, complete content for every field based on the story context and any information already provided. Do not leave any field empty.');
  };

  const handleClear = async () => {
    if (!sessionId || isStreaming) return;
    setPendingBrainstormUpdates(null);
    try { await api.deleteAISession(sessionId); } catch { /* ignore */ }
    setSessionId(null);
    try {
      const s = await api.createAISession({ project_id: projectId, phase, subsection_key: subsectionKey, context_item_id: contextItemId });
      setSessionId(s.id);
    } catch { /* ignore */ }
  };

  // ── Agent send ─────────────────────────────────────────────────────────────
  const handleAgentSend = async () => {
    if (!agentInput.trim() || !agentSessionId || agentStreaming) return;
    const content = agentInput.trim();
    setAgentInput(''); setAgentStreaming(true); setAgentStreamingText('');
    setAgentErrorText('');
    setPendingAgentUpdates(null);
    const optimistic: ChatMessage = {
      id: 'temp-' + Date.now(), role: 'user', content,
      message_type: 'chat', book_references: [], consulted_agents: [],
      created_at: new Date().toISOString(),
    };
    queryClient.setQueryData(
      QUERY_KEYS.CHAT_MESSAGES(agentSessionId),
      (old: ChatMessage[] | undefined) => [...(old || []), optimistic],
    );
    let ok = false;
    try {
      const fieldContext = buildFieldContext();
      await api.sendChatMessageStream(
        agentSessionId,
        content,
        (chunk) => setAgentStreamingText((prev) => prev + chunk),
        (data) => {
          if (data.field_updates && Object.keys(data.field_updates).length > 0) {
            setPendingAgentUpdates(data.field_updates);
          }
          if ((data.list_items_created ?? 0) > 0) {
            queryClient.invalidateQueries({ queryKey: ['list_items'] });
          }
        },
        fieldContext,
      );
      ok = true;
    } catch (err) {
      console.error('Agent send error:', err);
      setAgentErrorText(err instanceof Error ? err.message : 'The agent could not respond. Please try again.');
    } finally {
      setAgentStreamingText(''); setAgentStreaming(false);
      // Only refetch from the server on success. On failure, refetching would drop
      // the optimistic user bubble and make the message appear to vanish — instead
      // we keep it on screen next to the visible error so the user can retry.
      if (ok) {
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.CHAT_MESSAGES(agentSessionId) });
      }
    }
  };

  const handleAgentKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void handleAgentSend(); }
  };

  const handleAgentSwitch = (agentId: string) => {
    setSelectedAgentId(agentId); setAgentSessionId(null); setShowAgentDropdown(false);
    setPendingAgentUpdates(null);
  };

  const hasFieldUpdates = (msg: AIMessageResponse) =>
    msg.message_type === 'action' && msg.metadata?.applied &&
    msg.metadata?.field_updates && Object.keys(msg.metadata.field_updates).length > 0;

  const hasFields = !!buildFieldContext();

  return (
    <ResizablePanel defaultWidth={320} minWidth={280} maxWidth={600} storageKey={STORAGE_KEYS.SIDEBAR_CHAT_WIDTH}>
    <div className="flex flex-col h-full border-l border-border bg-card/30">

      {/* ── Top panel mode tabs ────────────────────────────────────────── */}
      <div className="flex border-b border-border flex-shrink-0">
        <button
          onClick={() => handleSetPanelMode('template')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            panelMode === 'template'
              ? 'border-amber-500 text-amber-400'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Zap className="h-3 w-3" />
          Chat
        </button>
        <button
          onClick={() => handleSetPanelMode('agent')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium border-b-2 transition-colors ${
            panelMode === 'agent'
              ? 'border-violet-500 text-violet-400'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <BookOpen className="h-3 w-3" />
          Specialists
          {agents.length > 0 && (
            <span className="text-[10px] text-muted-foreground">({agents.length})</span>
          )}
        </button>
      </div>

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* TEMPLATE AI PANEL                                                  */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {panelMode === 'template' && (
        <>
          <div className="px-4 py-3 border-b border-border flex-shrink-0">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-foreground uppercase tracking-wider">Chat</h3>
              <div className="flex items-center gap-1">
                {(messages.length > 0 || streamingText) && (
                  <button onClick={handleClear} disabled={isStreaming} title="Clear"
                    className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors disabled:opacity-30">
                    <RotateCcw className="h-3 w-3" />
                  </button>
                )}
              </div>
            </div>
            {hasFields && (
              <p className="text-[10px] text-muted-foreground/70 px-0.5">
                Charlá libremente — cuando la IA tenga cambios concretos, te los propone y vos decidís si aplicarlos.
              </p>
            )}
          </div>

          <div ref={scrollContainerRef} onScroll={handleScroll} className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && !streamingText && (
              <div className="text-center py-8">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Charlá con la IA sobre esta sección — tiene el contexto de tu proyecto. Si surgen cambios concretos, te los propone para aplicar.
                </p>
              </div>
            )}
            {messages.map((msg: AIMessageResponse) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className="max-w-[85%]">
                  <div className={`rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    msg.role === 'user' ? 'bg-amber-500/15 text-amber-100 border border-amber-500/10'
                    : hasFieldUpdates(msg) ? 'bg-amber-500/5 text-foreground/80 border border-amber-500/15'
                    : 'bg-muted/50 text-foreground/80 border border-border'
                  }`}>
                    <MarkdownContent content={msg.content} />
                  </div>
                  {hasFieldUpdates(msg) && (
                    <div className="flex items-center gap-1 mt-1 ml-1">
                      <Check className="h-3 w-3 text-amber-400" />
                      <span className="text-[10px] text-amber-400/80 font-medium">Fields updated</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {streamingText && (
              <div className="flex justify-start">
                <div className="max-w-[85%]">
                  <div className="rounded-xl px-3.5 py-2.5 text-sm leading-relaxed bg-muted/50 text-foreground/80 border border-border">
                    <MarkdownContent content={streamingText} />
                  </div>
                </div>
              </div>
            )}
            {isStreaming && !streamingText && (
              <div className="flex justify-start">
                <div className="bg-muted/50 border border-border rounded-xl px-3.5 py-2.5">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              </div>
            )}
            {errorText && (
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm bg-destructive/10 text-destructive border border-destructive/20">
                  <div className="flex items-center gap-1.5 mb-1">
                    <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
                    <span className="font-medium text-xs">Error</span>
                  </div>
                  <p className="whitespace-pre-wrap text-xs">{errorText}</p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Brainstorm proposed changes */}
          {pendingBrainstormUpdates && (
            <ProposedChangesCard
              updates={pendingBrainstormUpdates}
              subsection={subsection}
              onApply={handleApplyBrainstormUpdates}
              onDismiss={() => setPendingBrainstormUpdates(null)}
              applying={applyingBrainstorm}
            />
          )}

          <div className="p-3 border-t border-border flex-shrink-0">
            {hasFields && (
              <div className="flex items-center justify-end mb-2 px-1">
                <button
                  onClick={handleYolo}
                  disabled={isStreaming || !sessionId}
                  title="La IA propone contenido para todos los campos de la sección — vos decidís si aplicarlo"
                  className="text-[10px] px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-medium"
                >
                  ⚡ Proponer todos los campos
                </button>
              </div>
            )}
            <div className="flex gap-2">
              <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
                placeholder="Escribile a la IA…"
                rows={1} disabled={!sessionId || isStreaming}
                className="flex-1 bg-input border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-amber-500/20 resize-none" />
              <button onClick={() => handleSend()} disabled={!input.trim() || !sessionId || isStreaming}
                className="px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:bg-amber-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex-shrink-0">
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════════ */}
      {/* AGENT PANEL                                                         */}
      {/* ══════════════════════════════════════════════════════════════════ */}
      {panelMode === 'agent' && (
        <>
          {/* Agent selector */}
          <div className="px-3 py-2.5 border-b border-border flex-shrink-0">
            <div className="relative">
              <button onClick={() => setShowAgentDropdown(!showAgentDropdown)}
                className="flex items-center gap-2 w-full px-3 py-1.5 rounded-lg hover:bg-muted/50 transition-colors text-sm font-medium text-foreground">
                {selectedAgent && (
                  <span className="w-2.5 h-2.5 rounded-full ring-2 ring-background flex-shrink-0" style={{ backgroundColor: selectedAgent.color }} />
                )}
                <span className="flex-1 text-left truncate">{selectedAgent?.name || 'Select Agent'}</span>
                <ChevronDown className={`h-3 w-3 text-muted-foreground transition-transform ${showAgentDropdown ? 'rotate-180' : ''}`} />
              </button>
              {showAgentDropdown && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-xl shadow-xl z-20 overflow-hidden">
                  {agents.map((agent: Agent) => (
                    <button key={agent.id} onClick={() => handleAgentSwitch(agent.id)}
                      className={`w-full text-left px-3 py-2.5 text-sm hover:bg-muted/50 transition-colors flex items-center gap-2.5 ${
                        agent.id === selectedAgentId ? 'bg-violet-500/10 text-violet-300' : 'text-foreground'
                      }`}>
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: agent.color }} />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium truncate">{agent.name}</div>
                        {agent.description && (
                          <div className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{agent.description}</div>
                        )}
                        <div className="text-[10px] text-muted-foreground/70 mt-0.5">
                          {agent.agent_type === 'orchestrator' && <span className="text-violet-400">Orchestrator</span>}
                          {agent.agent_type === 'tag_based' && <span className="text-emerald-400">Tags: {(agent.tags_filter || []).slice(0, 2).join(', ') || 'none'}</span>}
                          {agent.agent_type === 'book_based' && agent.book_count > 0 && <span>{agent.book_count} book{agent.book_count !== 1 ? 's' : ''} linked</span>}
                          {agent.agent_type === 'book_based' && !agent.book_count && <span className="text-muted-foreground/60">no books linked</span>}
                        </div>
                      </div>
                    </button>
                  ))}
                  {agents.length === 0 && (
                    <div className="px-3 py-4 text-xs text-muted-foreground text-center">
                      No agents. Go to Books & Knowledge to create one.
                    </div>
                  )}
                </div>
              )}
            </div>
            {selectedAgent?.description && (
              <p className="text-[10px] text-muted-foreground mt-1.5 px-1 line-clamp-2">
                {selectedAgent.description}
              </p>
            )}
            {hasFields && (
              <p className="text-[10px] text-violet-400/60 mt-1 px-1">
                Puede leer y proponer cambios en la sección actual
              </p>
            )}
          </div>

          {/* Agent messages */}
          <div className="flex-1 overflow-y-auto p-4">
            {agentMessages.length === 0 && !agentStreaming && (
              <div className="text-center py-10">
                <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center mx-auto mb-4">
                  <Lightbulb className="h-5 w-5 text-violet-400" />
                </div>
                <p className="text-sm font-medium text-foreground/80 mb-1">
                  {selectedAgent ? `Consultá a ${selectedAgent.name}` : 'Elegí un especialista'}
                </p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {selectedAgent?.description
                    ? selectedAgent.description
                    : 'Cada especialista domina un área según los libros que tiene vinculados — elegilo por el tipo de ayuda que buscás.'}
                  {hasFields && ' También puede proponer cambios en tu sección actual.'}
                </p>
              </div>
            )}
            {agentMessages.map((msg: ChatMessage) => (
              <AgentMessageBubble key={msg.id} message={msg} />
            ))}
            {agentStreamingText && (
              <div className="flex justify-start mb-3">
                <div className="max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed bg-muted/50 text-foreground/80 border border-border">
                  <MarkdownContent content={agentStreamingText} />
                </div>
              </div>
            )}
            {agentStreaming && !agentStreamingText && (
              <div className="flex justify-start mb-3">
                <div className="bg-muted/50 border border-border rounded-xl px-3.5 py-2.5">
                  <Loader2 className="h-4 w-4 animate-spin text-violet-500/60" />
                </div>
              </div>
            )}
            {agentErrorText && (
              <div className="flex justify-start mb-3">
                <div className="max-w-[85%] rounded-xl px-3.5 py-2.5 text-xs leading-relaxed bg-destructive/10 text-destructive border border-destructive/30">
                  <p className="whitespace-pre-wrap">{agentErrorText}</p>
                </div>
              </div>
            )}
            <div ref={agentMessagesEndRef} />
          </div>

          {/* Agent proposed changes */}
          {pendingAgentUpdates && (
            <ProposedChangesCard
              updates={pendingAgentUpdates}
              subsection={subsection}
              onApply={handleApplyAgentUpdates}
              onDismiss={() => setPendingAgentUpdates(null)}
              applying={applyingAgent}
            />
          )}

          {/* Agent input */}
          <div className="p-3 border-t border-border flex-shrink-0">
            <div className="flex gap-2">
              <textarea value={agentInput} onChange={(e) => setAgentInput(e.target.value)} onKeyDown={handleAgentKeyDown}
                placeholder={selectedAgent ? `Ask ${selectedAgent.name}...` : 'Select an agent first...'}
                rows={1} disabled={!agentSessionId || agentStreaming}
                className="flex-1 bg-input border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-violet-500/20 resize-none" />
              <button onClick={handleAgentSend} disabled={!agentInput.trim() || !agentSessionId || agentStreaming}
                className="px-3 py-2 bg-violet-500/20 text-violet-300 border border-violet-500/20 rounded-lg hover:bg-violet-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex-shrink-0">
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </>
      )}

    </div>
    </ResizablePanel>
  );
}
