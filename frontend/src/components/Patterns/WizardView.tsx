import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Loader2, Wand2, CheckCircle2, AlertCircle, Sparkles, Check } from 'lucide-react';
import { api } from '../../lib/api';
import { QUERY_KEYS, DEBOUNCE_DELAY } from '../../lib/constants';
import { FieldRenderer } from '../Shared/FieldRenderer';
import type { SubsectionConfig } from '../../types/template';

interface WizardViewProps {
  subsection: SubsectionConfig;
  projectId: string;
  phase: string;
  phaseData: any;
  templateConfig: any;
  withChat?: boolean;
  isImport?: boolean;
}

export function WizardView({ subsection, projectId, phase, phaseData, withChat, isImport }: WizardViewProps) {
  const queryClient = useQueryClient();
  const wizardConfig = subsection.wizard_config;
  const approaches = wizardConfig?.approaches || [];
  const countOptions = wizardConfig?.count_options || [];
  const readinessChecks = wizardConfig?.readiness_checks || [];

  const [selectedApproach, setSelectedApproach] = useState(approaches[0]?.key || '');
  const [selectedCount, setSelectedCount] = useState(wizardConfig?.default_count || countOptions[0] || 0);
  const [customGuidance, setCustomGuidance] = useState('');
  const [wizardRunId, setWizardRunId] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [saveTimer, setSaveTimer] = useState<ReturnType<typeof setTimeout> | null>(null);

  // Sync form data from phaseData (including AI action mode updates)
  useEffect(() => {
    if (phaseData?.content) {
      setFormData(phaseData.content as Record<string, string>);
    }
  }, [phaseData]);

  const fieldSaveMutation = useMutation({
    mutationFn: (content: Record<string, string>) =>
      api.updateSubsectionData(projectId, phase, subsection.key, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.SUBSECTION_DATA(projectId, phase, subsection.key) });
    },
  });

  const handleFieldChange = useCallback((key: string, value: string) => {
    setFormData(prev => {
      const updated = { ...prev, [key]: value };
      if (saveTimer) clearTimeout(saveTimer);
      const timer = setTimeout(() => {
        fieldSaveMutation.mutate(updated);
      }, DEBOUNCE_DELAY * 3);
      setSaveTimer(timer);
      return updated;
    });
  }, [saveTimer, fieldSaveMutation, projectId, phase, subsection.key]);

  const { data: readiness } = useQuery({
    queryKey: QUERY_KEYS.READINESS(projectId, phase),
    queryFn: () => api.getReadiness(projectId, phase),
    enabled: readinessChecks.length > 0,
  });

  const { data: wizardRun } = useQuery({
    queryKey: QUERY_KEYS.WIZARD_RUN(wizardRunId || ''),
    queryFn: () => api.getWizardRun(wizardRunId!),
    enabled: !!wizardRunId,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data && (data.status === 'completed' || data.status === 'failed') ? false : 2000;
    },
  });

  const runMutation = useMutation({
    mutationFn: () => api.runWizard({
      project_id: projectId,
      wizard_type: subsection.key,
      phase,
      config: {
        approach: selectedApproach,
        count: selectedCount,
        custom_guidance: customGuidance,
        ...formData,
      },
    }),
    onSuccess: (data) => {
      setWizardRunId(data.id);
    },
  });

  const applyMutation = useMutation({
    mutationFn: () => api.applyWizardResults(wizardRunId!),
    onSuccess: () => {
      setWizardRunId(null);
    },
  });

  const isRunning = wizardRun?.status === 'pending' || wizardRun?.status === 'running';
  const isCompleted = wizardRun?.status === 'completed';
  const isFailed = wizardRun?.status === 'failed';

  return (
    <div className="p-8 max-w-2xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="mb-8">
        <h2 className="font-display text-2xl font-semibold text-foreground">{subsection.name}</h2>
        {subsection.description && (
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{subsection.description}</p>
        )}
      </div>

      {/* Import fields */}
      {isImport && subsection.fields && (
        <div className="space-y-4 mb-6">
          {subsection.fields.map((field) => (
            <FieldRenderer
              key={field.key}
              field={field}
              value={customGuidance}
              onChange={(_, val) => setCustomGuidance(val)}
            />
          ))}
        </div>
      )}

      {/* Readiness Panel */}
      {readinessChecks.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5 mb-6">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">Readiness</h3>
          <div className="space-y-3">
            {readinessChecks.map((check) => {
              const score = readiness?.[`${check.phase}.${check.subsection_key}`] || 0;
              const total = check.field_count;
              const pct = total > 0 ? Math.round((score / total) * 100) : 0;

              return (
                <div key={check.label}>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-muted-foreground">{check.label}</span>
                    <span className={`font-mono ${pct >= 75 ? 'text-emerald-400' : pct >= 40 ? 'text-amber-400' : 'text-muted-foreground'}`}>
                      {score}/{total}
                    </span>
                  </div>
                  <div className="h-1 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        pct >= 75 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-500' : 'bg-muted-foreground/30'
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Approach Selector */}
      {approaches.length > 0 && (
        <div className="mb-6">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Approach</h3>
          <div className="space-y-2">
            {approaches.map((approach) => {
              const isSelected = selectedApproach === approach.key;
              return (
                <button
                  key={approach.key}
                  onClick={() => setSelectedApproach(approach.key)}
                  className={`
                    w-full text-left p-4 rounded-xl border transition-all duration-200
                    ${isSelected
                      ? 'border-amber-500/30 bg-amber-500/5 glow-amber'
                      : 'border-border bg-card/50 hover:bg-card hover:border-muted-foreground/20'
                    }
                  `}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full border-2 flex-shrink-0 transition-colors ${
                      isSelected ? 'border-amber-500 bg-amber-500' : 'border-muted-foreground/40'
                    }`}>
                      {isSelected && <div className="w-full h-full rounded-full bg-amber-500" />}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-foreground">{approach.name}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">{approach.description}</div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Count Selector */}
      {countOptions.length > 0 && (
        <div className="mb-6">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Count</h3>
          <div className="flex gap-2">
            {countOptions.map((count) => (
              <button
                key={count}
                onClick={() => setSelectedCount(count)}
                className={`
                  px-4 py-2 text-sm font-mono rounded-lg transition-all duration-200
                  ${selectedCount === count
                    ? 'bg-amber-500 text-amber-950 font-semibold shadow-md shadow-amber-900/20'
                    : 'bg-card text-muted-foreground border border-border hover:border-muted-foreground/30 hover:text-foreground'
                  }
                `}
              >
                {count}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Custom Guidance */}
      {!isImport && (
        <div className="mb-8">
          <label className="block text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Custom Guidance
            <span className="text-muted-foreground/60 font-normal normal-case tracking-normal ml-1">(optional)</span>
          </label>
          <textarea
            value={customGuidance}
            onChange={(e) => setCustomGuidance(e.target.value)}
            placeholder="Any additional direction for the AI..."
            rows={3}
            className="w-full bg-input border border-border rounded-xl px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500/30 resize-y transition-all"
          />
        </div>
      )}

      {/* Wizard with chat fields */}
      {withChat && subsection.fields && (
        <div className="space-y-4 border-t border-border pt-6 mb-8">
          {subsection.fields.map((field) => (
            <FieldRenderer
              key={field.key}
              field={field}
              value={formData[field.key] || ''}
              onChange={handleFieldChange}
            />
          ))}
          {/* Save status */}
          <div className="flex justify-end">
            <div className="flex items-center gap-1.5 text-xs">
              {fieldSaveMutation.isPending && <span className="text-muted-foreground animate-pulse-warm">Saving...</span>}
              {fieldSaveMutation.isSuccess && (
                <span className="flex items-center gap-1 text-emerald-400"><Check className="h-3 w-3" /> Saved</span>
              )}
              {fieldSaveMutation.isError && (
                <span className="flex items-center gap-1 text-destructive"><AlertCircle className="h-3 w-3" /> Failed</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Generate Button */}
      <button
        onClick={() => runMutation.mutate()}
        disabled={runMutation.isPending || isRunning}
        className="w-full py-3.5 bg-gradient-to-r from-amber-500 to-amber-600 text-amber-950 font-semibold rounded-xl shadow-lg shadow-amber-900/20 hover:from-amber-400 hover:to-amber-500 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
      >
        {runMutation.isPending || isRunning ? (
          <span className="flex items-center justify-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            Generating...
          </span>
        ) : isImport ? (
          <span className="flex items-center justify-center gap-2">
            <Sparkles className="h-4 w-4" />
            Import & Align
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <Wand2 className="h-4 w-4" />
            Generate
          </span>
        )}
      </button>

      {/* Results */}
      {isCompleted && wizardRun && (
        <div className="mt-6 bg-card border border-emerald-500/20 rounded-xl p-5 animate-fade-up">
          <div className="flex items-center justify-between mb-3">
            <span className="flex items-center gap-2 text-sm font-medium text-emerald-400">
              <CheckCircle2 className="h-4 w-4" />
              Generation Complete
            </span>
            <button
              onClick={() => applyMutation.mutate()}
              disabled={applyMutation.isPending}
              className="px-4 py-1.5 text-xs font-medium bg-emerald-500 text-emerald-950 rounded-lg hover:bg-emerald-400 transition-colors disabled:opacity-50"
            >
              {applyMutation.isPending ? 'Applying...' : 'Apply Results'}
            </button>
          </div>
          <pre className="text-xs text-muted-foreground max-h-48 overflow-y-auto whitespace-pre-wrap font-screenplay leading-relaxed">
            {JSON.stringify(wizardRun.result, null, 2)}
          </pre>
        </div>
      )}

      {isFailed && wizardRun && (
        <div className="mt-6 bg-destructive/5 border border-destructive/20 rounded-xl p-5 animate-fade-up">
          <span className="flex items-center gap-2 text-sm font-medium text-destructive mb-1">
            <AlertCircle className="h-4 w-4" />
            Generation Failed
          </span>
          <p className="text-sm text-destructive/80">{wizardRun.error_message || 'An error occurred'}</p>
        </div>
      )}
    </div>
  );
}
