/* B121: convert the selected vascular syringe into a persistent Hardcore Medication push transaction. The
   physical magazine is reserved once; the stable Narc Box row remains as the authoritative live plunger state. */
disableSerialization;
private _d = findDisplay 84000;
if (isNull _d || {(uiNamespace getVariable ["ACME_SK_View","syringe"]) != "body"}) exitWith {false};
if !(missionNamespace getVariable ["ACME_hcEff_medications",false]) exitWith {false};
private _existing = missionNamespace getVariable ["ACME_HCMedPushJob",createHashMap];
if (_existing isEqualType createHashMap && {count _existing > 0}) exitWith {false};
private _pending = uiNamespace getVariable ["ACME_SK_PendingInjection",[]];
if !(_pending isEqualType [] && {count _pending >= 3}) exitWith {false};
_pending params ["_body","_site","_route"];
if (_route == "im") exitWith {false};
private _patient = uiNamespace getVariable ["ACME_SK_Patient",objNull];
if (isNull _patient) then {_patient = _d getVariable ["ACME_SK_ReturnPatient",objNull];};
if (isNull _patient) exitWith {false};
private _identity = [_patient,_body,_site] call ACME_fnc_medicationLineIdentity;
if (_identity isEqualTo []) exitWith {false};
if ([_patient,_body,_site] call ACME_fnc_medicationLineBloodBusy) exitWith {
    ["Blood is actively flowing through that line. Stop or finish the transfusion before pushing medication.",3,ACE_player,13] call ace_common_fnc_displayTextStructured;
    false
};
private _leash = missionNamespace getVariable ["ACM_circulation_AEDDistanceLimit",5];
if (((objectParent ACE_player) isNotEqualTo (objectParent _patient)) || {ACE_player distance _patient > _leash}) exitWith {false};
private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
private _idx = [_store] call ACME_fnc_skSelectedIndex;
if (_idx < 0 || {_idx >= count _store}) exitWith {false};
private _row = +(_store select _idx);
private _stable = _row param [11,"",[""]];
if (_stable == "") exitWith {false};
private _med = _row param [0,"",[""]];
private _size = _row param [1,10,[0]];
private _drug = _row param [2,0,[0]];
private _ns = _row param [4,0,[0]];
private _kind = _row param [6,"",[""]];
private _virtual = _kind in ["compoundB13","dilutionB13","epiMixB12"];
private _components = +(_row param [5,[],[[]]]);
if (!(_size isEqualType 0) || {!finite _size} || {!(_size in [1,3,5,10])}
    || {!(_drug isEqualType 0)} || {!finite _drug} || {_drug <= 0}
    || {!(_ns isEqualType 0)} || {!finite _ns} || {_ns < 0}) exitWith {false};
// The original one-shot path never allowed legacy non-source-funded mixtures. Preserve that guard here rather
// than letting a persistent push make an invalid row partly systemic before discovering the bad component.
if (!_virtual && {(_ns > 0.0005) || {!(_components isEqualTo [])}}) exitWith {false};
// Physical syringe magazines are stored in hundredths of a milliliter. Quantize the live row up front so every
// later stop/restart and the returned magazine agree on the exact same plunger volume.
if (!_virtual) then {_drug = (round (_drug*100))/100; _row set [2,_drug]; _store set [_idx,_row]; ACE_player setVariable ["ACME_narcStore",_store,false];};
private _total = (_drug + _ns) max 0;
if (_total <= 0 || {_total > _size + 0.001}) exitWith {false};
// Prevalidate every medication component and route before reserving the physical syringe or moving the plunger.
// A compound must therefore be all-valid or nothing starts; no batch can silently drop one drug later.
private _sourceParts = if (_components isEqualTo []) then {[[_med,_drug]]} else {+_components};
private _componentMl = 0;
private _componentsValid = !(_sourceParts isEqualTo []);
{
    if !(_x isEqualType [] && {count _x == 2}) then {_componentsValid=false;} else {
        _x params ["_source","_ml"];
        if !(_source isEqualType "" && {_source != ""} && {_ml isEqualType 0} && {finite _ml} && {_ml > 0}) then {_componentsValid=false;} else {
            private _class = _source + "_IV";
            if (_virtual && {_source in ["Adenosine","Amiodarone","Rocuronium"]}) then {_class = _source + "_IV";};
            if (_virtual && {!isClass (configFile >> "ACM_Medication" >> "Medications" >> _class)}) then {
                _class = if (isClass (configFile >> "ACM_Medication" >> "Medications" >> _source)) then {_source} else {_source + "_IV"};
            };
            private _conc = getNumber (configFile >> "ACM_Medication" >> "Concentration" >> _source >> "concentration");
            if (_conc <= 0 || {!([_class,true,true,_virtual] call ACME_fnc_medicationRouteAllowed)}) then {_componentsValid=false;};
            _componentMl = _componentMl + _ml;
        };
    };
} forEach _sourceParts;
if (!_componentsValid || {abs (_componentMl-_drug) > 0.001}) exitWith {false};
private _target = _total;
if (_kind == "epiMixB12") then {
    private _choice = uiNamespace getVariable ["ACME_SK_EpiDoseChoice",0];
    _target = ([1,2,_total] select ((_choice max 0) min 2)) min _total;
};

