# Bounded G: medication stock columns and preparation refresh

Pinned parent: `99da8584547c083c8a882c7786558885d6b8a5f7`. Test-contract changes only. Runtime, configuration, assets,
animation timing, medication behavior and all protected snapshot digests remain unchanged.

## Original identities resolved

H170, H171 and H172 demanded a removed header and a combined contents/count label.
The later three-column renderer intentionally uses one external Medication/Contents/Vials
header plus separate row controls. The current selected-row tick updates Contents and Vials
independently through the existing non-debiting preview path.

H430 demanded obsolete Drawn-list IDs. Current preparation hides the existing flush sources
and retains the scrolling medication tally. H437 demanded inline volume reads in a repaint
function and a row-click handler that now delegate to preview/session helpers instead.
The available-medication check in the preparation opener still retains its volume lookup.

All five pytest identities and all unreviewed test bodies are retained. No failure is waived,
skipped or marked xfail. The original source-contract index moves 132 to 127.

## Evidence and limits

32 new cases execute the actual header, stock-info, selected-row refresh and preparation
source-hiding blocks, plus negative source-contract controls. Cases cover idempotent header
creation, a single caption displacement, header visibility, bound/open stock, partial and zero
stock, count padding, compound/draw reservations, nonselected rows and a missing count control.
Existing source-row, physical-vial and preparation execution modules remain in the selection.
The new cases pass on unchanged runtime; these are stale contracts, not five gameplay fixes.

Engine controls, font metrics, localization and inventory-preview boundaries are explicit
fixtures. No live pixels, mouse hit-testing, real font fitting, UI scheduling, network ordering
or inventory debits are certified. All full-suite results are recorded in the G-H evidence and
bounded H report. No live Arma, dedicated server or stable-release approval.
