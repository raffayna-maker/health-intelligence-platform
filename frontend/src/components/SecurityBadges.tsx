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
  if (verdict === 'pass' || verdict === 'skip' || verdict === 'detected') return 'badge-pass'
  if (verdict === 'block') return 'badge-block'
  return 'badge-error'
}

// Map internal verdicts to user-friendly display text
function displayVerdict(verdict?: string): string {
  if (!verdict) return 'unknown'
  if (verdict === 'detected') return 'pass'
  return verdict
}

function isPassVerdict(verdict?: string): boolean {
  return !verdict || verdict === 'pass' || verdict === 'skip' || verdict === 'detected'
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
  // Show badges even when all verdicts are pass (for monitoring views)
  showOnPass?: boolean
}

export default function SecurityBadges({ toolResults, hlVerdict, aimVerdict, hlScanTimeMs, aimScanTimeMs, compact, showOnPass }: SecurityBadgesProps) {
  // Prefer dynamic tool_results if available
  if (toolResults && Object.keys(toolResults).length > 0) {
    // Hide if all verdicts are pass and showOnPass is not set
    if (!showOnPass && Object.values(toolResults).every(r => isPassVerdict(r.verdict))) {
      return null
    }
    return (
      <div className="flex gap-2 flex-wrap">
        {Object.entries(toolResults).map(([name, result]) => (
          <span key={name} className={badgeClass(result.verdict)}>
            {getLabel(name)}: {displayVerdict(result.verdict)}
            {!compact && result.scan_time_ms ? ` (${result.scan_time_ms}ms)` : ''}
          </span>
        ))}
      </div>
    )
  }

  // Legacy fallback — show HL/AIM badges from old data
  const hasLegacy = hlVerdict || aimVerdict
  if (!hasLegacy) return null

  // Hide if all legacy verdicts are pass and showOnPass is not set
  if (!showOnPass && isPassVerdict(hlVerdict) && isPassVerdict(aimVerdict)) {
    return null
  }

  return (
    <div className="flex gap-2 flex-wrap">
      {hlVerdict && (
        <span className={badgeClass(hlVerdict)}>
          HL: {displayVerdict(hlVerdict)}{!compact && hlScanTimeMs ? ` (${hlScanTimeMs}ms)` : ''}
        </span>
      )}
      {aimVerdict && (
        <span className={badgeClass(aimVerdict)}>
          AIM: {displayVerdict(aimVerdict)}{!compact && aimScanTimeMs ? ` (${aimScanTimeMs}ms)` : ''}
        </span>
      )}
    </div>
  )
}
