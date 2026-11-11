import { useEffect } from 'react'
import {
  LandingNavbar,
  HeroSection,
  SimulationSandbox,
  CapabilitiesExplorer,
  BenchmarksSection,
  ComparisonMatrix,
  PipelineDiagram,
  LandingCTA,
  LandingFooter,
  SectionBand,
} from '@/components/landing'
import useScrollReveal from '@/hooks/useScrollReveal'

/**
 * LandingPage — the marketing surface.
 *
 * One entrance on load, one scroll reveal per section, one authored sweep
 * in the pipeline diagram. Nothing loops, nothing glows, and there is no
 * cursor spotlight.
 */
export default function LandingPage() {
  useScrollReveal('[data-lx-reveal]')

  useEffect(() => {
    document.title = 'TrustRAG — Claim-level verification for retrieval-augmented generation'
  }, [])

  return (
    <div className="min-h-screen bg-surface-950 text-slate-100">
      <a href="#main-content" className="lx-skip-link">
        Skip to main content
      </a>

      <LandingNavbar />

      <main id="main-content">
        <HeroSection />

        <SectionBand
          id="pipeline"
          title="One loop, six stages, one verdict."
          lede="Every stage below is in the path of every answer. The diagram runs once when it enters the viewport."
        >
          <div data-lx-reveal>
            <PipelineDiagram />
          </div>
        </SectionBand>

        <SectionBand
          id="simulation"
          title="Watch a claim fail its check."
          lede="Three runs from the system’s own fixture corpus. Each one shows the claims, the verdict on each, and the recovery that followed."
        >
          <div data-lx-reveal>
            <SimulationSandbox />
          </div>
        </SectionBand>

        <SectionBand
          id="capabilities"
          title="Six layers, and the code behind each."
          lede="Nothing here is a summary of a document. This is the part of the system that does the work."
        >
          <div data-lx-reveal>
            <CapabilitiesExplorer />
          </div>
        </SectionBand>

        <SectionBand
          id="benchmarks"
          title="What it measures."
          lede="Figures from the internal reliability fixture and from published literature, with the provenance of each stated."
        >
          <div data-lx-reveal>
            <BenchmarksSection />
          </div>
        </SectionBand>

        <SectionBand
          id="compare"
          title="Against the single-pass baseline."
          lede="The difference is a verification stage, not a larger model. Here is what that stage changes."
        >
          <div data-lx-reveal>
            <ComparisonMatrix />
          </div>
        </SectionBand>

        <section className="lx-section" aria-labelledby="cta-heading">
          <div className="lx-container">
            <div data-lx-reveal>
              <LandingCTA />
            </div>
          </div>
        </section>
      </main>

      <LandingFooter />
    </div>
  )
}
