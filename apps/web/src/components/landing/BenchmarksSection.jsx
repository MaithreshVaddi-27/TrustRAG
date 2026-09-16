import { useState } from 'react'
import { BarChart3 } from 'lucide-react'
import { BENCHMARKS } from './landingData'

export default function BenchmarksSection() {
  const [activeBenchmarkKey, setActiveBenchmarkKey] = useState('accuracy')
  const currentBenchmark = BENCHMARKS[activeBenchmarkKey]

  return (
    <section id="benchmarks" className="scroll-mt-24 relative z-20 py-20 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-3 shadow-md shadow-cyan-950/50">
          <BarChart3 size={13} />
          <span>EMPIRICAL BENCHMARKS & EVALUATION</span>
        </div>
        <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
          Proven Performance In Production
        </h2>
        <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3">
          Toggle between benchmark dimensions to examine quantitative accuracy, latency SLA, and vector storage memory savings.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
          {Object.keys(BENCHMARKS).map((key) => {
            const b = BENCHMARKS[key]
            const Icon = b.icon
            const isSelected = activeBenchmarkKey === key
            return (
              <button
                key={key}
                onClick={() => setActiveBenchmarkKey(key)}
                className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 border ${
                  isSelected
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-lg shadow-cyan-950/50 scale-105'
                    : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700 hover:scale-102'
                }`}
              >
                <Icon size={14} className={isSelected ? 'text-cyan-400 animate-pulse' : 'text-slate-500'} />
                <span>{b.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="rounded-3xl border border-slate-800/90 bg-surface-900/80 p-6 sm:p-10 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300 hover:border-cyan-500/40">
        <div className="mb-6">
          <h3 className="text-xl font-bold text-white">{currentBenchmark.title}</h3>
          <p className="text-slate-400 text-xs mt-1">{currentBenchmark.description}</p>
        </div>

        <div className="space-y-5">
          {currentBenchmark.metrics.map((m, i) => (
            <div key={i} className="space-y-1.5 group cursor-default">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className={`font-semibold ${m.highlight ? 'text-cyan-300' : 'text-slate-300'}`}>
                  {m.label}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] px-2 py-0.5 rounded bg-surface-850 border border-slate-800 text-slate-400">
                    {m.badge}
                  </span>
                  <span className={`font-bold ${m.highlight ? 'text-cyan-400 text-sm' : 'text-slate-300'}`}>
                    {m.value} {m.suffix}
                  </span>
                </div>
              </div>
              <div className="h-3 rounded-full bg-surface-950 border border-slate-800/80 overflow-hidden p-0.5">
                <div
                  className={`h-full rounded-full bg-gradient-to-r ${m.color} transition-all duration-700 shadow-sm`}
                  style={{ width: m.width }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
