// apply one cable-tuner slider change to the cable of the megacode laptop, live.
// the plug x, y and z move the port on the laptop (where the plug sits and the cable goes in), the plug length is
// how far out along the plug the rope is anchored, the dummy y and z move the manikin end, the laptop x, y and z
// move the laptop in its heading frame, and the slack and segments re-form the rope.
// an engine rope stays where it was made once its ends hang on attached objects, so every change rebuilds the whole
// cable (ACME_fnc_megacodeCableBuild) instead of re-seating one end of the old one.
// the cable objects were spawned on the server, so the actual work runs there, re-invoked through remoteexec from
// a client. the updated values persist as globals, so new megacode spawns use the tuned cable.
// _this is [_key, _val], from a slider, or [_key, _val, _laptop], for the server re-invoke.
params ["_key", "_val", ["_laptop", objNull]];
if (isNull _laptop) then { _laptop = uiNamespace getVariable ["ACME_MC_CableLaptop", objNull]; };
if (isNull _laptop) exitWith {};
if (!isServer) exitWith { [_key, _val, _laptop] remoteExec ["ACME_fnc_megacodeCableApply", 2]; };

private _dummy = _laptop getVariable ["ACME_megacodeDummy", objNull];
private _lOff  = +(missionNamespace getVariable ["ACME_megacode_laptopHoseOffset", [0.10, 0.152, -0.143]]);
private _dOff  = +(missionNamespace getVariable ["ACME_megacode_dummyHoseOffset", [0, 0.32, 0.12]]);
private _plug  = missionNamespace getVariable ["ACME_megacode_plugLength", 0.036];
private _slack = missionNamespace getVariable ["ACME_megacode_ropeSlack", 0.2];
private _seg   = missionNamespace getVariable ["ACME_megacode_ropeSegments", 0];
private _pos   = +(missionNamespace getVariable ["ACME_megacode_laptopPosOffset", [0,0,0]]);  // the laptop position, in the heading frame.
// the legacy laptop pitch, yaw and roll. it is no longer exposed in the tuner and is kept callable.
private _pitch = missionNamespace getVariable ["ACME_megacode_laptopPitch", 0];
private _yaw   = missionNamespace getVariable ["ACME_megacode_laptopYaw", 0];
private _roll  = missionNamespace getVariable ["ACME_megacode_laptopRoll", 0];

switch (_key) do {
    // the port on the laptop: where the plug sits and the cable goes in.
    case "lx": { _lOff set [0, _val]; };
    case "ly": { _lOff set [1, _val]; };
    case "lz": { _lOff set [2, _val]; };
    case "plug": { _plug = _val; };
    // where the cable attaches on the manikin.
    case "dy": { _dOff set [1, _val]; };
    case "dz": { _dOff set [2, _val]; };
    // the laptop position in its heading frame.
    case "mlx": { _pos set [0, _val]; [_laptop, _pos select 0, _pos select 1, _pos select 2] call ACME_fnc_megacodeLaptopMove; };
    case "mly": { _pos set [1, _val]; [_laptop, _pos select 0, _pos select 1, _pos select 2] call ACME_fnc_megacodeLaptopMove; };
    case "mlz": { _pos set [2, _val]; [_laptop, _pos select 0, _pos select 1, _pos select 2] call ACME_fnc_megacodeLaptopMove; };
    // the legacy laptop orientation.
    case "pitch": { _pitch = _val; [_laptop, _pitch, _yaw, _roll] call ACME_fnc_megacodeLaptopOrient; };
    case "yaw":   { _yaw   = _val; [_laptop, _pitch, _yaw, _roll] call ACME_fnc_megacodeLaptopOrient; };
    case "roll":  { _roll  = _val; [_laptop, _pitch, _yaw, _roll] call ACME_fnc_megacodeLaptopOrient; };
    case "slack": { _slack = _val; };
    case "seg":   { _seg   = _val; };
};

// persist, so future megacode spawns use the tuned cable and laptop position.
missionNamespace setVariable ["ACME_megacode_laptopHoseOffset", _lOff, true];
missionNamespace setVariable ["ACME_megacode_dummyHoseOffset", _dOff, true];
missionNamespace setVariable ["ACME_megacode_plugLength", _plug, true];
missionNamespace setVariable ["ACME_megacode_ropeSlack", _slack, true];
missionNamespace setVariable ["ACME_megacode_ropeSegments", _seg, true];
missionNamespace setVariable ["ACME_megacode_laptopPosOffset", _pos, true];
missionNamespace setVariable ["ACME_megacode_laptopPitch", _pitch, true];
missionNamespace setVariable ["ACME_megacode_laptopYaw", _yaw, true];
missionNamespace setVariable ["ACME_megacode_laptopRoll", _roll, true];

// re-make the cable from the new values.
if (!isNull _dummy) then { [_dummy] call ACME_fnc_megacodeCableBuild; };
