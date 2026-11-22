/*
 * On every machine with a screen, eight times a second: the sound of what is dragged over the ground ("if there is
 * a dragging sound effect, i want those to play when items are being drug across the floor", 2026-11-20). Made
 * here, for this machine only: nothing is sent.
 * The sound is the game's own of a body moved over the ground, which it has for each kind of ground (the crawl
 * sounds of A3\Sounds_F\characters\crawl: dirt, grass, tall grass, gravel, sand, concrete, water). One is played
 * at the thing every stretch of way it is moved, lower and louder for a litter or a box than for a casualty. The
 * mod has no drag sound of its own and neither has ACE.
 * What is dragged near the camera is looked for once a second, within 35 m, six things at most: what hangs on the
 * carriers of fn_dragLocal.sqf (a SKED, a Talon II taken at its head end, a box, a casualty), and what somebody
 * drags with ACE. Not what is carried clear of the ground (a Talon II that two carry; ACE's carrying).
 * Setting: acme_drag_sound.
 * Arguments: none.
 */
if !(missionNamespace getVariable ["acme_drag_sound", true]) exitWith {};
if (diag_tickTime > (missionNamespace getVariable ["acme_drag_soundNext", 0])) then {
    acme_drag_soundNext = diag_tickTime + 1;
    private _camera = positionCameraToWorld [0, 0, 0];
    private _things = [];
    {
        {if (!isNull _x) then {_things pushBackUnique _x;};} forEach (attachedObjects _x);
    } forEach (nearestObjects [_camera, ["ACME_DragCarrier"], 35]);
    {
        private _dragged = _x getVariable ["ace_dragging_draggedObject", objNull];
        if (!isNull _dragged) then {_things pushBackUnique _dragged;};
    } forEach (_camera nearEntities ["CAManBase", 35]);
    acme_drag_soundNear = _things select [0, 6];
};
{
    private _thing = _x;
    if (!isNull _thing) then {
        private _at = getPosWorldVisual _thing;
        private _last = _thing getVariable ["acme_sound_at", _at];
        private _since = _thing getVariable ["acme_sound_time", diag_tickTime - 1];
        _thing setVariable ["acme_sound_at", _at];
        _thing setVariable ["acme_sound_time", diag_tickTime];
        private _speed = (_at distance2D _last) / ((diag_tickTime - _since) max 0.05);
        // (the way it has come since its last sound: a sound for every 0.55 m, so the pace of the sounds is the
        // pace it is moved at)
        private _way = (_thing getVariable ["acme_sound_way", 0]) + ((_at distance2D _last) min 1);
        if (_speed < 0.25 || {_speed > 12} || {!isNull (_thing getVariable ["acme_carry_rear", objNull])}) then {
            _thing setVariable ["acme_sound_way", _way min 0.4];
        } else {
            if (_way < 0.55) then {
                _thing setVariable ["acme_sound_way", _way];
            } else {
                _thing setVariable ["acme_sound_way", 0];
                private _man = _thing isKindOf "CAManBase";
                private _ground = getPosASLVisual _thing;
                private _kind = "Dirt";
                if (surfaceIsWater _ground && {(_ground select 2) < 0.2}) then {_kind = "water";} else {
                    // on a floor (anything but the terrain is under it): the sound of a hard floor
                    private _under = lineIntersectsSurfaces [_ground vectorAdd [0, 0, 0.6], _ground vectorAdd [0, 0, -0.6], _thing, attachedTo _thing, true, 1, "GEOM", "NONE"];
                    if (_under isNotEqualTo [] && {!isNull ((_under select 0) select 2)}) then {_kind = "concrete";} else {
                        private _surface = (surfaceType _ground) select [1];
                        _kind = missionNamespace getVariable ("acme_sound_of_" + _surface);
                        if (isNil "_kind") then {
                            private _env = toLowerANSI getText (configFile >> "CfgSurfaces" >> _surface >> "soundEnviron");
                            _kind = "Dirt";
                            {
                                _x params ["_word", "_set"];
                                if ((_env find _word) >= 0) exitWith {_kind = _set;};
                            } forEach [
                                ["tall", "grassTall"], ["grass", "Grass"], ["gravel", "Gravel"], ["rock", "Gravel"], ["stone", "Gravel"],
                                ["sand", "Sand"], ["beach", "Sand"], ["concrete", "concrete"], ["road", "concrete"], ["tarmac", "concrete"],
                                ["pavement", "concrete"], ["asphalt", "concrete"], ["metal", "concrete"], ["steel", "concrete"],
                                ["wood", "concrete"], ["tile", "concrete"], ["lino", "concrete"], ["virtual", "concrete"], ["int_", "concrete"]
                            ];
                            missionNamespace setVariable ["acme_sound_of_" + _surface, _kind];
                        };
                    };
                };
                private _file = format ["A3\Sounds_F\characters\crawl\%1_crawl_%2.wss", _kind, 1 + floor random 5];
                // a casualty: the sound as it is; a litter or a box: lower and louder (more of it on the ground)
                private _pitch = ([0.74, 0.92] select _man) + random 0.1;
                private _volume = ([2.6, 1.8] select _man) * (0.7 + 0.3 * ((_speed / 1.4) min 1.3));
                playSound3D [_file, objNull, false, _ground vectorAdd [0, 0, 0.1], _volume, _pitch, 45, 0, true];
                acme_drag_sounds = (missionNamespace getVariable ["acme_drag_sounds", 0]) + 1;       // for the tests
                acme_drag_soundLast = _file;
            };
        };
    };
} forEach (missionNamespace getVariable ["acme_drag_soundNear", []]);
