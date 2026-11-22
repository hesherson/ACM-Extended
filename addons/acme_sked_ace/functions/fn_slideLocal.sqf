/*
 * Every frame, on every machine, for what is local to it: casualties and occupied litters that were left on a
 * steep slope slide down it.
 *
 * Once a second the candidates are looked through (fn_slideCan.sqf) and those on ground steeper than their
 * angle of friction are taken into the list of what slides. Every frame each of those is moved down the fall
 * line: pulled by g * (sin(slope) - mu * cos(slope)), mu the tangent of its angle of friction, and held back in
 * proportion to its speed. So just over the angle it creeps (a hand's width a second), ten degrees over it it
 * goes at a slow walk, and it never goes faster than acme_slide_maxSpeed. Where the ground gets shallower the
 * same friction stops it. It stops at once against a wall, a rock or a vehicle, and when somebody takes it.
 * Settings: acme_slide (on/off), acme_slide_angle (degrees, for a body; a SKED 8 less).
 */
if !(missionNamespace getVariable ["acme_slide", true]) exitWith {
    if (acme_slide_list isNotEqualTo []) then {acme_slide_list = [];};
};
private _now = diag_tickTime;
if (_now >= acme_slide_scanAt) then {
    acme_slide_scanAt = _now + 1;
    private _has = acme_slide_list apply {_x select 0};
    private _candidates = (allUnits select {local _x && {_x getVariable ["ACE_isUnconscious", false]}})
        + ((entities [["ACME_SKED_Wrapped"], [], false, true]) select {local _x});
    {
        if !(_x in _has) then {
            private _angle = [_x] call acme_sked_fnc_slideCan;
            if (_angle > 0 && {acos (((surfaceNormal (getPosASL _x)) select 2) min 1) > _angle}
                && {_now >= (_x getVariable ["acme_slide_blockedUntil", 0])}) then {
                acme_slide_list pushBack [_x, 0, _angle];
            };
        };
    } forEach _candidates;
};
if (acme_slide_list isEqualTo []) exitWith {};
private _dt = diag_deltaTime min 0.1;
private _keep = [];
{
    _x params ["_thing", "_speed", "_angle"];
    private _go = ([_thing] call acme_sked_fnc_slideCan) > 0;
    if (_go) then {
        private _at = getPosASL _thing;
        private _normal = surfaceNormal _at;
        private _slope = acos ((_normal select 2) min 1);
        private _fall = [_normal select 0, _normal select 1, 0];
        // gravity along the slope less friction; held back the faster it goes
        private _pull = 9.81 * ((sin _slope) - (tan _angle) * (cos _slope));
        _speed = _speed + (_pull - 2.5 * _speed) * _dt;
        _speed = _speed min (missionNamespace getVariable ["acme_slide_maxSpeed", 3]);
        if (_speed <= 0 || {(vectorMagnitude _fall) < 0.01}) then {
            _go = false;
        } else {
            _fall = vectorNormalized _fall;
            // something in the way, a forearm's length ahead and a hand's width over the ground?
            private _from = _at vectorAdd [0, 0, 0.3];
            private _patient = _thing getVariable ["acme_sked_patient", objNull];
            private _hit = lineIntersectsSurfaces [_from, _from vectorAdd (_fall vectorMultiply 0.9), _thing, _patient, true, 1, "GEOM", "NONE"];
            if (_hit isNotEqualTo [] && {!isNull ((_hit select 0) select 2)}) then {
                _go = false;
                _thing setVariable ["acme_slide_blockedUntil", _now + 5];
            } else {
                private _to = _at vectorAdd (_fall vectorMultiply (_speed * _dt));
                _to set [2, getTerrainHeightASL _to];
                if (surfaceIsWater _to) then {
                    _go = false;
                } else {
                    if (_thing isKindOf "CAManBase") then {
                        _thing setPosASL _to;
                    } else {
                        // a litter lies on the ground as it goes
                        private _dir = vectorDir _thing;
                        private _up = surfaceNormal _to;
                        _thing setPosASL _to;
                        _thing setVectorDirAndUp [_dir vectorDiff (_up vectorMultiply (_dir vectorDotProduct _up)), _up];
                    };
                };
            };
        };
    };
    if (_go) then {_keep pushBack [_thing, _speed, _angle];};
} forEach acme_slide_list;
acme_slide_list = _keep;
