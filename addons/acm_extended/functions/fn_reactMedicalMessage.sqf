/* Local browser boundary. JSON is data; no compile, arbitrary SQF, remote events or actor from JSON. */
params ["_control","_confirm","_text"];
// Always answer the native JS dialog, including rejected input, to avoid blocking Chromium.
if (_confirm || {!(_text isEqualType "")} || {count _text > 2048}) exitWith {true};
private _display = ctrlParent _control;
if (isNull _display || {!(_display isEqualTo findDisplay 89300)}
    || {!(_control isEqualTo (_display displayCtrl 89301))}) exitWith {true};
private _context = _display getVariable ["ACME_reactContext",[]];
if !([_context] call ACME_fnc_reactMedicalValid) exitWith {true};
private _packet = nil;
try {_packet = fromJSON _text;} catch {_packet = nil;};
if (isNil "_packet" || {!(_packet isEqualType createHashMap)} || {count _packet != 5}) exitWith {true};
private _version = _packet getOrDefault ["version",-1];
private _session = _packet getOrDefault ["session",""];
private _sequence = _packet getOrDefault ["sequence",-1];
private _operation = _packet getOrDefault ["operation",""];
private _route = _packet getOrDefault ["route",[]];
if (isNil "_version" || {isNil "_session"} || {isNil "_sequence"}
    || {isNil "_operation"} || {isNil "_route"}) exitWith {true};
if (!(_version isEqualTo 1) || {!(_session isEqualType "")} || {_session == ""}
    || {_session != (_display getVariable ["ACME_reactSession",""])}
    || {!(_sequence isEqualType 0)} || {!finite _sequence} || {_sequence != floor _sequence}
    || {_sequence < 1} || {_sequence > 1000000}
    || {_sequence <= (_display getVariable ["ACME_reactRequestSequence",0])}
    || {!(_operation in ["ready","native","manage"])} || {!(_route isEqualType [])}) exitWith {true};
if (_operation == "manage") then {
    if (count _route != 3 || {(_route findIf {isNil "_x"}) >= 0}) exitWith {_operation = "";};
    _route params ["_part","_iv","_site"];
    if (!(_part in ["head","body","leftarm","rightarm","leftleg","rightleg"])
        || {!(_iv isEqualType true)} || {!(_site isEqualType 0)} || {!(_site in [0,1,2])}
        || {!_iv && {_site != 0}}
        || {!([_context select 1,_part,_iv,_site] call ACME_fnc_transfusionAccessValid)}) then {_operation = "";};
} else {if (count _route != 0) then {_operation = "";};};
if (_operation == "") exitWith {
    _display setVariable ["ACME_reactRequestSequence",_sequence];
    private _reply = createHashMapFromArray [["version",1],["session",_session],["request",_sequence]];
    _control ctrlWebBrowserAction ["ExecJS",format ["window.ACMEUI && window.ACMEUI.reject(%1);",toJSON _reply]];
    true
};
if (_operation != "ready" && {!(_display getVariable ["ACME_reactReady",false])}) exitWith {true};
// Retire this request before any re-entrant UI/native event can repeat its handoff.
_display setVariable ["ACME_reactRequestSequence",_sequence];
if (_operation == "ready") exitWith {_display setVariable ["ACME_reactReady",true];true};
[_display,_route] call ACME_fnc_reactMedicalFallback;
true
