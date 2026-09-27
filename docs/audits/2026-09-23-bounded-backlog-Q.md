# Bounded Q: initial Elevate Head retry placement ownership

Parent: `ee3f54143c5be163727f4c8b575c520be180f640` (O-P).

The initial Elevate Head normalization retry wrote facing before re-entering startup. Rejected or duplicate retries could therefore change the cached side of a later placement; a changed inactive placement could still run startup/gear work. Capture the existing placement token before normalization and reject mismatch before recursive startup. Remove the duplicate delayed facing write: normal startup already writes front after owner, life, active-placement and eligibility validation.

Only headElevateStart changes runtime. Roll dispatch, physical/fallback branches, delay, support handling, patient/provider choreography, owner dispatch and clinical rules remain. No new state key, timer, event handler or network operation. The one affected preservation hash is reviewed.

Twenty full-startup SQF cases: unchanged O-P {'failed': 16, 'passed': 4}; candidate all twenty pass. They cover physical/fallback normalization, replacement and rejection, locality/life/medic loss, duplicate delivery, current auto/manual flags and supersession by another actual startup call. Engine boundaries are fixtures, not RTM rendering or inventory transactions.

H452 retains its identity but checks actual retry token capture, validation and no pre-validation facing write, plus the carrier callback's existing guards, instead of counting spellings. Index 107 to 106. No unreviewed historical test body or H entry changes.

Empty-token ABA/reuse, owner-away-and-back with the same token, concurrent pending starts before either places the patient, later physical-orientation changes within the same retry and live multiplayer behavior remain open. No complete lifecycle redesign or stable-release approval.
