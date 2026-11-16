/*
 * Read-only inspection of nearby equipment and casualty links. Run on a client for attachment
 * state on that machine, or pass an object on the server for authoritative chest and crew state.
 * Returns [checked objects, issues]; detail lines are written to RPT.
 */
params [["_observer", objNull, [objNull]]];
if (isNull _observer) exitWith {[0, 0]};
private _objects = nearestObjects [_observer, ["ACME_SKED_Base", "ACME_MedicalChest", "CAManBase", "vtx_H60_base"], 20];
private _checked = 0;
private _issues = 0;
{
    private _notes = [];
    private _state = [];
    if (_x isKindOf "ACME_SKED_Wrapped") then {
        private _patient = _x getVariable ["acme_sked_patient", objNull];
        private _bearers = (_x getVariable ["acme_sked_bearers", []]) select {!isNull _x};
        private _limits = [_x] call acme_sked_fnc_bearerLimits;
        private _lead = _x getVariable ["acme_sked_lead", objNull];
        private _lifted = _x getVariable ["acme_sked_lifted", false];
        private _expected = [_x] call acme_sked_fnc_patientRoot;
        private _actual = attachedTo _patient;
        if (isNull _patient || {(_patient getVariable ["acme_sked_litter", objNull]) isNotEqualTo _x}) then {
            _notes pushBack "missing casualty or reciprocal link";
        } else {
            if (isNull objectParent _patient && {!(_patient getVariable ["acme_sked_loading", false])}
                && {_actual isNotEqualTo _expected}) then {
                _notes pushBack "casualty attachment differs from litter root";
            };
        };
        if ((count _bearers) > (_limits select 1)) then {_notes pushBack "handle limit exceeded"};
        if (_lifted && {isNull _lead || {!(_lead in _bearers)} || {_expected isNotEqualTo _lead}
            || {(count _bearers) < (_limits select 0)}}) then {_notes pushBack "invalid lift team or lead"};
        private _litter = _x;
        if ((_bearers findIf {
            (_x getVariable ["acme_sked_bearing", objNull]) isNotEqualTo _litter
            || {(!(_x isEqualTo _lead) || {!_lifted}) && {(attachedTo _x) isNotEqualTo _expected}}
        }) >= 0) then {_notes pushBack "bearer link or attachment differs from claim"};
        _state = ["occupied", _patient, _actual, _expected, _lifted, _bearers, _limits, animationState _patient, vest _patient];
    } else {
        if (_x isKindOf "ACME_SKED_Base") then {
            _state = ["equipment", attachedTo _x];
        };
    };
    if (_x isKindOf "ACME_MedicalChest") then {
        private _status = _x getVariable ["ACME_medicalChestState", []];
        if !(_status isEqualTo []) then {
            _status params ["_revision", "_open"];
            private _transition = _x getVariable ["ACME_medicalChestTransition", false];
            private _cabinet = _x getVariable ["ACME_medicalChestCabinet", objNull];
            private _cargo = _x getVariable ["ACME_medicalChestCargo", objNull];
            private _finish = (getObjectTextures _x) param [0, ""];
            if (!_transition) then {
                if (isNull _cargo || {_open isEqualTo (isNull _cabinet)} || {_open && {(attachedTo _cargo) isNotEqualTo _cabinet}}) then {
                    _notes pushBack "chest state or cargo mismatch";
                };
                if (_open && {!isNull _cabinet} && {((getObjectTextures _cabinet) param [0, ""]) != _finish}) then {
                    _notes pushBack "cabinet finish differs from closed chest";
                };
            };
            if (isServer) then {
                private _lid = _x getVariable ["ACME_medicalChestLid", objNull];
                private _viewerCount = count (_x getVariable ["ACME_medicalChestViewers", []]);
                private _drawers = _x getVariable ["ACME_medicalChestDrawerFraction", 0];
                if (_open && {!_transition} && {isNull _lid || {((getObjectTextures _lid) param [0, ""]) != _finish}}) then {
                    _notes pushBack "missing lid or mismatched lid finish";
                };
                if (_open && {!_transition} && {(_x getVariable ["ACME_medicalChestDrawerPFH", -1]) < 0}
                    && {abs (_drawers - ([0, 1] select (_viewerCount > 0))) > 0.01}) then {
                    _notes pushBack "drawers disagree with viewers and no motion is running";
                };
                _state = ["chest", _revision, _open, _transition, _viewerCount, _drawers];
            } else {
                _state = ["chest", _revision, _open, _transition];
            };
        };
    };
    if (_x isKindOf "CAManBase" && {_x getVariable ["acme_sked_stowed", false]}) then {
        _state = ["stowed", _x getVariable ["acme_sked_stowedOpen", "ACME_SKED_Open"], objectParent _x];
    };
    if (_x isKindOf "vtx_H60_base") then {
        _state = ["Hatchet", [0, _x] call acme_sked_fnc_preferredLitter];
    };
    if !(_state isEqualTo []) then {
        _checked = _checked + 1;
        _issues = _issues + count _notes;
        diag_log format ["[ACME Transport] audit type=%1 net=%2 state=%3 issues=%4", typeOf _x, netId _x, _state, _notes];
    };
} forEach _objects;
private _summary = format ["Transport audit: %1 objects, %2 issues. See RPT for details.", _checked, _issues];
diag_log format ["[ACME Transport] %1", _summary];
if (hasInterface && {_observer isEqualTo player}) then {systemChat _summary};
[_checked, _issues]
