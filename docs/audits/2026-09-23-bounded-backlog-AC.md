# Bounded AC: normal staged-push callback ownership

Parent: `bf745808d8e92c56af211a1b32d315174a155004` (AA-AB).

Normal display-bound pushes looked up the current draw dialog again in both deferred callbacks. The completion then handed off through the current global patient/provider. Closing and reopening, changing the patient/page, or starting a replacement push could redirect an old callback, clear new locks, or repeat the medication handoff. The plunger PFH could also clear a newer PFH handle. Confirmation validated a ReturnPatient fallback that was not carried into skInjectSite.

Only skConfirmInjection and skClose change runtime. A normal push captures its display/provider/patient/stable syringe ID and a display-local generation. Its two existing delays and plunger PFH validate that job; completion retires it before the authoritative handoff. The validated fallback patient is made explicit at the existing skInjectSite boundary. Unload cancels only the originating normal push and releases its locks/PFH. Persistent Hardcore flow retains its existing delegation and is not cancelled by these callbacks. The existing initial 0.14-second settle, default three-second IM/blank duration, typed vascular durations and smoothstep stroke remain.

This introduces a display-local generation and one UI-local job record. No new timer, PFH, network event, dose/kinetics code or inventory transaction is added. The existing authoritative skInjectSite path still performs access, distance, route and inventory validation; it was not edited.

37 full-source execution checks run with explicit controls, patient/provider identities and captured callbacks. On unchanged AA-AB runtime: 21 fail and 16 pass. All 37 pass after correction. Coverage includes start/commit context changes, normal replacement jobs, duplicate completion, closed dialogs, missing/reordered stable IDs, return-patient fallback, IV/IO/IM durations, plunger endpoints and Hardcore noninterference. Existing duration, syringe-identity and UI-default tests remain included.

The tests record the skInjectSite handoff rather than administering drugs, performing engine inventory work or transmitting events. They do not certify actual Arma dialog scheduling, display-handle reuse, arbitrary external job-state resets, live pixels, same-context patient/page round trips, changing a syringe's contents under the same ID, all epinephrine-dose UI paths or general stale skClose ownership. No new patient-life restriction is added. No live Arma or stable-release approval. This runtime fix alone closes no original H entry.
