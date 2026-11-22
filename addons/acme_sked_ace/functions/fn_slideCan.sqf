/*
 * May this thing slide down a slope by itself (fn_slideLocal.sqf), and from what angle?
 * A casualty who is not awake, lying free on the ground; or a litter with a casualty strapped into it that
 * nobody holds, lifts or drags. Only on the terrain itself: on a floor, a road bridge or a rock nothing slides.
 * Arguments: 0: unit or litter.
 * Returns: the angle of the ground (degrees) from which it slides, or -1 when it must not slide <NUMBER>.
 */
params ["_thing"];
if (isNull _thing || {!local _thing} || {!isNull attachedTo _thing} || {!isNull objectParent _thing}) exitWith {-1};
private _angle = missionNamespace getVariable ["acme_slide_angle", 30];
private _ok = if (_thing isKindOf "CAManBase") then {
    alive _thing && {_thing getVariable ["ACE_isUnconscious", false]}
    && {isNull (_thing getVariable ["acme_sked_litter", objNull])}
    && {isNull (_thing getVariable ["acme_sked_placing", objNull])}
    && {isNull (_thing getVariable ["acme_drag_by", objNull])}
} else {
    // a SKED is a sheet of slick plastic: it goes earlier than a body or a litter on feet
    if (getNumber (configOf _thing >> "acmeDragStrap") > 0) then {_angle = _angle - 8;};
    !isNull (_thing getVariable ["acme_sked_patient", objNull])
    && {!(_thing getVariable ["acme_sked_lifted", false])}
    && {((_thing getVariable ["acme_sked_bearers", []]) findIf {!isNull _x}) < 0}
    && {isNull (_thing getVariable ["acme_drag_by", objNull])}
    && {isNull (_thing getVariable ["ace_common_owner", objNull])}
};
if (!_ok) exitWith {-1};
// on the terrain: not higher over it than a body lies, and nothing to stand on between it and the terrain
private _at = getPosASL _thing;
if ((_at select 2) - (getTerrainHeightASL _at) > 0.35 || {surfaceIsWater _at}) exitWith {-1};
_angle max 5
