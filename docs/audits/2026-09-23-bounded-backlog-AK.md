# Bounded AK: Body Map flush uses its displayed patient

Parent: `3ac65fedf7106a53be1f3703933d39e724c9de9a` (AI-AJ).

Body Map artwork and skSiteClick validate the display-local ReturnPatient (with the existing self-view fallback). skFlushSite instead read mutable shared ACME_SK_Patient. A cleared global could flush the medic rather than the displayed casualty; a different shared patient with access could receive the request instead. A missing display did not prevent dispatch.

Only skFlushSite changes runtime. Require an open draw display and use its same patient snapshot/self fallback as the artwork and exact site-click validation. No shared patient overwrite, new state, timer, handler, network event, access/distance rule, dose calculation or inventory algorithm is introduced. The unchanged salineFlush worker retains exact-site, stock, locality and same-vehicle distance checks. No patient-life restriction is added.

Twenty-three new cases execute actual skSiteClick, skFlushSite and salineFlush. On unchanged source: ten fail and thirteen pass. Candidate: all pass. Cases cover IV/IO, cleared/different/matching shared patient, live/dead casualty flags, self view, missing display, exact-access rejection, stock/locality/distance rejection, same-vehicle exception, remaining selection, request/log patient, and no mutation of stored syringes or a staged medication target.

These tests record inventory removal, medicationRequest and activity boundaries. They do not deliver parked line medications, use live inventory or test actual controls/networking. The actual patient death engine state is not simulated. Old-control events from a replaced dialog, provider changes within a live display, general site-click busy gating and same-context lifecycle round trips remain outside this narrow correction. No original H entry closes in AK. No live Arma or stable-release approval.
