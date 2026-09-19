# ACM Extended 1.2.2: repeat seal burping and Carry Assist release

## Changes

- Traumatic and thoracostomy seals share one six-second cooldown per patient across providers. The first burp is immediately available, and each accepted burp starts the interval. Readiness uses the synchronized engine clock instead of comparing separate client and patient-owner CBA mission clocks.
- Scrolling a fully lifted corner after cooldown starts another five-notch peel cycle. Moving the cursor away or closing the panel is no longer necessary to rearm it. Reverse scrolling still lays the corner flat immediately during cooldown. A resting lifted seal never triggers another treatment automatically.
- The patient owner commits the cooldown before relief, logging or the treatment gesture. A competing provider or rapid wheel input cannot repeat those effects during the interval.
- Both seal types remain usable after patient death. Handling and logging continue, while pressure relief and lung physiology workers remain stopped.
- Carry Assist handles the real left mouse button and Escape events in addition to CBA input. Escape is consumed even if CBA already requested cancellation, preventing the pause menu from interrupting the release. Cleanup removes both input paths, releases the patient reservation and requests the native movable crouch.
- Input handlers carry their original action generation, so a delayed callback cannot cancel a replacement maneuver. The shared crouched and prone continuous holding states now have explicit native exit connections.

Version remains 1.2.2. The experimental drag handle remains excluded from release builds.

## Validation

Both branches passed 124 focused checks, including strict HEMTT validation, with one optional development package test skipped. Each branch compiled its configs and SQF and built 14 release PBOs using `hemtt release --no-bin --no-sign --no-archive`. Release packages still exclude the experimental drag handle. Windows binarization and signing were not run here.

Sixteen new SQF execution tests cover repeated burps on the same corner, both scroll directions, the 5.999/6-second boundary, lowering during cooldown, shared provider and seal cooldowns, client clock offsets, ownership, clinical episode replacement and dead patients. Carry Assist tests call the actual captured mouse and keyboard callbacks, including Escape after CBA cancellation, repeated starts, stale callbacks, unrelated buttons and a missing display fallback.

The tests reproduce both seals remaining latched with the previous wheel handlers. They simulate native UI, animation, networking and physiology effects, so actual Arma multiplayer playback still needs verification.

Update every client and the server, then restart Arma and the mission. On both seal types, lift a corner, wait six seconds, then scroll to lift it again while keeping the cursor on the seal. Also lower the corner during cooldown and repeat after the interval. Start Carry Assist, cancel with left click, repeat and cancel with Escape, then move and begin another treatment.
