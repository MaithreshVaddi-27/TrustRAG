import { motion } from 'motion/react'
import { ShieldCheck } from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar,
  XAxis, YAxis, Tooltip, Cell
} from 'recharts'

/**
 * ClaimDistributionChart - Claim verification breakdown bar chart
 * Called by: DashboardPage.jsx (line 544-603 in current implementation)
 * No existing file serves this purpose - extracted from DashboardPage
 * Reads/writes: Receives stats object as prop
 * User instruction: "continue and Use asynchronous methods for better working with async and await"
 */
export function ClaimDistributionChart({ stats }) {
  const claimDistributionData = [
    { name: 'Supported', count: stats.supportedClaims, color: '#10b981' },
    { name: 'Neutral', count: stats.neutralClaims, color: '#f59e0b' },
    { name: 'Contradicted', count: stats.contradictedClaims, color: '#ef4444' },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', damping: 25, stiffness: 200, delay: 0.2 }}
      className="glass-card p-6 flex flex-col justify-between"
    >
      <div className="mb-4">
        <h3 className="font-bold text-white text-base flex items-center gap-2">
          <ShieldCheck size={16} className="text-emerald-400" />
          Claim Verification Audit
        </h3>
        <p className="text-xs text-slate-400 mt-0.5">
          {stats.totalClaimsCount} atomic claims evaluated from history
        </p>
      </div>

      {stats.totalClaimsCount === 0 ? (
        <div className="h-48 w-full flex flex-col items-center justify-center text-center p-4 border border-dashed border-slate-800 rounded-xl bg-surface-900/40">
          <ShieldCheck size={24} className="text-slate-600 mb-2" />
          <p className="text-xs text-slate-300 font-medium">No claims decomposed yet</p>
          <p className="text-[11px] text-slate-500 mt-1 max-w-xs">
            Run a query in the Playground to extract and verify atomic assertions.
          </p>
        </div>
      ) : (
        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={claimDistributionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#080c16',
                  borderColor: '#1e293b',
                  borderRadius: '12px',
                  fontSize: '12px',
                  color: '#f8fafc',
                }}
              />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {claimDistributionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 pt-4 border-t border-slate-800/80 text-center">
        <div className="p-2 rounded-xl bg-emerald-950/20 border border-emerald-800/30">
          <p className="text-xs text-emerald-400 font-bold">{stats.supportedClaims}</p>
          <p className="text-[10px] text-slate-400">Supported ({stats.supportedRate}%)</p>
        </div>
        <div className="p-2 rounded-xl bg-amber-950/20 border border-amber-800/30">
          <p className="text-xs text-amber-400 font-bold">{stats.neutralClaims}</p>
          <p className="text-[10px] text-slate-400">Neutral</p>
        </div>
        <div className="p-2 rounded-xl bg-red-950/20 border border-red-800/30">
          <p className="text-xs text-red-400 font-bold">{stats.contradictedClaims}</p>
          <p className="text-[10px] text-slate-400">Contradicted</p>
        </div>
      </div>
    </motion.div>
  )
}