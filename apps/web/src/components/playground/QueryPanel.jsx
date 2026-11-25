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
  embedding,
  activeProviderInfo,
  availableModels,
  refetchProviders,
  providersPending,
  providersFailed,
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
          <ErrorDisplay errorMsg={errorMsg} setErrorMsg={setErrorMsg} />

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
              providersPending={providersPending}
              providersFailed={providersFailed}
              refetchProviders={refetchProviders}
            />

            <EmbeddingModelDisplay
              embedding={embedding}
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
      </form>

      {/* The query and the run control sit outside the form so that they can
          stick to the foot of the pane. A sticky element cannot leave its
          containing block, and as the form's last child the compose bar
          could never move — on a phone the run button was always a scroll
          away. The button drives the run itself, so it does not need to be
          inside the form. */}
      <div className="lx-workbench__compose shrink-0 space-y-2 border-t border-[color:var(--rule)] px-5 py-4">
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
    </div>
  )
}
