# B281: altitude exposure and walkable aircraft

Version **1.2.4.1 / B281**, network protocol **1**. Baseline: B280,
`90e780fded0d0fafe248cbd085ecd8ab34433c32`.

## Behavior

Native oxygenation reads current exposure for the patient being updated, including
untreated players. A separate owner-local flight registry samples pressure and
maneuver effects without enrolling healthy flight occupants into general clinical
maintenance. Existing slow owner discovery supplies the registry; the hot worker
does not scan every unit. Untouched AI activate ACE's existing vitals worker only
when actual exposure lowers their oxygen ceiling.

Altitude contributes a ceiling to native oxygenation. It does not overwrite the
shared clinical oxygen target. Descent, a teleport to ground, supplied oxygen and
the Flight physiology switch therefore remove their own contribution while
preserving lung injury, suction, ventilation, medication and scenario effects.
Oxygen saturation still evolves through native vitals; a position change does not
directly set a healthy player's saturation or force unconsciousness.

Ambient pressure uses finite standard-atmosphere layers through the stratosphere
and a bounded numerical tail above them. It no longer plateaus at 11 km or a
pressure ratio of 0.2. Low oxygen availability can continue below the former 78%
target floor. Personal oxygen raises delivered FiO2; it does not pressurize the
body or protect trapped gas from pressure changes. At extreme altitude, oxygen
alone is not a pressure suit.

Terrain datum, live elevation overrides and ACE's configured map elevation use
one exposure source. Explicit datum mode keeps its raw-ASL-minus-datum contract.
Only terrain sampling is cached; live configuration changes are re-evaluated.
Pressure history is local to the current owner and clinical epoch. Initial samples,
ownership changes, resets and long gaps establish a new baseline rather than
replaying unseen travel into pneumothorax damage.

Flight chill measures height above terrain directly rather than subtracting
incompatible position datums. The same climb therefore produces the same added
cooling over low ground and a high plateau, and Flight physiology OFF disables
that additional cooling.

## Equipment and cabin compatibility

No aircraft or equipment classname whitelist is used. Oxygen equipment follows
ACE's `ace_medical_vitals_oxygenSupply` config condition, evaluated on the actual
patient. An equipment provider can alternatively maintain the patient's
`ACME_oxygenSupply` Boolean or owner-local condition. The provider remains
responsible for its supply, regulator, fuel/oxygen inventory and exhaustion state.
An ordinary cosmetic mask does not imply an oxygen source.

Aircraft pressure requires explicit object or inherited config metadata:

| Field | Meaning |
| --- | --- |
| `ACME_cabinPressureRatio` | Ambient-relative sea-level pressure ratio from 0 to 1. A live value of 0 vents back to outside ambient pressure. |
| `ACME_cabinAltitude` | Cabin-equivalent altitude in metres, using the same pressure curve. |

Live object values take precedence over static config. Cabin metadata applies
only in the identified aircraft cabin context; a supported exterior roof/wing
does not by itself imply pressurization. Geometry is a conservative enclosure
check, not an engine API proving an airtight cabin. A pressure controller must
publish actual depressurization when a ramp/door is opened; names and animation
phases cannot establish pressure across arbitrary mods.

## Walkable-aircraft containment

Before native unconsciousness begins, the owner checks nearby floor contact in
separate ROADWAY, GEOM and PHYSX LOD queries. The supporting object/proxy must
resolve to a live `Air` vehicle. This works without an altitude cutoff or aircraft
classname list. Mere proximity, bounding-box containment and freefall are not
floor contact. ROADWAY support is available from Arma 2.08, below the project's
2.18 minimum; the implementation uses the original unbatched command syntax.

A supported unconscious casualty receives a generation-checked owner-local
floor lease. It follows the captured aircraft-relative model root while retaining
ACE's medical flag and native incapacitated state. It does not disable collision,
alter mass, grant damage immunity, attach the patient or move them to a cargo seat.
Wake, death, aircraft loss, teleport/ejection, native cargo entry, dragging/carrying,
stronger position controllers, clinical reset and ownership changes retire or
adopt the exact lease. Ground and freefall unconsciousness retain the native path.

Arma must still establish whether moving the native model root keeps the active
ragdoll skeleton above every third-party aircraft floor, without jitter or banking
artifacts. Command-boundary tests cannot establish that engine behavior.

## Validation and native acceptance

Automated coverage executes production pressure, exposure, oxygen ceiling,
registration, clinical cleanup and containment decision paths with explicit
fixtures at native engine boundaries. B280 case identities remain required.
Strict HEMTT, original CLI gates, complete CI and signed-package checks are
required for the published candidate. Native acceptance remains a separate gate:

1. On a dedicated server, teleport ten previously untouched players to altitude,
   then repeat with previously treated players. Confirm identical exposure inputs
   for equivalent equipment, with native physiological variation in collapse time.
2. Repeat below 500 m, at 10,000 m and above 11,000 m; descend or teleport to ground,
   disable/re-enable Flight physiology, and repeat after JIP/locality changes.
3. Compare room air, declared HALO oxygen, exhausted supplies, a cosmetic mask,
   a metered NRB and effective ventilator oxygen. Verify lung/shunt and suction
   effects still apply. Check explicit cabin pressure and live depressurization.
4. Use seated cargo and a walkable interior in different aircraft mods. Test
   native unconsciousness at ground and flight altitude, banks/climbs, aircraft
   teleport, patient teleport, wake, carry/drag, cargo entry, death, full heal and
   deleted aircraft. Confirm no floor penetration or obsolete floor following.
5. Jump normally and while already unconscious. Confirm unsupported/freefall
   players are never pulled back into an aircraft.

## Deployment

Close Arma and local servers. Fetch the exact published B281 commit into the
existing `F:\ACM-Extended` checkout and run `tools\Deploy-ACME-B281.ps1` through
PowerShell with execution-policy bypass. The helper performs strict validation,
native release packaging and journalled deployment. Confirm **1.2.4.1 / B281**.
Server, clients and headless clients must use the same complete build.
