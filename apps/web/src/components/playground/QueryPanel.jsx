import { RotateCcw, Zap } from 'lucide-react'
import { KnowledgeBaseSelector } from './KnowledgeBaseSelector'
import { AIEngineSelector } from './AIEngineSelector'
import { WebSearchToggle } from './WebSearchToggle'
import { EmbeddingModelDisplay } from './EmbeddingModelDisplay'
import { QueryInput } from './QueryInput'
import { RunButton } from './RunButton'
import { ErrorDisplay } from './ErrorDisplay'

/**
 * QueryPanel — the fixed left pane of the workbench.
 *
 * Configuration scrolls; the query and the run control stay anchored at the
 * bottom, because the question you are asking is the one thing you should
 * never have to scroll to find.
 */
export function QueryPanel({
  query,
  setQuery,
  kbId,
  setKbId,
  knowledgeBases = [],
  selectedKb,
  loading,
  handleSubmit,
  handleReset,
  handlePresetSelect,
  errorMsg,
  setErrorMsg,
  enableWebSearch,
  setEnableWebSearch,
  selectedProvider,
  setSelectedProvider,
  selectedModel,
  setSelectedModel,
  selectedEmbeddingModel,
  activeProviderInfo,
  availableModels,
  refetchProviders,
  providersUnresolved,
  kbEmbeddingPin,
  embeddingMismatch,
  elapsedSec,
}) {
  return (
    <div className="lx-workbench__pane">
      <div className="lx-workbench__section flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="lx-h3 flex items-center gap-2">
            <Zap size={15} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
            Playground
          </h1>
          <p className="lx-micro mt-1">Reliability and provenance workbench</p>
        </div>

        <button
          type="button"
          onClick={handleReset}
          disabled={loading}
          className="lx-icon-btn shrink-0"
          title="Reset query and results"
          aria-label="Reset query and results"
        >
          <RotateCcw size={14} strokeWidth={1.5} aria-hidden="true" />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
        <div className="flex-1 space-y-5 overflow-y-auto">
          <div className="lx-workbench__section">
            <ErrorDisplay errorMsg={errorMsg} setErrorMsg={setErrorMsg} />
          </div>

          <div className="lx-workbench__section space-y-5">
            <KnowledgeBaseSelector
              kbId={kbId}
              setKbId={setKbId}
              knowledgeBases={knowledgeBases}
              selectedKb={selectedKb}
              loading={loading}
            />

            <AIEngineSelector
              selectedProvider={selectedProvider}
              setSelectedProvider={setSelectedProvider}
              activeProviderInfo={activeProviderInfo}
              availableModels={availableModels}
              selectedModel={selectedModel}
              setSelectedModel={setSelectedModel}
              loading={loading}
              providersUnresolved={providersUnresolved}
              refetchProviders={refetchProviders}
            />

            <EmbeddingModelDisplay
              selectedEmbeddingModel={selectedEmbeddingModel}
              selectedKb={selectedKb}
              kbEmbeddingPin={kbEmbeddingPin}
              embeddingMismatch={embeddingMismatch}
            />

            <WebSearchToggle
              enableWebSearch={enableWebSearch}
              setEnableWebSearch={setEnableWebSearch}
              loading={loading}
              selectedProvider={selectedProvider}
            />
          </div>
        </div>

        <div className="shrink-0 space-y-3 border-t border-[color:var(--rule)] bg-surface-raised px-5 py-5">
          <QueryInput
            query={query}
            setQuery={setQuery}
            loading={loading}
            handleSubmit={handleSubmit}
            handlePresetSelect={handlePresetSelect}
          />

          <RunButton
            loading={loading}
            elapsedSec={elapsedSec}
            disabled={!query.trim() || !kbId || !selectedProvider || !selectedModel}
            onClick={handleSubmit}
          />
        </div>
      </form>
    </div>
  )
}
