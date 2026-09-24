# Bounded C: Direct Pressure current ownership and handoffs

Pinned parent: `7c031508124ea1b431207faf3bda0eeb7e2fbbdf`. This is test-contract work, not a gameplay patch.
No SQF, configuration, asset, animation timing, input binding, medication or physiology file changes.

## Original entries resolved

H131, H372 and H373 retain their original pytest function identities. The superseded assumptions were an old medic entry/end animation pair, torso-only ownership of the global continuous-action gate, and inline torso cancellation in BP/Hang Bag wrappers.

Current runtime uses the connected pressure hold with priority-one entry. A narrow priority-two exit is retained only when the provider is visibly stuck in the pressure hold; another maneuver blocks the exit. Torso, limb/head and self pressure do not acquire ACM's exclusive continuous-action controller. Compatible stationary work can yield/reapply the clinical marker and shift the clot timers by the yielded duration. A successful BVM handoff deliberately ends the provider's pressure episode; the existing integration tests continue to verify that behavior. The obsolete blanket non-cancellation interpretation is not restored.

## Evidence

The three original identities fail before this review and pass afterward. Twenty-four new cases execute the actual pressure entry/tick/stop/BP-wrapper code with the existing explicit engine boundaries, plus negative source-contract checks. Cases cover all four region routes, exact-once marker yield/resume, no clot credit during pause, exit priorities and competing-action protection, and intact native BP payloads. Existing native BVM/DP integration tests remain included. No input binding is changed or newly certified by these checks. No Arma animation or network transport is rendered.

The new cases pass against unchanged runtime, showing that these three historical assertions were stale rather than proving three new gameplay defects. The old function names remain for historical identity tracking. Assertions inspect executable tokens, not comment phrases. The 146-entry original source-contract index becomes 143. Its other entries remain verbatim. No skip, xfail or production workaround is introduced.
