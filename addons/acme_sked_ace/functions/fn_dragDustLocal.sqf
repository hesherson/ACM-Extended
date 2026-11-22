/*
 * On every machine with a screen, eight times a second: dust where a dragged thing scrapes over the ground. It is
 * made here, for this screen only: nothing is sent, and a machine that sees no drag does nothing but look at an
 * empty list. What is dragged near the camera is looked for once a second (the carriers of fn_dragLocal.sqf,
 * within 45 m, six at most).
 * Where: under the trailing end and the middle of a SKED or a box; at the foot handles of a Talon whose head end
 * is lifted (none when two carry it); at the heels of a casualty. Only while it moves, only on ground that makes
 * dust (CfgSurfaces "dust"), not on a floor, not in water, not in rain.
 * Setting: acme_drag_dust.
 * Arguments: none.
 */
if !(missionNamespace getVariable ["acme_drag_dust", true]) exitWith {};
if (diag_tickTime > (missionNamespace getVariable ["acme_drag_dustNext", 0])) then {
    acme_drag_dustNext = diag_tickTime + 1;
    private _near = nearestObjects [positionCameraToWorld [0, 0, 0], ["ACME_DragCarrier"], 45];
    acme_drag_dustNear = _near select [0, 6];
};
if (acme_drag_dustNear isEqualTo [] || {rain > 0.25}) exitWith {};
{
    private _carrier = _x;
    if (!isNull _carrier) then {
        private _unit = attachedTo _carrier;
        {
            private _thing = _x;
            private _at = getPosWorldVisual _thing;
            private _last = _thing getVariable ["acme_dust_at", _at];
            private _since = _thing getVariable ["acme_dust_time", diag_tickTime - 1];
            _thing setVariable ["acme_dust_at", _at];
            _thing setVariable ["acme_dust_time", diag_tickTime];
            private _speed = (_at distance2D _last) / ((diag_tickTime - _since) max 0.05);
            if (_speed > 0.5 && {_speed < 12}) then {
                // where it touches the ground, in its own axes
                private _points = [];
                if (_thing isKindOf "CAManBase") then {
                    _points = [_thing selectionPosition ["leftfoot", "Memory"], _thing selectionPosition ["rightfoot", "Memory"]];
                } else {
                    (0 boundingBoxReal _thing) params ["_min", "_max"];
                    private _handles = if (getNumber (configOf _thing >> "acmeDragLift") > 0) then {getArray (configOf _thing >> "acmeLitterHandles")} else {[]};
                    if (count _handles == 4) then {
                        if (isNull (_thing getVariable ["acme_carry_rear", objNull])) then {
                            _points = [_thing selectionPosition [_handles select 2, "Memory"], _thing selectionPosition [_handles select 3, "Memory"]];
                        };
                    } else {
                        // the end further from the rescuer trails
                        private _a = [0, (_min select 1) * 0.85, _min select 2];
                        private _b = [0, (_max select 1) * 0.85, _min select 2];
                        if (!isNull _unit && {(_unit distance2D (_thing modelToWorldVisual _b)) > (_unit distance2D (_thing modelToWorldVisual _a))}) then {_a = _b;};
                        _points = [_a, [0, 0, _min select 2]];
                    };
                };
                {
                    private _p = _thing modelToWorldVisual _x;       // AGL
                    // (near the terrain: not on a floor, a pier or a roof. A casualty's heels are a hand over the
                    // ground; the dust rises from the ground under them.)
                    if ((_p select 2) < 0.45 && {!surfaceIsWater _p}) then {
                        private _surface = (surfaceType _p) select [1];
                        private _dust = missionNamespace getVariable ("acme_dust_of_" + _surface);
                        if (isNil "_dust") then {
                            _dust = getNumber (configFile >> "CfgSurfaces" >> _surface >> "dust");
                            missionNamespace setVariable ["acme_dust_of_" + _surface, _dust];
                        };
                        if (_dust > 0.05) then {
                            private _fade = (0.34 * (_dust min 1)) * ((_speed / 1.4) min 1.3);
                            drop [["\A3\data_f\ParticleEffects\Universal\Universal", 16, 12, 8, 0], "", "Billboard", 1, 1.3 + random 0.8,
                                [_p select 0, _p select 1, 0.04],
                                [(random 0.5) - 0.25, (random 0.5) - 0.25, 0.16 + random 0.18], 0, 1.277, 1, 0.1,
                                [0.18, 0.6 + random 0.4, 0.9 + random 0.4],
                                [[0.62, 0.54, 0.42, _fade], [0.64, 0.56, 0.44, _fade * 0.55], [0.66, 0.58, 0.46, 0]],
                                [1000], 0, 0, "", "", "", random 360];
                            acme_drag_dustDrops = (missionNamespace getVariable ["acme_drag_dustDrops", 0]) + 1;      // for the tests
                        };
                    };
                } forEach _points;
            };
        } forEach (attachedObjects _carrier);
    };
} forEach acme_drag_dustNear;
