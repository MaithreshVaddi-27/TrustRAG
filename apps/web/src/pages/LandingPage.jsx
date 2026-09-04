import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LandingNavbar, HeroSection, SimulationSandbox,
  CapabilitiesExplorer, BentoArchitecture, BenchmarksSection,
  ComparisonMatrix, LandingFooter
} from '@/components/landing'

export default function LandingPage() {
  const navigate = useNavigate()
  const [mousePos, setMousePos] = useState({ x: -1000, y: -1000 })
  const containerRef = useRef(null)
  const rafId = useRef(null)

  const handleMouseMove = (e) => {
    if (!containerRef.current) return
    if (rafId.current) cancelAnimationFrame(rafId.current)
    rafId.current = requestAnimationFrame(() => {
      const rect = containerRef.current.getBoundingClientRect()
      setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top })
    })
  }

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      className="min-h-screen bg-surface-950 text-slate-100 font-sans selection:bg-sky-500/30 selection:text-sky-300 relative overflow-hidden bg-cyber-grid"
    >
      {/* Interactive Cursor Spotlight */}
      <div
        className="pointer-events-none fixed inset-0 z-10 transition-opacity duration-300 opacity-60"
        style={{
          background: `radial-gradient(650px circle at ${mousePos.x}px ${mousePos.y}px, rgba(14, 165, 233, 0.12), transparent 80%)`,
        }}
      />

      {/* Ambient Radial Flares */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[1000px] h-[550px] rounded-full bg-cyan-500/10 blur-[180px]" />
        <div className="absolute top-[35%] right-[-10%] w-[600px] h-[500px] rounded-full bg-primary-600/10 blur-[180px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[700px] h-[500px] rounded-full bg-teal-500/10 blur-[180px]" />
      </div>

      <LandingNavbar />
      <HeroSection />
      <SimulationSandbox />
      <CapabilitiesExplorer />
      <BentoArchitecture />
      <BenchmarksSection />
      <ComparisonMatrix />

      {/* Final CTA */}
      <section className="relative z-20 py-24 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="border-beam p-10 sm:p-20 rounded-3xl bg-gradient-to-b from-surface-900 to-surface-950 border border-cyan-500/40 shadow-2xl shadow-cyan-950/60 relative overflow-hidden">
          <div className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-cyan-500/15 blur-[120px] pointer-events-none" />
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
            Start Eliminating Hallucinations In Production
          </h2>
          <p className="text-slate-400 text-sm sm:text-base max-w-xl mx-auto mb-10 leading-relaxed">
            Deploy your knowledge bases, audit evidence integrity, and self-heal low-confidence RAG answers in minutes.
          </p>
          <button
            onClick={() => navigate('/login')}
            className="w-full sm:w-auto px-10 py-4 rounded-xl bg-gradient-to-r from-primary-600 via-sky-500 to-cyan-500 hover:from-primary-500 hover:to-cyan-400 text-white font-bold text-sm shadow-2xl shadow-cyan-950/80 border border-cyan-400/50 flex items-center justify-center gap-2.5 transition-all hover:scale-[1.05] active:scale-[0.98] cursor-pointer group relative overflow-hidden mx-auto"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full duration-700 transition-transform pointer-events-none" />
            <span>Get Started Now</span>
          </button>
        </div>
      </section>

      <LandingFooter />
    </div>
  )
}
