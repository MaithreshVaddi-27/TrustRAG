import { useState } from 'react'
import {
  Cpu, Activity, Check
} from 'lucide-react'
import { CAPABILITIES } from './landingData'

export default function CapabilitiesExplorer() {
  const [activeCapKey, setActiveCapKey] = useState('langgraph')
  const currentCapability = CAPABILITIES[activeCapKey]

  return (
    <section id="features" className="scroll-mt-24 relative z-20 py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/60 text-xs font-mono text-cyan-400 mb-3 shadow-md shadow-cyan-950/50">
          <Cpu size={13} />
          <span>DEEP CAPABILITIES EXPLORER</span>
        </div>
        <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
          Interactive System Capabilities
        </h2>
        <p className="text-slate-400 text-sm sm:text-base max-w-2xl mx-auto mt-3">
          Click across the core verification subsystems below to explore code implementations, architectural invariants, and safety guarantees.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3 mt-8">
          {Object.keys(CAPABILITIES).map((key) => {
            const cap = CAPABILITIES[key]
            const Icon = cap.icon
            const isSelected = activeCapKey === key
            return (
              <button
                key={key}
                onClick={() => setActiveCapKey(key)}
                className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer flex items-center gap-2 border ${
                  isSelected
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-lg shadow-cyan-950/50 scale-105'
                    : 'bg-surface-900 text-slate-400 border-slate-800 hover:text-white hover:border-slate-700 hover:scale-102'
                }`}
              >
                <Icon size={14} className={isSelected ? 'text-cyan-400 animate-spin-slow' : 'text-slate-500'} />
                <span>{cap.title.split(' ')[0]} {cap.title.split(' ')[1]}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="rounded-3xl border border-slate-800/90 bg-surface-900/80 p-6 sm:p-10 backdrop-blur-xl shadow-2xl relative overflow-hidden transition-all duration-300 hover:border-cyan-500/40">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
          <div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-700/50 text-[11px] font-mono text-cyan-300 mb-4">
              <Activity size={12} />
              <span>{currentCapability.tagline}</span>
            </div>
            <h3 className="text-2xl sm:text-3xl font-extrabold text-white mb-4">
              {currentCapability.title}
            </h3>
            <p className="text-slate-300 text-sm leading-relaxed mb-6 font-normal">
              {currentCapability.desc}
            </p>
            <div className="space-y-2.5">
              {currentCapability.highlights.map((h, i) => (
                <div key={i} className="flex items-center gap-2.5 text-xs text-slate-300 font-mono">
                  <div className="w-5 h-5 rounded-full bg-emerald-950 border border-emerald-600/60 flex items-center justify-center text-emerald-400 shrink-0">
                    <Check size={11} />
                  </div>
                  <span>{h}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl bg-surface-950 border border-slate-800 p-5 font-mono text-xs text-slate-300 shadow-inner overflow-x-auto relative group">
            <div className="flex items-center justify-between text-[11px] text-slate-500 pb-3 mb-3 border-b border-slate-800/80">
              <span>implementation_preview.py</span>
              <span className="text-cyan-400 text-[10px]">Python 3.12 Verified</span>
            </div>
            <pre className="text-slate-300 text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap font-mono">
              {currentCapability.code}
            </pre>
          </div>
        </div>
      </div>
    </section>
  )
}
