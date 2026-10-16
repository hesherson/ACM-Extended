# B286: unconscious AI recurring work

Version **1.2.4.1**, build **B286**, network protocol **2**.
Baseline: B285, `90baff5acf73cdd9de09277aa3b8588b1bfcf75f`.

The reported case is a local VR mission with CBA, ACE, RHS, ACM Extended and CUP: shooting more AI unconscious increases recurring one-second frame-time spikes. There was no useful RPT error. The report did not establish which installed build or handler dominates the hitch. Source inspection and SQF-VM work counts identify avoidable work; they do not reproduce native frame times.

## Changes

- Discovery and preoxygenation retain their one-second cadence and order in one unscheduled callback. Identical aircraft-support rays share an invocation-local sample keyed by patient and ray endpoints. Ten eligible patients require 30 raw floor rays across these two updates instead of 60. The sample ends when the callback returns. Aircraft classification, model transforms and motion rejection remain live, and configured oxygen condition code invalidates the sample scope before it runs. No long-lived negative geometry cache or global aircraft scan is added.
- Native coagulation callbacks check cleanup and the next-attempt deadline before reading TXA kinetics. The actual attempt reads current platelets, clot strength and medication effect; its interval and clotting rules are unchanged.
- Untreated native vital updates skip three unused medication-map copies. Toxicity also exits before config and medication-count lookups when the canonical medication history is empty. Later admissions still use native onset and the existing family/generation gates.
- Completed clinical passes retire recovered patients from the shared clinical registry using the same live indication used by owner enrollment and late-state recovery. Historical maps and a resolved PTX tuple alone do not keep four-times-per-second maintenance alive. Ongoing drugs, devices, wounds and finite recovery state retain their worker until their actual cleanup completes. Retirement does not erase patient history or medical state.
- Re-entry after a dormant interval rebaselines only the elapsed clocks owned by clinical maintenance. Its first resumed pass has zero elapsed time, then subsequent active passes use their normal measured delta. A newly admitted dose cannot inherit up to five seconds of idle catch-up. Direct circulation/infusion/PTX entry and repeated registration of an already active patient follow the same rule; independent flight, preoxygenation and NRB clocks are unchanged.

AI protection, native vital cadence, medical update rates and treatment mechanics remain active. B285's syringe delivery journal and protocol-2 ownership fences remain in this candidate. Medmash stays on `dev`; the release still contains the original 14 addons.

## Measurement and acceptance

`ACME_fnc_performanceDiagnostics` is an opt-in local capture of every observed frame and selected inclusive handler timings. It buffers aggregate data for at most 600 seconds and installs no observer until explicitly started. The capture records no patient identities and produces no per-frame log or network traffic. Native vitals total timing includes its synchronous extension event; that event is also measured separately.

Follow [the capture procedure](../maintenance/B286-performance-capture.md) for identical fixed-population VR windows with 0, 1, 5 and 10 unconscious AI, and a recovery window. The baseline needs the same frame observer loaded into the test mission; its absent named instrumentation must not be interpreted as zero handler cost. Compare runs with diagnostics disabled as well.

Automated checks verify executed SQF decisions, work counts, cleanup, recovery and bounded diagnostic storage against explicit engine boundaries. They cannot certify RHS/CUP engine behavior, third-party event handlers, aircraft collision, native scheduling or an FPS improvement. The one-second symptom remains subject to an in-game before/after capture; this candidate must not be described as a confirmed native hitch fix before that evidence exists.

Use `tools/Deploy-ACME-B286.ps1` for the existing journalled local build/deployment workflow. PR #31 remains draft and unmerged pending native acceptance. All players, servers and headless clients must use the same complete build.
