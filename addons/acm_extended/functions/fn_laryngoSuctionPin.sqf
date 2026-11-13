/* B13: explicit SALAD park at the upper esophageal inlet, left of the cord target.
   Manual suction bags cannot be pinned. Parking never changes blade/tube success gates. */
disableSerialization;
private _medic = uiNamespace getVariable ["ACME_laryngo_medic", objNull];
if (uiNamespace getVariable ["ACME_laryngo_sucPinned", false]) exitWith {
    uiNamespace setVariable ["ACME_laryngo_sucPinned", false];
    uiNamespace setVariable ["ACME_laryngo_sucOn", false];
    [_medic] call ACME_fnc_suctionSfxStop;
    [true] call ACME_fnc_suctionPublish;
    [] call ACME_fnc_laryngoRefreshSlots;
};
if (([true] call ACME_fnc_suctionSelectDevice) != 1) exitWith {
    ["Continuous SALAD parking requires the ACCUVAC. The suction bag must be squeezed by hand.", 3] call ace_common_fnc_displayTextStructured;
};
if (!([_medic,uiNamespace getVariable ["ACME_laryngo_patient",objNull]] call ACME_fnc_equipmentAvailable)
    || {(uiNamespace getVariable ["ACME_laryngo_held", ""]) != "suction"}) exitWith {
    ["Take the ACCUVAC suction first; bring its tip into the mouth, then middle-click.", 3] call ace_common_fnc_displayTextStructured;
};
// Recompute hit test at the click, rather than trusting a stale previous frame.
(uiNamespace getVariable ["ACME_laryngo_cur", [0,0]]) params ["_cx","_cy"];
(uiNamespace getVariable ["ACME_laryngo_rect", [0,0,1,1]]) params ["_rx","_ry","_rw","_rh"];
(uiNamespace getVariable ["ACME_Laryngo_ShakeBase_off", [0,0]]) params ["_dx","_dy"];
(uiNamespace getVariable ["ACME_laryngo_mouthZone", [0.502,0.172,0.16]]) params ["_mu","_mv","_radius"];
private _u = (_cx - _rx - _dx) / (_rw max 0.00001);
private _v = (_cy - _ry - _dy) / (_rh max 0.00001);
if (((_u - _mu)^2 + (_v - _mv)^2) > (_radius * 0.85)^2) exitWith {
    ["Bring the suction tip inside the mouth before parking it.", 2] call ace_common_fnc_displayTextStructured;
};
(uiNamespace getVariable ["ACME_laryngo_frame", [0,0,1,1]]) params ["_fx","_fy","_fw","_fh"];
// Anatomical UV anchor is deliberately outside the vocal-cord target, not on a tool pixel.
private _park = [0.425, 0.210];
uiNamespace setVariable ["ACME_laryngo_sucPinRel", [(_rx + (_park select 0) * _rw - _fx) / (_fw max 0.00001), (_ry + (_park select 1) * _rh - _fy) / (_fh max 0.00001)]];
uiNamespace setVariable ["ACME_laryngo_sucPinned", true];
uiNamespace setVariable ["ACME_laryngo_sucInMouth", true];
uiNamespace setVariable ["ACME_laryngo_sucOn", true];
uiNamespace setVariable ["ACME_laryngo_held", ""];
[_medic, uiNamespace getVariable ["ACME_laryngo_patient", objNull]] call ACME_fnc_suctionSfxStart;
[true] call ACME_fnc_suctionPublish;
["SALAD suction parked. Continue with the laryngoscope and tube; middle-click again to remove it.", 3] call ace_common_fnc_displayTextStructured;
[] call ACME_fnc_laryngoRefreshSlots;
