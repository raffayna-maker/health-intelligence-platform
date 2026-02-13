import { ToolResult } from '../types'

const TOOL_LABELS: Record<string, string> = {
  hidden_layer: 'HL',
  promptfoo: 'PF',
}

function getLabel(toolName: string): string {
  return TOOL_LABELS[toolName] || toolName.split('_').map(w => w[0]?.toUpperCase()).join('')
}

function badgeClass(verdict?: string): string {
  if (!verdict) return 'badge-error'
  if (verdict === 'pass' || verdict === 'skip') return 'badge-pass'
  if (verdict === 'block') return 'badge-block'
  return 'badge-error'
}

interface SecurityBadgesProps {
  toolResults?: Record<string, ToolResult> | null
  // Legacy fallback fields
  hlVerdict?: string
  hlScanTimeMs?: number
  aimVerdict?: string
  aimScanTimeMs?: number
  // Compact mode hides scan times
  compact?: boolean
}

export default function SecurityBadges({ toolResults, hlVerdict, aimVerdict, hlScanTimeMs, aimScanTimeMs, compact }: SecurityBadgesProps) {
  // Prefer dynamic tool_results if available
  if (toolResults && Object.keys(toolResults).length > 0) {
    return (
      <div className="flex gap-2 flex-wrap">
        {Object.entries(toolResults).map(([name, result]) => (
          <span key={name} className={badgeClass(result.verdict)}>
            {getLabel(name)}: {result.verdict}
            {!compact && result.scan_time_ms ? ` (${result.scan_time_ms}ms)` : ''}
          </span>
        ))}
      </div>
    )
  }

  // Legacy fallback — show HL/AIM badges from old data
  const hasLegacy = hlVerdict || aimVerdict
  if (!hasLegacy) return null

  return (
    <div className="flex gap-2 flex-wrap">
      {hlVerdict && (
        <span className={badgeClass(hlVerdict)}>
          HL: {hlVerdict}{!compact && hlScanTimeMs ? ` (${hlScanTimeMs}ms)` : ''}
        </span>
      )}
      {aimVerdict && (
        <span className={badgeClass(aimVerdict)}>
          AIM: {aimVerdict}{!compact && aimScanTimeMs ? ` (${aimScanTimeMs}ms)` : ''}
        </span>
      )}
    </div>
  )
}
