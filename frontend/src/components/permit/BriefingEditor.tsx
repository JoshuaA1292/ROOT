'use client'

import { useState } from 'react'
import type { Briefing } from '@/lib/types'
import { api } from '@/lib/api'

interface Props {
  briefing: Briefing
  onUpdate: (updated: Briefing) => void
}

export default function BriefingEditor({ briefing, onUpdate }: Props) {
  const [text, setText] = useState(briefing.draft_comment)
  const [saving, setSaving] = useState(false)
  const [reviewing, setReviewing] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(briefing.status === 'submitted')
  const reviewed = briefing.status === 'reviewed' || briefing.status === 'exported'

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await api.briefings.patch(briefing.id, { draft_comment: text })
      onUpdate(updated)
    } finally {
      setSaving(false)
    }
  }

  const handleReview = async () => {
    setReviewing(true)
    try {
      const updated = await api.briefings.patch(briefing.id, {
        draft_comment: text,
        status: 'reviewed',
      })
      onUpdate(updated)
    } finally {
      setReviewing(false)
    }
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await api.briefings.submit(briefing.id)
      const updated = await api.briefings.get(briefing.id)
      onUpdate(updated)
      setSubmitted(true)
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="bg-root-green/20 border border-root-leaf/40 rounded-lg p-6 text-center space-y-2">
        <div className="text-2xl">&#10003;</div>
        <div className="text-root-leaf font-semibold">Comment submitted for review</div>
        <div className="text-sm text-white/60">
          Your public comment has been logged. Submit it to the agency at the permit link above.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white">Public Comment Draft</h3>
        <div className="flex gap-2">
          <span className={`text-xs px-2 py-1 rounded ${reviewed ? 'bg-root-leaf/15 text-root-leaf' : 'bg-yellow-500/20 text-yellow-400'}`}>
            {reviewed ? 'Human reviewed' : 'AI-drafted · Review required'}
          </span>
        </div>
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        className="w-full h-96 bg-root-bark/60 border border-white/10 rounded-lg p-4 text-sm text-white/90 font-mono resize-y focus:outline-none focus:border-root-leaf/40"
        placeholder="Generating comment..."
      />

      {briefing.citations.length > 0 && (
        <div className="bg-root-green/10 rounded p-3">
          <div className="text-xs font-semibold text-white/60 mb-2 uppercase tracking-wide">Citations</div>
          <ul className="space-y-1">
            {briefing.citations.map((c, i) => (
              <li key={i} className="text-xs text-white/50">— {c}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-4 py-2 bg-white/10 text-white/80 text-sm rounded hover:bg-white/20 transition-colors disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save edits'}
        </button>
        <button
          onClick={handleReview}
          disabled={reviewing || !text.trim()}
          className="px-4 py-2 bg-root-leaf/15 text-root-leaf text-sm font-semibold rounded hover:bg-root-leaf/25 transition-colors disabled:opacity-50"
        >
          {reviewing ? 'Marking...' : reviewed ? 'Reviewed' : 'Mark reviewed'}
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting || !text.trim() || !reviewed}
          className="px-6 py-2 bg-root-green text-white font-semibold text-sm rounded hover:bg-root-canopy transition-colors disabled:opacity-50"
        >
          {submitting ? 'Submitting...' : 'Submit comment'}
        </button>
        <span className="text-xs text-white/30 self-center">
          {reviewed ? 'Ready for steward submission.' : 'Review the draft before submitting.'}
        </span>
      </div>
    </div>
  )
}
