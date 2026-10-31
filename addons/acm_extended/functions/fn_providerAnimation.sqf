/* Resolve provider-only theatre without raising a prone medic. Never use this for patient repositioning.
 * A controller may pass its captured entry posture so a delayed callback cannot turn an earlier prone action
 * into a kneeling one. CPR owns its separate, intentionally forced posture and does not use this resolver.
 */
params [["_medic", objNull, [objNull]], ["_requested", "", [""]], ["_enteredProne", false, [false]]];
if (isNull _medic || {_requested == ""}) exitWith {_requested};
// Custom prone holds and interpolations can report an undefined engine stance.
// A prone animation is positive evidence; a prone-to-kneel transition is not.
private _current = toLowerANSI animationState _medic;
private _proneState = ((_current find "ppne") >= 0 || {(_current find "prone") >= 0})
    && {(_current find "pknl") < 0};
if (!_enteredProne && {stance _medic != "PRONE"} && {!_proneState}) exitWith {_requested};
private _name = toLowerANSI _requested;
if ((_name find "ppne") >= 0 && {(_name find "pknl") < 0} || {(_name find "prone") >= 0}) exitWith {_requested};
// Rest/stance transitions have no work phase. Return directly to a movable prone idle.
if (((_name find "amov") == 0 || {(_name find "aidl") == 0})
    && {(_name find "putdown") < 0} && {(_name find "pickup") < 0}
    && {(_name find "ainv") < 0}) exitWith {"AmovPpneMstpSnonWnonDnon"};
// ACM ships this supported prone medical state. Specialty kneeling RTMs have no equivalent authored prone
// choreography; retain a prone medical hold instead of applying those incompatible kneeling skeleton poses.
"ACM_ProneContinuous"
