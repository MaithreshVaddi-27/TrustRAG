import AppLayout from '@/layouts/AppLayout'
import { FileSearch } from 'lucide-react'

export default function EvidencePage() {
  return (
    <AppLayout>
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Evidence</h1>
          <p className="text-slate-400 text-sm mt-1">Retrieved evidence across all analyses, with provenance metadata</p>
        </div>
        <div className="glass-card p-12 text-center text-slate-500">
          <FileSearch size={28} className="mx-auto mb-3 text-slate-600" />
          <p className="font-medium text-slate-400">No evidence records yet</p>
          <p className="text-sm mt-1">Evidence is persisted after each analysis run.</p>
        </div>
      </div>
    </AppLayout>
  )
}
