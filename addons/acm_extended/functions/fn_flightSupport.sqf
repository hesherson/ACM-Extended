/* Actual nearby aircraft support, independent of aircraft classname or altitude.
 * ROADWAY (supported since Arma 2.08), GEOM and PHYSX are queried separately:
 * an available GEOM LOD does not imply that its walkable floor was tested.
 * Result: [aircraft, feet/model, model-root/model]. A bounding box is not support.
 * Optional point/air arguments validate a previously owned floor anchor only. */
params [["_patient",objNull,[objNull]], ["_foot",[],[[]]],
    ["_expectedAir",objNull,[objNull]], ["_checkMotion",true,[false]], ["_allowDeadContact",false,[false]]];
// Medical reachability may inspect a dead casualty's actual floor. No default
// physiology or containment caller enables this read-only contact exception.
if (isNull _patient || {!_allowDeadContact && {!alive _patient}}) exitWith {[]};
if (_foot isEqualTo []) then {_foot = getPosASL _patient;};
if (count _foot != 3 || {(_foot findIf {!(_x isEqualType 0) || {!finite _x}}) >= 0}) exitWith {[]};
private _best = [];
private _bestDistance = 1;
private _up = if (isNull _expectedAir) then {[0,0,1]} else {vectorUp _expectedAir};
private _start = _foot vectorAdd (_up vectorMultiply 0.20);
private _end = _foot vectorDiff (_up vectorMultiply 0.30);
{
    private _hits = lineIntersectsSurfaces [_start,_end,_patient,objNull,true,1,_x,"NONE"];
    if !(_hits isEqualTo []) then {
        private _hit = _hits select 0;
        private _air = _hit param [2,objNull];
        if (isNull _air || {!(_air isKindOf "Air")}) then {_air = _hit param [3,objNull];};
        private _point = _hit param [0,[]];
        private _normal = _hit param [1,[]];
        if (count _point == 3 && {count _normal == 3}) then {
            private _gap = _foot vectorDistance _point;
            private _rayDistance = _start vectorDistance _point;
            // A tight contact ray never enrolls someone merely near an airframe.
            // Cross-LOD order is measured from the SAME RAY START: an obstacle
            // just above the feet must block an aircraft floor just below them.
            if (_gap <= 0.30 && {_rayDistance < _bestDistance}) then {
                _bestDistance = _rayDistance;
                // A closer non-air obstacle/terrain blocks a farther aircraft
                // floor even when the obstacle exists in only the other LOD.
                _best = [];
                if (!isNull _air && {_air isKindOf "Air"} && {alive _air}
                    && {isNull _expectedAir || {_air isEqualTo _expectedAir}}
                    && {(_normal vectorDotProduct _up) > 0.45}) then {
                    _best = [_air,_air vectorWorldToModel (_foot vectorDiff getPosWorld _air),
                        _air vectorWorldToModel ((getPosWorld _patient) vectorDiff getPosWorld _air)];
                };
            };
        };
    };
} forEach ["ROADWAY","GEOM","PHYSX"];
if (_best isEqualTo []) exitWith {[]};
if (_checkMotion) then {
    private _air = _best select 0;
    // Native HALO/freefall or a rapid unsupported descent must retain freefall.
    // Touching-ground exempts a genuinely carried floor contact from comparing
    // stale infantry velocity with the aircraft's climb velocity.
    private _animation = toLowerANSI animationState _patient;
    private _falling = ((velocity _patient) vectorDiff velocity _air) select 2;
    if ((_animation find "halofreefall") >= 0
        || {!isTouchingGround _patient && {_falling < -4}
            && {abs ((velocity _patient) select 2) > 4}}) then {_best = [];};
};
_best
