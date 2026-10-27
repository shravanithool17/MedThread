import type { Mention } from '../types'

const CONTEXT_HIGHLIGHTS: Record<string, string> = {
  affirmed:  'bg-clinical-affirmed-bg text-clinical-affirmed rounded px-0.5',
  negated:   'bg-clinical-negated-bg text-clinical-negated rounded px-0.5',
  uncertain: 'bg-clinical-uncertain-bg text-clinical-uncertain rounded px-0.5',
  resolved:  'bg-clinical-resolved-bg text-clinical-resolved rounded px-0.5',
  unclear:   'bg-clinical-unclear-bg text-clinical-unclear rounded px-0.5',
}

interface Segment {
  text: string
  mention?: Mention
}

function buildCodePointToUtf16Map(
  text: string,
  mentions: Mention[],
): { offsets: Map<number, number>; codePointLength: number } {
  const targets = new Set<number>()
  for (const mention of mentions) {
    if (Number.isInteger(mention.char_start) && mention.char_start !== null && mention.char_start >= 0) {
      targets.add(mention.char_start)
    }
    if (Number.isInteger(mention.char_end) && mention.char_end !== null && mention.char_end >= 0) {
      targets.add(mention.char_end)
    }
  }
  const offsets = new Map<number, number>()
  let utf16Offset = 0
  let codePointOffset = 0
  for (const character of text) {
    if (targets.has(codePointOffset)) offsets.set(codePointOffset, utf16Offset)
    utf16Offset += character.length
    codePointOffset += 1
  }
  if (targets.has(codePointOffset)) offsets.set(codePointOffset, utf16Offset)
  return { offsets, codePointLength: codePointOffset }
}

function buildSegments(text: string, mentions: Mention[]): Segment[] {
  if (!mentions.length) return [{ text }]

  const candidates = mentions.filter(m =>
    m.offset_validated !== false
      && Number.isInteger(m.char_start)
      && Number.isInteger(m.char_end)
      && m.char_start !== null
      && m.char_end !== null
      && m.char_start >= 0
      && m.char_start < m.char_end,
  )
  const { offsets: codePointOffsets, codePointLength } = buildCodePointToUtf16Map(text, candidates)
  const positioned = candidates.filter(m => {
    if (m.char_end === null || m.char_start === null || m.char_end > codePointLength) return false
    const start = codePointOffsets.get(m.char_start)
    const end = codePointOffsets.get(m.char_end)
    if (start === undefined || end === undefined) return false
    return text.slice(start, end).toLowerCase()
      === (m.entity ?? m.entity_normalized).toLowerCase()
  })
  if (!positioned.length) {
    const result: Segment[] = []
    const terms = [...new Map(
      mentions.map(m => [(m.entity ?? m.entity_normalized).toLowerCase(), m]),
    ).values()].sort((a, b) =>
      (b.entity ?? b.entity_normalized).length - (a.entity ?? a.entity_normalized).length,
    )
    const escaped = terms.map(m =>
      (m.entity ?? m.entity_normalized).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'),
    )
    const pattern = new RegExp(`\\b(${escaped.join('|')})\\b`, 'gi')
    let lastIndex = 0
    let match: RegExpExecArray | null
    while ((match = pattern.exec(text)) !== null) {
      if (match.index > lastIndex) result.push({ text: text.slice(lastIndex, match.index) })
      const mention = terms.find(
        m => (m.entity ?? m.entity_normalized).toLowerCase() === match![0].toLowerCase(),
      )
      result.push({ text: match[0], mention })
      lastIndex = match.index + match[0].length
    }
    if (lastIndex < text.length) result.push({ text: text.slice(lastIndex) })
    return result.length ? result : [{ text }]
  }

  const sorted = [...positioned].sort((a, b) => (a.char_start ?? 0) - (b.char_start ?? 0))
  const segments: Segment[] = []
  let cursor = 0
  for (const m of sorted) {
    const start = codePointOffsets.get(m.char_start ?? 0) ?? cursor
    const end = codePointOffsets.get(m.char_end ?? 0) ?? start
    if (start < cursor) continue
    if (start > cursor) segments.push({ text: text.slice(cursor, start) })
    segments.push({ text: text.slice(start, end), mention: m })
    cursor = end
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor) })
  return segments
}

interface Props {
  text: string
  mentions: Mention[]
  className?: string
  selectedMention?: Mention | null
  onMentionClick?: (mention: Mention) => void
}

export default function HighlightedText({
  text,
  mentions,
  className = '',
  selectedMention,
  onMentionClick,
}: Props) {
  const segments = buildSegments(text, mentions)
  return (
    <p className={`leading-relaxed whitespace-pre-wrap ${className}`}>
      {segments.map((seg, i) =>
        seg.mention ? (
          <button
            type="button"
            key={i}
            title={`${seg.mention.entity_normalized} — ${seg.mention.context}. ${seg.mention.reason ?? ''}`}
            aria-label={`Inspect ${seg.mention.entity_normalized}, ${seg.mention.context}`}
            data-mention-start={seg.mention.char_start ?? undefined}
            data-mention-end={seg.mention.char_end ?? undefined}
            aria-pressed={selectedMention === seg.mention}
            onClick={() => onMentionClick?.(seg.mention!)}
            onKeyDown={event => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                onMentionClick?.(seg.mention!)
              }
            }}
            className={`rounded px-0.5 font-medium transition-opacity ${
              onMentionClick ? 'cursor-pointer hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-700' : 'cursor-default'
            } ${selectedMention === seg.mention ? 'ring-2 ring-teal-700' : ''} ${
              CONTEXT_HIGHLIGHTS[seg.mention.context] ?? 'bg-yellow-100'
            }`}
          >
            {seg.text}
          </button>
        ) : (
          <span key={i}>{seg.text}</span>
        ),
      )}
    </p>
  )
}
