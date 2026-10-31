/* Bound local card input delegates to the original native selection handler. No menu navigation. */
params ["_control","_confirm","_text"];
if (_confirm || {!(_text isEqualType "")} || {count _text > 2048}) exitWith {true};
private _display = ctrlParent _control;
if (isNull _display || {!(_display isEqualTo findDisplay 86000)}
    || {!(_control isEqualTo (_display displayCtrl 89301))}) exitWith {true};
private _context = _display getVariable ["ACME_reactContext",[]];
if (!([_context] call ACME_fnc_reactMedicalValid)
    || {(missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Medic",objNull]) isNotEqualTo (_context select 0)}
    || {(missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull]) isNotEqualTo (_context select 1)}
    || {!isNull findDisplay 86200} || {!isNull findDisplay 84000}
    || {!((_display getVariable ["ACME_txActionMenu",""]) isEqualTo "")}) exitWith {true};
private _packet = nil;
try {_packet = fromJSON _text;} catch {_packet = nil;};
if (isNil "_packet" || {!(_packet isEqualType createHashMap)} || {count _packet != 5}) exitWith {true};
private _version = _packet getOrDefault ["version",-1];
private _session = _packet getOrDefault ["session",""];
private _sequence = _packet getOrDefault ["sequence",-1];
private _operation = _packet getOrDefault ["operation",""];
private _route = _packet getOrDefault ["route",[]];
if (isNil "_version" || {isNil "_session"} || {isNil "_sequence"} || {isNil "_operation"} || {isNil "_route"}) exitWith {true};
if (!(_version isEqualTo 2) || {!(_session isEqualType "")} || {_session == ""}
    || {_session != (_display getVariable ["ACME_reactSession",""])}
    || {!(_sequence isEqualType 0)} || {!finite _sequence} || {_sequence != floor _sequence}
    || {_sequence < 1} || {_sequence > 1000000}
    || {_sequence <= (_display getVariable ["ACME_reactRequestSequence",0])}
    || {!(_operation in ["ready","select","wheel","key"])} || {!(_route isEqualType [])}) exitWith {true};
if (_operation == "ready") exitWith {
    if (count _route == 0) then {
        _display setVariable ["ACME_reactRequestSequence",_sequence];
        _display setVariable ["ACME_reactReady",true];
    };
    true
};
if (!(_display getVariable ["ACME_reactReady",false]) || {count _route != 1} || {isNil {_route select 0}}) exitWith {true};
private _argument = _route select 0;
private _allowed = false;
if (_operation == "select") then {
    if (_argument isEqualType "" && {count _argument <= 64}) then {
        private _identity = (_display getVariable ["ACME_reactRows",createHashMap]) getOrDefault [_argument,[]];
        if (_identity isNotEqualTo []) then {
            _control setVariable ["ACME_txIdentity",_identity];
            _control setVariable ["ACME_txPatient",_context select 1];
            _allowed = true;
        };
    };
} else {
    _allowed = _argument isEqualType 0 && {finite _argument} && {
        if (_operation == "wheel") then {_argument in [-1,1]} else {_argument in [200,208,201,209,199,207]}
    };
};
// Retire the request before native callbacks can reenter the browser bridge.
_display setVariable ["ACME_reactRequestSequence",_sequence];
if (_allowed) then {[_control,_operation,_argument] call ACME_fnc_transfusionCardSelect;};
private _reply = createHashMapFromArray [["version",2],["session",_session],["request",_sequence]];
_control ctrlWebBrowserAction ["ExecJS",format ["window.ACMEUI && window.ACMEUI.ack(%1);",toJSON _reply]];
true
