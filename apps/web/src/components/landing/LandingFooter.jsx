import { motion } from 'motion/react'
import { ExternalLink } from 'lucide-react'
import { TrustRagEmblem } from '@/components/common/TrustRagLogo'
import { useReducedMotion } from 'motion/react'

export default function LandingFooter() {
  const reduced = useReducedMotion()

  const springTransition = { type: 'spring', damping: 25, stiffness: 200 }
  const springTransitionGentle = { type: 'spring', damping: 30, stiffness: 180 }

  const footerVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: { opacity: 1, y: 0, transition: springTransitionGentle },
  }

  const linkVariants = {
    hidden: { opacity: 0, y: 8 },
    visible: (i) => ({ opacity: 1, y: 0, transition: { ...springTransitionGentle, delay: 0.1 + i * 0.05 } }),
  }

  return (
    <motion.footer
      className="relative z-20 border-t border-slate-800/80 py-12 bg-surface-950/90 text-xs text-slate-500"
      variants={footerVariants}
      initial="hidden"
      animate="visible"
      aria-labelledby="footer-heading"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
        <motion.div
          className="flex items-center gap-2.5"
          variants={linkVariants}
          custom={0}
        >
          <TrustRagEmblem size={28} framed={true} glow={false} aria-hidden="true" />
          <span className="font-bold text-slate-200 text-sm">TrustRAG</span>
          <span className="text-slate-500">Autonomous AI Reliability Platform</span>
        </motion.div>

        <motion.div
          className="flex items-center gap-2 text-[11px] font-mono text-emerald-400"
          variants={linkVariants}
          custom={1}
        >
          <motion.span
            className="w-2 h-2 rounded-full bg-emerald-400"
            animate={!reduced ? { scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] } : false}
            transition={{ duration: 1.5, ease: 'easeInOut', repeat: Infinity }}
            aria-hidden="true"
          />
          <span>Local-first verification pipeline</span>
        </motion.div>

        <motion.div
          className="flex items-center gap-6"
          variants={linkVariants}
          custom={2}
        >
          <motion.a
            href="https://github.com/MaithreshVaddi-27/TrustRAG"
            target="_blank"
            rel="noreferrer"
            className="hover:text-cyan-400 transition-colors flex items-center gap-1 spring-interactive px-3 py-2"
            whileHover={{ x: 2, transition: springTransition }}
            whileTap={{ scale: 0.95, transition: { duration: 0.08, ease: 'easeOut' } }}
            aria-label="TrustRAG on GitHub"
            style={{ minWidth: '44px', minHeight: '44px' }}
          >
            <span>GitHub</span>
            <ExternalLink size={12} aria-hidden="true" />
          </motion.a>
          <motion.button
            className="hover:text-cyan-400 transition-colors spring-interactive px-3 py-2"
            whileHover={{ x: 2, transition: springTransition }}
            whileTap={{ scale: 0.95, transition: { duration: 0.08, ease: 'easeOut' } }}
            style={{ minWidth: '44px', minHeight: '44px' }}
          >
            Sign In
          </motion.button>
          <motion.button
            className="hover:text-cyan-400 transition-colors spring-interactive px-3 py-2"
            whileHover={{ x: 2, transition: springTransition }}
            whileTap={{ scale: 0.95, transition: { duration: 0.08, ease: 'easeOut' } }}
            style={{ minWidth: '44px', minHeight: '44px' }}
          >
            Get Started
          </motion.button>
        </motion.div>
      </div>
    </motion.footer>
  )
}
