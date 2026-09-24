# Bounded D: EMMA identity and separate sedation-debug columns

Builds on bounded C from published A-B checkpoint 7c031508. Test-contract changes only.
No runtime, artwork, medication model or rendering layout is changed.

## Original entries resolved

H428 expected the EMMA attachment key inline in every caller. The actual attachment and removal callers delegate to emmaIGelStateCommit, which retains attachment status, timestamp and provider UID/name. Eligibility and the HUD still read the same state key. The revised contract follows those actual calls and reads instead of demanding duplicate inline writes.

H436 expected full medication-name literals in the old debug layout. The current clinical page takes the six-field sedationComponents result and places Ket/Prop and Mid/Fent in distinct columns. The revised contract checks the actual positional binding and columns instead of requiring retired captions.

## Evidence and limits

Twenty-two new cases execute the actual EMMA eligibility, identity writer, contact, attach and detach functions, or the exact clinical debug row-building block. EMMA controls cover ETT/i-gel, live/dead patients, transfer from own BVM, later independent own-BVM preservation, rejection without identity writes, and distance/same-vehicle boundaries. Debug cases supply distinct six-field component values and verify which values reach each row. This does not execute drug kinetics, calibrate dosing, render text, simulate inventory transactions or certify multiplayer transport.

The new cases pass against unchanged runtime. The two retained original identities fail before the test-contract update and pass afterward. Together with C, 157 local focused tests pass, including native BVM/DP integration and the complete preservation module. The original source-contract index moves 143 to 141; all other entries remain unchanged. No skip or xfail is introduced. No live Arma, dedicated server or stable-release validation is claimed.

## Complete-checkout validation

Focused: {'passed': 157}. Full addon before: {'passed': 3746, 'failed': 174, 'skipped': 4}. Full addon after: {'passed': 3797, 'failed': 169, 'skipped': 4}. Exactly five retained historical identities move from failing to passing; 46 new cases pass. No newly failing or missing prior identities. Both full addon commands return 1 and retain the same four skips. Full-project HEMTT check returns 0. All 4045 other existing tracked files retain their complete-checkout SHA256; runtime/configuration/assets are unchanged. Root preservation tests are included, but the entire root-tools suite was not rerun. No live Arma or release approval. Evidence is retained by this workflow run.
