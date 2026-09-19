# ACM Extended 1.2.2: provider hold synchronization

## Problem

Feel Pulse and Auscultate Chest share the ACME_StethoscopeWork animation and hold at the existing 0.421-second sample. The provider's controller froze locally, but a remote observer discarded its hold handler whenever its animation state differed. A delayed engine animation update could therefore release that observer permanently while the provider remained frozen and had no reason to send another correction.

Repeated hold packets also removed and recreated the observer handler, briefly restoring speed and seeking again. The owner shortcut accepted a delayed hold before checking whether its episode had already ended.

## Changes

- Keep the observer handler active until the episode ends, the provider dies or becomes unconscious, enters a vehicle, is deleted or changes owner.
- Repair animation state or phase drift on the observer using the existing held sample. Corrections are limited to once every 0.25 seconds and occur only when the visible state or phase has drifted.
- Correct a speed reset without restarting the animation. Duplicate hold packets preserve the current observer handler.
- Validate the episode before processing an owner echo, so a late hold cannot freeze a cancelled or newer action.
- Preserve the owner animation, 0.421-second hold, crouch transitions, cancellation and Direct Pressure handoff. No patient positioning, audio or minigame controls changed. Version remains 1.2.2.

The shared receiver also serves the existing chest inspection and roll holds; their timing and lifecycle remain unchanged.

## Validation

Both main and dev passed 18 checks: 16 SQF-VM execution cases against the actual receiver, strict HEMTT 1.21.0 diagnostics and complete addon config compilation.

Execution cases cover delayed animation entry, state and phase drift, speed resets, duplicate packets, cancellation, late owner echoes, old release packets during a new hold, joining-player event ordering, death, unconsciousness, vehicle entry, deletion and ownership transfer. Native animation and network operations are simulated; the production control flow runs in SQF-VM.

Rendered animation and actual network timing still require Arma multiplayer verification. With two updated clients, watch the other provider perform Feel Pulse and Auscultate Chest, then cancel and repeat. Confirm the held frame stays still and the provider returns to a movable unarmed crouch. Repeat with two providers treating separate patients and with a client joining during a hold.

## References

The existing protocol uses CBA's [global events for joining players](https://github.com/CBATeam/CBA_A3/blob/master/addons/events/fnc_globalEventJIP.sqf) and [event removal](https://github.com/CBATeam/CBA_A3/blob/master/addons/events/fnc_removeGlobalEventJIP.sqf). Episode checks prevent a queued hold from restarting an action after its release.
