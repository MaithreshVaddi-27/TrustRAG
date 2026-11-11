import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import {
  ArrowRight, ChevronRight,
  Sparkles, Cpu, RefreshCw, BarChart3, ShieldCheck,
  Menu, X
} from 'lucide-react'
import { TrustRagEmblem } from '@/components/common/TrustRagLogo'
import { useAuthStore } from '@/store/authStore'

export default function LandingNavbar() {
  const { isAuthenticated } = useAuthStore()
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false)

  const springTransition = { type: 'spring', damping: 25, stiffness: 200 }
  const springTransitionGentle = { type: 'spring', damping: 30, stiffness: 180 }
  const pressTransition = { duration: 0.08, ease: 'easeOut' }

  const navLinkVariants = {
    hidden: { opacity: 0, y: 8, scale: 0.95 },
    visible: (i) => ({ opacity: 1, y: 0, scale: 1, transition: { ...springTransitionGentle, delay: 0.15 + i * 0.04 } }),
  }

  const mobileLinkVariants = {
    hidden: { opacity: 0, x: -12 },
    visible: (i) => ({ opacity: 1, x: 0, transition: { ...springTransitionGentle, delay: 0.05 + i * 0.04 } }),
  }

  const authButtonVariants = {
    hidden: { opacity: 0, scale: 0.9, y: 8 },
    visible: { opacity: 1, scale: 1, y: 0, transition: { ...springTransitionGentle, delay: 0.3 } },
  }

  return (
    <header className="sticky top-0 z-50 backdrop-blur-2xl bg-surface-950/80 border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <motion.div
            className="group-hover:scale-105 transition-transform shrink-0"
            whileHover={{ scale: 1.05, transition: springTransition }}
            aria-hidden="true"
          >
            <TrustRagEmblem size={36} framed={true} glow={true} />
          </motion.div>
          <div className="flex flex-col">
            <motion.span
              className="font-display text-base tracking-tight text-white flex items-center gap-1 spring-interactive"
              whileHover={{ x: 2, transition: springTransition }}
            >
              TRUST<span className="text-cyan-400">RAG</span>
            </motion.span>
            <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest hidden sm:inline">
              Reliability Workbench
            </span>
          </div>
        </Link>

        <motion.nav
          className="hidden md:flex items-center gap-7 text-xs font-medium text-slate-400"
          initial="hidden"
          animate="visible"
          variants={navLinkVariants}
        >
          <motion.a
            href="#simulation"
            variants={navLinkVariants}
            custom={0}
            className="hover:text-cyan-400 transition-colors flex items-center gap-1 spring-interactive"
            whileHover={{ x: 2, transition: springTransition }}
            whileTap={{ scale: 0.95, transition: pressTransition }}
          >
            <Sparkles size={13} className="text-cyan-400" aria-hidden="true" />
            <span>Sandbox</span>
          </motion.a>
          <motion.a
            href="#features"
            variants={navLinkVariants}
            custom={1}
            className="hover:text-cyan-400 transition-colors spring-interactive"
            whileHover={{ x: 2, transition: springTransition }}
            whileTap={{ scale: 0.95, transition: pressTransition }}
          >
            Capabilities
          </motion.a>
          <motion.a
            href="#bento"
            variants={navLinkVariants}
            custom={2}
            className="hover:text-cyan-400 transition-colors spring-interactive"
            whileHover={{ x: 2, transition: springTransition }}
            whileTap={{ scale: 0.95, transition: pressTransition }}
          >
            Architecture
          </motion.a>
          <motion.a
            href="#benchmarks"
            variants={navLinkVariants}
            custom={3}
            className="hover:text-cyan-400 transition-colors spring-interactive"
            whileHover={{ x: 2, transition: springTransition }}
            whileTap={{ scale: 0.95, transition: pressTransition }}
          >
            Benchmarks
          </motion.a>
          <motion.a
            href="#compare"
            variants={navLinkVariants}
            custom={4}
            className="hover:text-cyan-400 transition-colors spring-interactive"
            whileHover={{ x: 2, transition: springTransition }}
            whileTap={{ scale: 0.95, transition: pressTransition }}
          >
            Comparison
          </motion.a>
        </motion.nav>

        <motion.div
          className="flex items-center gap-2.5"
          initial="hidden"
          animate="visible"
          variants={authButtonVariants}
        >
          {isAuthenticated ? (
            <motion.button
              onClick={() => {}}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-950/50 border border-cyan-400/30 transition-all hover:scale-[1.02] spring-interactive action-feedback"
              whileHover={{ scale: 1.05, transition: springTransition }}
              whileTap={{ scale: 0.97, transition: pressTransition }}
            >
              <span>Dashboard</span>
              <ChevronRight size={14} aria-hidden="true" />
            </motion.button>
          ) : (
            <motion.div
              className="hidden sm:flex items-center gap-3"
              variants={authButtonVariants}
            >
              <motion.button
                onClick={() => {}}
                className="px-3.5 py-2 rounded-xl text-slate-300 hover:text-white hover:bg-surface-800/80 text-xs font-semibold transition-colors spring-interactive action-feedback"
                whileHover={{ scale: 1.05, transition: springTransition }}
                whileTap={{ scale: 0.97, transition: pressTransition }}
                style={{ minWidth: '44px', minHeight: '44px' }}
              >
                Sign In
              </motion.button>
              <motion.button
                onClick={() => {}}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-primary-600 to-cyan-600 hover:from-primary-500 hover:to-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-950/50 border border-cyan-400/30 transition-all hover:scale-[1.02] spring-interactive action-feedback"
                whileHover={{ scale: 1.05, transition: springTransition }}
                whileTap={{ scale: 0.97, transition: pressTransition }}
                style={{ minWidth: '44px', minHeight: '44px' }}
              >
                <span>Get Started</span>
                <ArrowRight size={13} aria-hidden="true" />
              </motion.button>
            </motion.div>
          )}

          <motion.button
            onClick={() => setIsMobileNavOpen(prev => !prev)}
            className="md:hidden flex items-center justify-center w-9 h-9 rounded-xl border border-slate-800 text-slate-400 hover:text-white hover:bg-surface-800 transition-colors spring-interactive action-feedback"
            whileHover={{ scale: 1.05, transition: springTransition }}
            whileTap={{ scale: 0.97, transition: pressTransition }}
            aria-label="Toggle mobile menu"
            aria-expanded={isMobileNavOpen}
            aria-controls="mobile-nav"
          >
            {isMobileNavOpen ? <X size={18} aria-hidden="true" /> : <Menu size={18} aria-hidden="true" />}
          </motion.button>
        </motion.div>
      </div>

      <motion.div
        id="mobile-nav"
        className="md:hidden bg-surface-950/95 border-b border-slate-800 backdrop-blur-2xl px-4 pt-3 pb-5 space-y-3"
        initial={false}
        animate={isMobileNavOpen
          ? { opacity: 1, height: 'auto', paddingTop: '0.75rem', paddingBottom: '1.25rem' }
          : { opacity: 0, height: 0, paddingTop: 0, paddingBottom: 0 }
        }
        transition={{ ...springTransitionGentle, duration: 0.3 }}
        overflow="hidden"
      >
        <motion.div
          className="flex flex-col space-y-1.5 text-xs font-medium text-slate-300"
          variants={mobileLinkVariants}
        >
          <motion.a
            href="#simulation"
            onClick={() => setIsMobileNavOpen(false)}
            variants={mobileLinkVariants}
            custom={0}
            className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2 spring-interactive"
            whileHover={{ x: 4, transition: springTransition }}
            whileTap={{ scale: 0.98, transition: pressTransition }}
          >
            <Sparkles size={14} className="text-cyan-400" aria-hidden="true" />
            <span>Interactive Sandbox</span>
          </motion.a>
          <motion.a
            href="#features"
            onClick={() => setIsMobileNavOpen(false)}
            variants={mobileLinkVariants}
            custom={1}
            className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2 spring-interactive"
            whileHover={{ x: 4, transition: springTransition }}
            whileTap={{ scale: 0.98, transition: pressTransition }}
          >
            <Cpu size={14} className="text-cyan-400" aria-hidden="true" />
            <span>Capabilities Explorer</span>
          </motion.a>
          <motion.a
            href="#bento"
            onClick={() => setIsMobileNavOpen(false)}
            variants={mobileLinkVariants}
            custom={2}
            className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2 spring-interactive"
            whileHover={{ x: 4, transition: springTransition }}
            whileTap={{ scale: 0.98, transition: pressTransition }}
          >
            <RefreshCw size={14} className="text-cyan-400" aria-hidden="true" />
            <span>Architecture</span>
          </motion.a>
          <motion.a
            href="#benchmarks"
            onClick={() => setIsMobileNavOpen(false)}
            variants={mobileLinkVariants}
            custom={3}
            className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2 spring-interactive"
            whileHover={{ x: 4, transition: springTransition }}
            whileTap={{ scale: 0.98, transition: pressTransition }}
          >
            <BarChart3 size={14} className="text-cyan-400" aria-hidden="true" />
            <span>Benchmarks</span>
          </motion.a>
          <motion.a
            href="#compare"
            onClick={() => setIsMobileNavOpen(false)}
            variants={mobileLinkVariants}
            custom={4}
            className="px-3 py-2 rounded-lg hover:bg-surface-850 hover:text-cyan-400 transition-colors flex items-center gap-2 spring-interactive"
            whileHover={{ x: 4, transition: springTransition }}
            whileTap={{ scale: 0.98, transition: pressTransition }}
          >
            <ShieldCheck size={14} className="text-cyan-400" aria-hidden="true" />
            <span>Why TrustRAG</span>
          </motion.a>
        </motion.div>

        <motion.div
          className="pt-3 border-t border-slate-800/80 flex items-center gap-2.5"
          initial="hidden"
          animate={isMobileNavOpen ? 'visible' : 'hidden'}
          variants={mobileLinkVariants}
          custom={5}
        >
          {!isAuthenticated && (
            <>
              <motion.button
                onClick={() => { setIsMobileNavOpen(false) }}
                className="flex-1 py-2.5 rounded-xl text-center text-xs font-semibold text-slate-300 bg-surface-900 border border-slate-800 spring-interactive action-feedback"
                whileHover={{ scale: 1.02, transition: springTransition }}
                whileTap={{ scale: 0.98, transition: pressTransition }}
              >
                Sign In
              </motion.button>
              <motion.button
                onClick={() => { setIsMobileNavOpen(false) }}
                className="flex-1 py-2.5 rounded-xl text-center text-xs font-semibold text-white bg-gradient-to-r from-primary-600 to-cyan-600 shadow-md spring-interactive action-feedback"
                whileHover={{ scale: 1.02, transition: springTransition }}
                whileTap={{ scale: 0.98, transition: pressTransition }}
              >
                Get Started
              </motion.button>
            </>
          )}
        </motion.div>
      </motion.div>
    </header>
  )
}
