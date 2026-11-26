import { Terminal, Cpu, Zap, Lightbulb } from 'lucide-react'

/**
 * LocalLLMPanel — the private, offline inference engines.
 *
 * Each engine is a row with its status, its endpoint, the discovery command
 * and the models it has loaded. An engine that is not running gets a
 * recovery line, because the answer to "why is it off?" is always a command.
 */
const ENGINES = [
  {
    key: 'ollama',
    label: 'Ollama engine',
    icon: Cpu,
    endpoint: 'http://localhost:11434',
    discovery: 'ollama list',
    offlineLabel: 'Not running',
    recovery: (cmd) => (
      <>
        Start Ollama with <code>{cmd}</code> and pull{' '}
        <code>granite4.2:3b-q4_K_M</code>.
      </>
    ),
  },
  {
    key: 'llama_cpp',
    label: 'llama.cpp server',
    icon: Terminal,
    endpoint: 'http://127.0.0.1:9931/v1',
    discovery: 'llama-server --cache-list',
    offlineLabel: 'Standby',
    recovery: (cmd) => (
      <>
        Start the server with <code>{cmd}</code>.
      </>
    ),
  },
  {
    key: 'mlx',
    label: 'Apple MLX',
    icon: Zap,
    endpoint: 'http://127.0.0.1:8080/v1',
    discovery: 'mlx_lm / HuggingFace',
    offlineLabel: 'Standby',
    recovery: (cmd) => (
      <>
        Start the server with <code>{cmd}</code>.
      </>
    ),
  },
]

const RECOVERY_COMMANDS = {
  ollama: 'ollama serve',
  llama_cpp: './scripts/servers/start_local_llm.sh --port 9931',
  mlx: './scripts/servers/start_mlx_server.sh --port 8080',
}

export default function LocalLLMPanel({ providers, providersPending = false }) {
  return (
    <section className="lx-panel-block" aria-labelledby="local-llm-heading">
      <div className="lx-panel-block__head">
        <h2 id="local-llm-heading" className="lx-panel-block__title flex items-center gap-2">
          <Terminal size={16} strokeWidth={1.5} aria-hidden="true" />
          Local LLM infrastructure
        </h2>
        <span className="lx-micro">Private and offline</span>
      </div>

      <div className="lx-panel-block__body">
        <dl className="lx-deflist">
          {ENGINES.map(({ key, label, icon: Icon, endpoint, offlineLabel }) => {
            const engine = providers?.[key]
            const online = Boolean(engine?.connected)
            // Before the registry answers, an engine is neither running nor
            // stopped. It is unknown.
            const state = providersPending ? 'Detecting…' : online ? 'Online' : offlineLabel
            return (
              <div key={key} className="lx-deflist__row">
                <dt className="lx-deflist__key flex items-center gap-2">
                  <Icon size={14} strokeWidth={1.5} aria-hidden="true" className="text-silver-500" />
                  <span className="text-silver-300">{label}</span>
                  <span className="lx-micro">{endpoint}</span>
                </dt>
                <dd
                  className="lx-deflist__value"
                  style={!online ? { color: 'var(--color-silver-500)' } : undefined}
                >
                  {state}
                  {engine?.default_model && (
                    <span className="ml-2 text-silver-500">{engine.default_model}</span>
                  )}
                </dd>
              </div>
            )
          })}
        </dl>
      </div>

      <div className="lx-panel-block__foot">
        <ul className="space-y-2">
          {ENGINES.filter(({ key }) => !providersPending && !providers?.[key]?.connected).map(({ key, discovery, recovery }) => (
            <li key={key} className="lx-micro flex items-start gap-2">
              <Lightbulb
                size={13}
                strokeWidth={1.75}
                className="mt-0.5 shrink-0 text-silver-500"
                aria-hidden="true"
              />
              <span>
                {recovery(RECOVERY_COMMANDS[key])}
                <span className="ml-1 text-silver-500">Discovery: {discovery}</span>
              </span>
            </li>
          ))}
          {!providersPending &&
            ENGINES.every(({ key }) => providers?.[key]?.connected) && (
              <li className="lx-micro">Every local engine is reachable.</li>
            )}
        </ul>
      </div>
    </section>
  )
}
