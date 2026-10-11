/* Reserve an exact prepared bag into provider escrow before the owner request. No new stock debit here. */
if (canSuspend) exitWith {isNil {_this call ACME_fnc_piggybackAttachRequest;};};
params ["_setId"];
private _intent = missionNamespace getVariable ["ACME_piggybackPending", []];
if (count _intent < 6 || {_setId == ""}) exitWith {false};
_intent params ["_patient", "_part", "_iv", "_site", "_primaryUid", "_epoch"];
if !((_intent select [0,4]) isEqualTo [missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Target",objNull],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_BodyPart",""],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_SelectIV",true],missionNamespace getVariable ["ACM_circulation_TransfusionMenu_Selected_AccessSite",-1]]) exitWith {["cancel"] call ACME_fnc_piggybackWorkflow;false};
private _sets = +(ACE_player getVariable ["ACME_preparedIVSets", []]);
private _si = _sets findIf {(_x param [0, ""]) == _setId};
if (_si < 0) exitWith {false};
private _set = +(_sets select _si);
private _prepared = +(ACE_player getVariable ["ACME_infusion_PreparedBags", []]);
private _mi = _prepared findIf {(_x param [0, ""]) == _setId};
private _medication = if (_mi >= 0) then {+(_prepared select _mi)} else {[]};
private _type = getText (configFile >> "ace_medical_treatment" >> "IV" >> (_set param [2, ""]) >> "type");
if ((_set param [8,"yset"]) in ["yset","blood","propofol"] || {!([_patient,_part,_iv,_site,_type,!(_medication isEqualTo [])] call ACME_fnc_piggybackEligible)}) exitWith {
    [ACE_player,"Choose a matching non-blood fluid, or a prepared saline infusion for a saline primary."] call ACME_fnc_clinicalNotice;
    false
};
// Do not reserve a physical set already in a normal Hang/Give transaction.
private _normalHang = missionNamespace getVariable ["ACME_preparedHangPending",createHashMap];
private _normalInfusion = missionNamespace getVariable ["ACME_preparedPending",createHashMap];
if (((values _normalHang) findIf {!(_x param[3,false]) && {((_x param[1,[]]) param[3,""]) == _setId}}) >= 0
    || {((values _normalInfusion) findIf {!(_x param[2,false]) && {(((_x param[0,[]]) param[10,[]]) param[0,""]) == _setId}}) >= 0}) exitWith {
    [ACE_player,"That prepared bag is already being connected."] call ACME_fnc_clinicalNotice;
    false
};
private _escrow = ACE_player getVariable ["ACME_piggybackEscrow", createHashMap];
if (_setId in _escrow) exitWith {false};
private _serial = (missionNamespace getVariable ["ACME_piggybackSerial",0]) + 1;
missionNamespace setVariable ["ACME_piggybackSerial",_serial];
private _id = format ["pib:%1:%2:%3",clientOwner,_serial,floor(diag_tickTime*1000)];
private _at = serverTime;
_part = toLowerANSI _part;
private _args = [ACE_player,_patient,_id,_setId,_part,_iv,_site,_primaryUid,_epoch,_set,_medication,_at];
private _entry = [_id,_patient,_epoch,_set,_medication,_at,_args];
_escrow set [_setId,_entry];
ACE_player setVariable ["ACME_piggybackEscrow",_escrow,true];
_sets deleteAt _si;
if (_mi >= 0) then {_prepared deleteAt _mi;};
ACE_player setVariable ["ACME_preparedIVSets",_sets,true];
ACE_player setVariable ["ACME_infusion_PreparedBags",_prepared,true];
private _requests = missionNamespace getVariable ["ACME_piggybackRequests",createHashMap];
_requests set [_id,[_args,CBA_missionTime,false]];
missionNamespace setVariable ["ACME_piggybackRequests",_requests];
private _source = findDisplay 86000;
if (!isNull _source) then {_source setVariable ["ACME_piggybackConnecting",true]; _source closeDisplay 1;};
[_id] call ACME_fnc_piggybackRetry;
true
