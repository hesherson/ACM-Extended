# Residual backlog BD: focused test drift and test-environment closure

Parent checkpoint: `4d012d486d9e999e3b431e45d845c87ecab335f8` (residual BC).

BD resolves the failures observed while rerunning the focused residual suite and makes the broad Python test collection reproducible.

## Focused failures

- Chest-seal workspace readiness still uses the shared server clock. The current implementation writes `ACME_CS_ProcedureReadyAt` as either `serverTime` or `serverTime + _rollTime + 0.08` after the carrier transaction. The test still expected the retired `_readyDelay` variable and was updated to protect the current contract.
- FBTK full-bag return still snaps a bag within tolerance to its nominal volume. The implementation now sanitizes and clamps `_tol` to 0–5 mL before comparing `_remainingVolume >= ((_volume - _tol) max 0)`. The test still expected the retired local name `_fullTolerance` and was updated to protect the bounded tolerance behavior rather than a historical identifier.

No runtime SQF changed in either case.

## Test environment

The broad addon suite stopped during collection because the local Python environment did not contain dependencies already imported by existing tests:

- `numpy` for PAA/IV geometry tests.
- `soundfile` for syringe audio assertions.
- `pytest` is included so the manifest is self-contained for a fresh test environment.

`tools/requirements-test.txt` is now the canonical install list for the Python addon test suite.

BD is test/audit/environment-only. It does not change gameplay, config, networking, treatment state, assets, or release packaging.
