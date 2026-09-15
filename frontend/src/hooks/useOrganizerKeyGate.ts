import { useCallback, useState } from 'react'

import { UnauthorizedError } from '../api'

/**
 * Tracks whether the last organizer/staff request was refused for lack of a valid key.
 * `guard(error)` returns true when it handled the error (so callers skip their own error UI);
 * `version` changes after a key is saved so data-loading effects can rerun.
 */
export function useOrganizerKeyGate() {
  const [needsKey, setNeedsKey] = useState(false)
  const [version, setVersion] = useState(0)

  // Stable identities so effects can list them as dependencies without rerunning every render.
  const guard = useCallback((error: unknown): boolean => {
    if (error instanceof UnauthorizedError) {
      setNeedsKey(true)
      return true
    }
    return false
  }, [])

  const saved = useCallback(() => {
    setNeedsKey(false)
    setVersion((current) => current + 1)
  }, [])

  return { needsKey, version, guard, saved }
}