// B122 HUD label: use the actual medication component names, not the syringe tag or internal compound key.
private _medName = {
    params ["_m"];
    private _key = format ["STR_ACM_Circulation_Medication_%1",_m];
    private _name = localize _key;
    if (_name == "" || {_name == _key}) then {_name = _m;};
    _name
};
private _pushNames = [];
{
    private _source = _x param [0,"",[""]];
    if (_source != "") then {_pushNames pushBackUnique ([_source] call _medName);};
} forEach _sourceParts;
private _pushLabel = _pushNames joinString " + ";
if (_pushLabel == "") then {_pushLabel = [_med] call _medName;};

// Cache the exact open Narc Box syringe geometry before this display can be closed. The persistent corner overlay
// reuses these normalized values, which prevents the plunger from separating from the barrel at other resolutions.
private _nativeRect = _d getVariable ["ACME_SK_CarouselNativeRect",[0,0,safeZoneW*0.02,safeZoneH*0.17]];
private _nativeH = (_nativeRect param [3,safeZoneH*0.17,[0]]) max 0.0001;
private _overlayAspect = ((_nativeRect param [2,safeZoneW*0.02,[0]]) / _nativeH) max 0.035 min 0.45;
private _travel10 = _d getVariable ["ACME_SK_CarouselTravel10",_nativeH*0.195];
private _overlayTravelNorm = (_travel10 / _nativeH) max 0.02 min 0.40;

// The recommended grey value is guidance, not an implicit selection. A provider who does not type a duration
// gets the original 3-second push; an explicitly entered value still controls the persistent Hardcore transaction.
private _dur = 3;
private _durValid = true;
private _durCtrl = _d displayCtrl 84831;
if (!isNull _durCtrl && {!(_durCtrl getVariable ["ACME_SK_GhostActive",false])}) then {
    private _raw = ctrlText _durCtrl;
    if (_raw != "") then {
        _dur = parseNumber _raw;
        _durValid = _dur >= 1 && {_dur <= 300};
    };
};
if (!_durValid) exitWith {
    ["Push duration must be 1-300 seconds. Leave it blank to use 3 seconds.",2.5,ACE_player,13] call ace_common_fnc_displayTextStructured;
    false
};
private _magClass = ""; private _magContainer = objNull;
if (!_virtual) then {
    _magClass = format ["ACM_Syringe_%1_%2",_size,_med];
    private _ammo = round (_drug*100);
    {
        if (!isNull _x && {((magazinesAmmoCargo _x) findIf {(_x select 0) == _magClass && {(_x select 1) == _ammo}}) >= 0}) exitWith {_magContainer=_x;};
    } forEach [uniformContainer ACE_player,vestContainer ACE_player,backpackContainer ACE_player];
    if (isNull _magContainer || {_ammo <= 0}) exitWith {};
    _magContainer addMagazineAmmoCargo [_magClass,-1,_ammo];
};
if (!_virtual && {isNull _magContainer}) exitWith {false};
private _serial = (missionNamespace getVariable ["ACME_HCMedPushSerial",0]) + 1;
missionNamespace setVariable ["ACME_HCMedPushSerial",_serial];
private _session = format ["hcpush:%1:%2:%3",clientOwner,floor(diag_tickTime*1000),_serial];
private _job = createHashMapFromArray [
    ["medic",ACE_player],["patient",_patient],["bodyPart",toLowerANSI _body],["site",_site],["route","vascular"],
    ["identity",_identity],["stableId",_stable],["size",_size],["med",_med],["kind",_kind],["virtual",_virtual],
    ["label",_row param [3,"",[""]]],["pushLabel",_pushLabel],["barrelMarker",_row param [12,"",[""]]],
    ["overlayAspect",_overlayAspect],["overlayTravelNorm",_overlayTravelNorm],["magClass",_magClass],["magContainer",_magContainer],
    ["duration",_dur],["targetMl",_target],["rateMlSec",_target/(_dur max 0.01)],["pushedMl",0],["carryMl",0],
    ["unsentDelta",[0,0,[]]],["batchElapsed",0],["pendingAcks",0],["session",_session],["lastTick",diag_tickTime],
    ["lastSend",diag_tickTime],["nextUi",0],["flowing",true],["stopRequested",false],["finishRequested",false]
];
missionNamespace setVariable ["ACME_HCMedPushJob",_job];
uiNamespace setVariable ["ACME_SK_InjectionBusy",true];
uiNamespace setVariable ["ACME_SK_CarouselBusy",true];
uiNamespace setVariable ["ACME_SK_CarouselExpanded",true];
uiNamespace setVariable ["ACME_SK_CarouselCollapseAt",0];
{private _c=_d displayCtrl _x; if (!isNull _c) then {_c ctrlEnable false;};} forEach [84150,84151,84154,84470,84831];
private _old = missionNamespace getVariable ["ACME_HCMedPushPFH",-1];
if (_old >= 0) then {[_old] call CBA_fnc_removePerFrameHandler;};
private _h = [{call ACME_fnc_hardcorePushTick;},0.05] call CBA_fnc_addPerFrameHandler;
missionNamespace setVariable ["ACME_HCMedPushPFH",_h];
playSound "ACME_SyringePush";
[0] call ACME_fnc_skCarouselRender;
call ACME_fnc_skBodyActionRender;
true
