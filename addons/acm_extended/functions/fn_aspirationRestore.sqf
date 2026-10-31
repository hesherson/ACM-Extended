/* Restore is the sole legacy migration boundary. Rebind persistent injury and its receipt together.
 * Native TargetVitals are not serialized by ACM; respiration composes injury at its existing endpoint.
 */
params ["_patient", ["_payload",[]]];
if (isNull _patient || {!local _patient}) exitWith {false};
private _epoch = [_patient] call ACME_fnc_clinicalEpoch;
private _saved = [];
private _legacyLoad = 0;
private _legacyEdema = 0;
if (_payload isEqualType [] && {count _payload == 2} && {(_payload select 0) isEqualTo 3} && {(_payload select 1) isEqualType []}) then {
    {
        if (_x isEqualType [] && {count _x == 2}) then {
            private _name = _x select 0;
            if (_name == "ACME_aspiration_State") then {
                private _value = [_x select 1,false] call ACME_fnc_clinicalCodec;
                if (!isNil "_value") then {_saved = _value;};
            };
            if (_name in ["ACME_aspiration_load","ACME_aspiration_edema"]) then {
                private _v = [_x select 1,false] call ACME_fnc_clinicalCodec;
                if (!isNil "_v" && {_v isEqualType 0} && {finite _v} && {_v >= 0 && {_v <= 1}}) then {
                    if (_name == "ACME_aspiration_load") then {_legacyLoad = _v;} else {_legacyEdema = _v;};
                };
            };
        };
    } forEach (_payload select 1);
};
// Validate a saved tuple using its own epoch before explicitly rebinding it.
private _state = [];
if (_saved isEqualType [] && {count _saved == 5}) then {
    // No temporary epoch writes: validate each element directly.
    _saved params ["_bound","_key","_load","_edema","_serial"];
    if (_bound isEqualType 0 && {finite _bound} && {_bound >= 0} && {_bound == floor _bound} && {_key isEqualType ""}
        && {_load isEqualType 0} && {finite _load} && {_load >= 0 && {_load <= 1}}
        && {_edema isEqualType 0} && {finite _edema} && {_edema >= 0 && {_edema <= 1}}
        && {_serial isEqualType 0} && {finite _serial} && {_serial >= 0} && {_serial == floor _serial}) then {_state = [_epoch,_key,_load,_edema,_serial];};
};
private _event = _patient getVariable ["ACME_laryngo_emesis",[]];
if (_event isEqualType [] && {count _event == 5}) then {
    _event = +_event;
    _event set [3,_epoch];
    [_patient,"ACME_laryngo_emesis",_event] call ACME_fnc_setVarNet;
};
if (_state isEqualTo []) then {
    _state = [_epoch,"",_legacyLoad,_legacyEdema,0];
    // Recognized legacy injury has no receipt history; retain it without guessing another aliquot of emesis.
    if ((_legacyLoad > 0 || {_legacyEdema > 0}) && {_event isEqualType []} && {count _event >= 3}) then {
        private _id = _event select 0;
        private _n = _event select 1;
        private _validId = _id isEqualType "" && {_id != ""};
        if (count _event == 3 && {_id isEqualType 0} && {finite _id}) then {_validId = true;};
        if (_validId && {_n isEqualType 0} && {finite _n}) then {
            private _serial = if (count _event == 5 && {(_event select 4) isEqualType 0} && {finite (_event select 4)} && {(_event select 4) >= 0} && {(_event select 4) == floor (_event select 4)}) then {_event select 4} else {0};
            _state set [1,format ["explicit:%1:%2:%3",_id,_n,_serial]];
            _state set [4,_serial];
        };
    };
};
[_patient,"ACME_aspiration_State",_state] call ACME_fnc_setVarNet;
private _load = _state select 2;
private _edema = _state select 3;
private _injury = _load max (0.85 * _edema);
{[_patient,_x select 0,_x select 1] call ACME_fnc_setVarNet;} forEach [
    ["ACME_aspiration_load",_load],["ACME_aspiration_edema",_edema],["ACME_aspiration_injury",_injury],
    ["ACME_aspiration_edemaActive",_edema >= (missionNamespace getVariable ["ACME_aspiration_edemaCrackleThreshold",0.12])],
    ["ACME_aspiration_SpO2Penalty",30*_injury],["ACME_aspiration_RRDrive",14*_injury],["ACME_aspiration_shunt",0.30*_injury]
];
_patient setVariable ["ACME_aspiration_lastRRAdj",0,false];
_patient setVariable ["ACME_aspiration_lastEmesisKey",_state select 1,false];
_patient setVariable ["ACME_clock_aspiration",nil,false];
_patient setVariable ["ACME_clock_aspiration_owner",nil,false];
true
