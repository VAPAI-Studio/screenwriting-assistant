import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Upload, Trash2, BookOpen, Loader2, CheckCircle2,
  AlertCircle, Brain, Link2, RefreshCw,
  ChevronDown, FileText
} from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS } from '../../lib/constants';
import { Book, BookStatus, Agent } from '../../types';
import { Button } from '../UI/Button';

const STATUS_CONFIG: Record<BookStatus, { label: string; color: string; icon: typeof Loader2 }> = {
  pending: { label: 'Pending', color: 'text-muted-foreground', icon: RefreshCw },
  extracting: { label: 'Extracting text...', color: 'text-blue-400', icon: Loader2 },
  analyzing: { label: 'Building knowledge graph...', color: 'text-violet-400', icon: Brain },
  embedding: { label: 'Generating embeddings...', color: 'text-amber-400', icon: Loader2 },
  completed: { label: 'Ready', color: 'text-emerald-400', icon: CheckCircle2 },
  failed: { label: 'Failed', color: 'text-destructive', icon: AlertCircle },
};

function BookStatusBadge({ status }: { status: BookStatus }) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;
  const isProcessing = ['extracting', 'analyzing', 'embedding'].includes(status);

  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${config.color}`}>
      <Icon className={`h-3.5 w-3.5 ${isProcessing ? 'animate-spin' : ''}`} />
      {config.label}
    </span>
  );
}

function BookCard({
  book,
  agents,
  onDelete,
  onLinkAgent,
}: {
  book: Book;
  agents: Agent[];
  onDelete: (id: string) => void;
  onLinkAgent: (agentId: string, bookId: string) => void;
  onUnlinkAgent: (agentId: string, bookId: string) => void;
}) {
  const [showAgentMenu, setShowAgentMenu] = useState(false);

  const fileSizeMB = (book.file_size_bytes / (1024 * 1024)).toFixed(1);

  return (
    <div className="border border-border rounded-xl bg-card/60 hover:bg-card p-4 transition-all duration-200 hover:glow-amber group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="p-2.5 bg-amber-500/10 border border-amber-500/15 rounded-xl">
            <BookOpen className="h-5 w-5 text-amber-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-medium text-sm text-foreground truncate">{book.title}</h3>
            {book.author && (
              <p className="text-xs text-muted-foreground truncate">{book.author}</p>
            )}
            <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
              <span className="font-mono">{book.file_type.toUpperCase()}</span>
              <span className="font-mono">{fileSizeMB} MB</span>
              {book.total_concepts > 0 && (
                <span className="flex items-center gap-1">
                  <Brain className="h-3 w-3 text-violet-400" />
                  {book.total_concepts} concepts
                </span>
              )}
              {book.total_chunks > 0 && (
                <span className="flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  {book.total_chunks} chunks
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={() => onDelete(book.id)}
          className="p-1.5 text-transparent group-hover:text-muted-foreground hover:!text-destructive rounded-lg transition-colors"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      <div className="flex items-center justify-between">
        <BookStatusBadge status={book.status} />

        {book.status === 'completed' && (
          <div className="relative">
            <button
              onClick={() => setShowAgentMenu(!showAgentMenu)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-muted-foreground border border-border rounded-lg hover:text-foreground hover:border-muted-foreground/30 transition-colors"
            >
              <Link2 className="h-3 w-3" />
              Link to Agent
              <ChevronDown className={`h-3 w-3 transition-transform duration-200 ${showAgentMenu ? 'rotate-180' : ''}`} />
            </button>
            {showAgentMenu && (
              <div className="absolute right-0 top-full mt-1 w-56 bg-card border border-border rounded-xl shadow-xl z-10 animate-fade-in overflow-hidden">
                {agents.map((agent) => (
                  <button
                    key={agent.id}
                    onClick={() => {
                      onLinkAgent(agent.id, book.id);
                      setShowAgentMenu(false);
                    }}
                    className="w-full text-left px-3 py-2.5 text-sm hover:bg-muted/50 transition-colors flex items-center gap-2.5"
                  >
                    <span
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{ backgroundColor: agent.color }}
                    />
                    <span className="truncate">{agent.name}</span>
                  </button>
                ))}
                {agents.length === 0 && (
                  <div className="px-3 py-3 text-xs text-muted-foreground text-center">
                    No agents yet. Seed defaults first.
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {book.processing_error && (
        <p className="text-xs text-destructive mt-3 bg-destructive/10 border border-destructive/20 rounded-xl px-3 py-2">
          {book.processing_error}
        </p>
      )}
    </div>
  );
}

export function BookManager() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);

  const { data: books = [], isLoading: booksLoading } = useQuery({
    queryKey: [QUERY_KEYS.BOOKS],
    queryFn: () => api.getBooks(),
    refetchInterval: (query) => {
      const data = query.state.data as Book[] | undefined;
      const hasProcessing = data?.some(
        (b) => ['pending', 'extracting', 'analyzing', 'embedding'].includes(b.status)
      );
      return hasProcessing ? 5000 : false;
    },
  });

  const { data: agents = [] } = useQuery({
    queryKey: [QUERY_KEYS.AGENTS],
    queryFn: () => api.getAgents(),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', file.name.replace(/\.[^/.]+$/, ''));
      return api.uploadBook(formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.BOOKS] });
      setIsUploading(false);
    },
    onError: () => {
      setIsUploading(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteBook(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.BOOKS] });
    },
  });

  const seedMutation = useMutation({
    mutationFn: () => api.seedDefaultAgents(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.AGENTS] });
    },
  });

  const linkMutation = useMutation({
    mutationFn: ({ agentId, bookId }: { agentId: string; bookId: string }) =>
      api.linkBookToAgent(agentId, bookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.AGENTS] });
      queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.BOOKS] });
    },
  });

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    uploadMutation.mutate(file);
    e.target.value = '';
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Delete this book and all its extracted knowledge?')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="container mx-auto px-6 py-10 max-w-4xl animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-3xl font-semibold text-foreground">Books & Knowledge</h1>
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">
            Upload screenwriting books to power your AI agents with deep, concept-level understanding
          </p>
        </div>
        <div className="flex items-center gap-2">
          {agents.length === 0 && (
            <Button variant="outline" onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending}>
              {seedMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Brain className="h-4 w-4 mr-2" />
              )}
              Seed Default Agents
            </Button>
          )}
          <Button onClick={() => fileInputRef.current?.click()} disabled={isUploading} className="gap-1.5">
            {isUploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Upload className="h-4 w-4" />
            )}
            Upload Book
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.epub,.txt"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>
      </div>

      {/* Agent summary */}
      {agents.length > 0 && (
        <div className="mb-8 p-5 bg-card/40 border border-border rounded-xl">
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Agents</h2>
          <div className="flex flex-wrap gap-2">
            {agents.map((agent: Agent) => (
              <div
                key={agent.id}
                className="inline-flex items-center gap-2.5 bg-card border border-border rounded-full px-4 py-2 text-sm hover:glow-amber transition-all duration-200"
              >
                <span
                  className="w-2.5 h-2.5 rounded-full ring-2 ring-background"
                  style={{ backgroundColor: agent.color }}
                />
                <span className="font-medium text-foreground">{agent.name}</span>
                {agent.book_count > 0 && (
                  <span className="text-xs text-muted-foreground font-mono">
                    {agent.book_count} book{agent.book_count !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Books list */}
      {booksLoading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="h-6 w-6 animate-spin text-amber-500/60 mb-3" />
          <span className="text-sm text-muted-foreground">Loading library...</span>
        </div>
      ) : books.length === 0 ? (
        <div className="text-center py-20 border border-dashed border-border rounded-xl animate-fade-up">
          <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-5">
            <BookOpen className="h-7 w-7 text-amber-400" />
          </div>
          <h3 className="font-display text-lg font-semibold text-foreground mb-2">No books uploaded yet</h3>
          <p className="text-sm text-muted-foreground mb-6 max-w-md mx-auto leading-relaxed">
            Upload screenwriting books (PDF, EPUB, or TXT). Each book will be processed to extract
            concepts, relationships, and actionable questions for your AI agents.
          </p>
          <Button onClick={() => fileInputRef.current?.click()} className="gap-1.5">
            <Upload className="h-4 w-4" />
            Upload Your First Book
          </Button>
        </div>
      ) : (
        <div className="grid gap-3">
          {books.map((book: Book, index: number) => (
            <div key={book.id} className="animate-fade-up" style={{ animationDelay: `${index * 60}ms` }}>
              <BookCard
                book={book}
                agents={agents}
                onDelete={handleDelete}
                onLinkAgent={(agentId, bookId) => linkMutation.mutate({ agentId, bookId })}
                onUnlinkAgent={(agentId, bookId) => linkMutation.mutate({ agentId, bookId })}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
