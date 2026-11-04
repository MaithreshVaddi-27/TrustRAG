import { Zap, RotateCcw } from 'lucide-react'
import { KnowledgeBaseSelector } from './KnowledgeBaseSelector'
import { AIEngineSelector } from './AIEngineSelector'
import { WebSearchToggle } from './WebSearchToggle'
import { EmbeddingModelDisplay } from './EmbeddingModelDisplay'
import { QueryInput } from './QueryInput'
import { RunButton } from './RunButton'
import { ErrorDisplay } from './ErrorDisplay'

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
    <div className="w-full md:w-[330px] lg:w-[370px] xl:w-[410px] shrink-0 border-b md:border-b-0 md:border-r border-slate-800 flex flex-col bg-surface-900/60 backdrop-blur-md h-auto md:h-full overflow-hidden">
      <div className="p-4 border-b border-slate-800 shrink-0 flex items-center justify-between">
        <div>
          <h2 className="font-semibold text-white flex items-center gap-2 text-sm">
            <span className="p-1 rounded-md bg-cyan-950/80 border border-cyan-500/40 text-cyan-400">
              <Zap size={14} />
            </span>
            <span>Playground</span>
          </h2>
          <div className="flex items-center gap-1.5 mt-0.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <p className="text-[11px] text-slate-400 font-medium">Reliability & Provenance Workbench</p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleReset}
          disabled={loading}
          title="Reset query and results (Clear)"
          aria-label="Reset query and results"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-surface-800 rounded-lg border border-slate-800 transition-colors"
        >
          <RotateCcw size={13} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex-1 min-h-0 flex flex-col overflow-hidden">
        <div className="p-4 space-y-4 flex-1 min-h-0 overflow-y-auto custom-scrollbar">
          <ErrorDisplay errorMsg={errorMsg} setErrorMsg={setErrorMsg} />

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

          <QueryInput
            query={query}
            setQuery={setQuery}
            loading={loading}
            handleSubmit={handleSubmit}
            handlePresetSelect={handlePresetSelect}
          />
        </div>

        <div className="p-4 border-t border-slate-800/80 bg-surface-900/95 backdrop-blur-md shrink-0 space-y-1.5">
          <RunButton
            loading={loading}
            elapsedSec={elapsedSec}
            disabled={!query.trim() || !kbId}
            onClick={handleSubmit}
          />
        </div>
      </form>
    </div>
  )
}