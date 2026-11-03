# B310 candidate — deployed equipment persistence

Version 1.2.4.1, protocol 5. Based on B309; includes earlier equipment/blood fixes.

- Added server-only portable world capture, schema validation, final capture validation and startup import for deployed Pro, LS, ACCUVAC and Ventway.
- Preserves ASL placement/orientation, manual placement, durable patient references, observation connections/power and Pro/LS pairing.
- Validates the whole import before creating objects; failed partial allocation rolls back. Duplicate imports reuse existing objects; retired objects cannot be respawned by replay.
- Rebuilds Ventway custody from matching restored clinical state, including original supplier/recovery/vehicle paths. No additional inventory grant or debit.
- Restored LS units are disarmed, with pacing/metronome stopped. Browser therapy state and cached readings are discarded.
- Equipment transactions now participate in server checkpoint readiness. Patient persistence fences protect setup/pickup admissions.
- Ventway model swaps preserve durable identity and retain their old prop if replacement allocation fails.

See `B310-world-equipment-persistence.md` for required mission-adapter ordering and limits. No automatic mission backend is installed. Native multiplayer/Windows deployment acceptance remains pending. The Linux integration candidate retains MLOD models; use the source installer for a normal native Windows release.
