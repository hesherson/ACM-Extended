# Local candidate AO: confirm the patient actually shown by the Body Map

Base: published AK-AL `8df66dfb5f9701c960bf352ba1f41d16dcd77fc8`, with the prior AM-AN local candidate retained. This is not a new published or full-checkout-validated checkpoint.

## Defect and narrowly scoped change

The site click and Body Map use the injected display's ReturnPatient snapshot (or self-view fallback). Confirmation preferred a non-null shared ACME_SK_Patient instead. A conflicting shared patient could therefore start a normal push or reach the Hardcore start delegate for a different casualty. Normal deferred validation also ignored a changed displayed patient as long as its shared patient stayed unchanged.

Only skConfirmInjection changes runtime in AO. Reject a non-null shared patient that disagrees with the displayed patient before reading or mutating the pending target and before either normal setup or Hardcore delegation. Normal callbacks additionally require their captured patient to remain the displayed patient. Keep the existing shared-patient, provider, workspace, busy, page and job-identity checks. Reject disagreement rather than silently changing the chosen patient. This does not alter the existing empty/self-view initialization behavior.

No timing, dose, inventory, new state key, timer, PFH or network operation is added. A matching Hardcore request still delegates to its existing worker; that worker is not edited. Other direct calls that bypass confirmation are not covered by this guard.

## Executed controls

23 full-confirmation/callback cases reproduce 12 failures and 11 passing controls against the original confirmation code. All pass after the guard. Coverage includes IV, IO, IM, conflicting self/other references, rejection before Hardcore delegation, changed displayed patient at settle/completion, cleared-shared-value fallback, explicit self treatment, existing shared-patient change rejection, duplicate completion and missing display.

The prior replacement-dialog test fixture now supplies the ReturnPatient snapshot that real skInject sets on every injected display. Only that setup property and its comment change; every prior assertion is retained. The separate regression selection includes prior normal-push, workspace, teardown, site-click and measured-epinephrine checks.

## Limits

These tests record the authoritative handoff using explicit UI/scheduler delegates. They do not establish real drug delivery, live player input, physical inventory or network transport. They do not handle a patient change away and back between checks, changes inside an already-running handoff, external generation resets, direct worker callers, or every possible patient-field writer. No clinical calibration is claimed. No H entry closes due to AO alone.

All available AK-AL source/assets were verified against its published SHA256 manifest before editing. 1,239 binary/nonexported files remain unavailable locally. HEMTT can perform its source check, but this is not a complete-package build or release acceptance. GitHub publication and live Arma validation remain outstanding.
