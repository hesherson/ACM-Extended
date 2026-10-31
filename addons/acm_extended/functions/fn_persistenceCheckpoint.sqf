/* Compatibility alias. This is an owner-local equipment checkpoint. For a
 * coordinated server save, acquire/validate/release persistenceBarrier and
 * freeze external/native gameplay through the mission's own save adapter. */
_this call ACME_fnc_persistenceLocalCheckpoint
