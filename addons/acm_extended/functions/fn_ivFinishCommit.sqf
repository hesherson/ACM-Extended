/* B236. Owner-only extension/aspiration/dressing transaction.
   A live catheter UID, clinical epoch, provider, token and bounded deadline own
   every job. There is no whole-array write supplied by a client. */
params ["_patient","_medic","_phase","_uid","_action","_token","_epoch","_deadline",["_receipt",[]]];
if (isNull _patient || {!local _patient} || {isNull _medic}) exitWith {};
if !(_phase in ["begin","finish","cancel","advance","thread","retract"] && {_action in ["extension","flush","dressing","line","lock","field14","field16","removeLock","removeSecondary","removeExtension","removeDressing","removeLine"]}
    && {_uid isEqualType ""} && {_uid != ""} && {_token isEqualType ""} && {_token != ""}
    && {count _token <= 120} && {_deadline isEqualType 0} && {finite _deadline}
    && {_epoch isEqualType 0} && {finite _epoch} && {_receipt isEqualType []}) exitWith {};
private _reply = {
    params ["_status","_accepted",["_message",""],["_row",[]]];
    [_medic,"ivFinishReply",[_medic,_patient,_token,_status,_accepted,_message,_row]] call ACME_fnc_ownerDispatch;
};
private _field=_action in ["field14","field16"];
private _now=serverTime;
private _history=+(_patient getVariable ["ACME_IV_FinishReceipts",[]]);
_history=_history select {(_x param [5,0]) + 30 >= _now};
private _ri=_history findIf {(_x select 0)==_token};
private _record=if (_ri>=0) then {+(_history select _ri)} else {[]};
private _same=count _record>=10 && {(_record select 1) isEqualTo _medic}
    && {(_record select 2)==_uid} && {(_record select 3)==_action} && {(_record select 4)==_epoch}
    && {(_record select 5)==_deadline || {(_record select 8)=="cancel" && {!(_record select 6)}}};
if (_ri>=0 && {!_same}) exitWith {};
private _marks=+(_patient getVariable ["ACME_IV_Marks",[]]);
private _mi=_marks findIf {(_x param [4,""])=="hub" && {(_x param [14,""])==_uid}};
private _row=if (_mi>=0) then {+(_marks select _mi)} else {[]};
private _job=+(_row param [16,[]]);
private _state=+(_row param [15,[false,false,false,false]]);
private _publish = {
    if (_mi>=0) then {
        _marks set [_mi,_row];
        _patient setVariable ["ACME_IV_Marks",_marks,true];
        _patient setVariable ["ACME_IV_MarkVer",(_patient getVariable ["ACME_IV_MarkVer",0])+1,true];
    };
    _patient setVariable ["ACME_IV_FinishReceipts",_history,true];
};
private _bp=toLower (_row param [0,""]);
if (_bp=="ej") then {_bp="head";};
private _site=[_row param [10,""]] call ACME_fnc_ivSiteIndex;
private _valid=_epoch==([_patient] call ACME_fnc_clinicalEpoch) && {_mi>=0}
    && {_deadline>=_now} && {_deadline<=_now+(if (_field) then {100} else {40})} && {alive _medic}
    && {!(_medic getVariable ["ACE_isUnconscious",false])}
    && {([_medic,_patient] call ACME_fnc_patientInteractionDistance)<=3}
    && {(objectParent _medic) isEqualTo (objectParent _patient)}
    && {[_patient,_bp,0,_site] call ACM_circulation_fnc_hasIV};
// Cancellation can precede BEGIN in transit: keep a tombstone so a late BEGIN
// cannot start a removed display's procedure. It cannot cancel a different job.
if (_ri<0 && {count _history>=64}) exitWith {["rejected",false,"Please wait for the previous IV request."] call _reply;};
if (_phase=="cancel") exitWith {
    if (_same) then {_record set [8,"cancel"];_history set [_ri,_record];} else {
        _record=[_token,_medic,_uid,_action,_epoch,_now+30,false,"","cancel",""];
        _history pushBack _record;
    };
    if (count _job>0 && {(_job select 0)==_token}) then {_row set [16,[]];};
    call _publish;
    ["cancel",_record select 6,"",_row] call _reply;
};
if (_same && {(_record select 8)!="begin" || {_phase=="begin"}}) exitWith {
    // Repeated begin or completed finish: return the receipt, never consume or credit twice.
    [_record select 8,_record select 6,"",_row] call _reply;
};
// Every consumable requires an exact provider-issued scope, including patient,
// catheter UID, action, epoch and deadline. A missing replicated binding is not
// a negative acknowledgement: leave stock reserved and let the retry deliver it.
private _supplyState=1;
if (_phase=="begin" && {_action=="flush" || {_field}}) then {
    _supplyState=[_medic,_patient,_uid,_action,_token,_epoch,_deadline,_receipt] call ACME_fnc_ivSupplyScopeCheck;
};
if (_phase=="begin" && {_supplyState<0} && {_valid}) exitWith {};
if (_phase=="begin") exitWith {
    private _reason="The IV is no longer available.";
    private _plan=[false,_reason,"",0];
    if (_valid) then {
        _plan=[_state,_action,[_patient,_row] call ACME_fnc_ivFinishPatency,_row param [7,0]] call ACME_fnc_ivFinishPlan;
        if (count _job>0 && {(_job param [6,0])>=_now}) then {_plan=[false,"This IV is already being worked on.","",0];};
        if (_action=="flush" && {_supplyState!=1 || {count _receipt!=4}
            || {(_history findIf {(_x param [9,""])==(_receipt param [3,""]) && {_x param [6,false]}})>=0}}) then {
            _plan=[false,"A 10 mL saline flush is required.","",0];
        };
        if (_field) then {
            private _item=if (_action=="field14") then {"ACM_IV_14g"} else {"ACM_IV_16g"};
            if (_supplyState!=1 || {count _receipt!=4} || {(_receipt param [1,""])!=_item} || {(_receipt param [3,""])==""}
                || {(_history findIf {(_x param [9,""])==(_receipt param [3,""]) && {_x param [6,false]}})>=0}) then {
                _plan=[false,"The selected catheter is not available.","",0];
            };
        };
        if (count _history>=64) then {_plan=[false,"Please wait for the previous IV request.","",0];};
    };
    _plan params ["_ok","_message","_sequence","_duration"];
    _record=[_token,_medic,_uid,_action,_epoch,_deadline,_ok,_sequence,["rejected","begin"] select _ok,_receipt param [3,""]];
    _history pushBack _record;
    if (_ok) then {
        _row set [16,[_token,_medic,_action,_now,_duration,_sequence,_deadline]];
    };
    call _publish;
    [_record select 8,_ok,_message,_row] call _reply;
};
if (!_same || {count _job<7} || {(_job select 0)!=_token}) exitWith {["rejected",false,"The IV procedure has expired."] call _reply;};
// B234 manual stages must arrive in order. These messages never mutate venous state.
if (_field && {_valid}) then {
    _valid=([_state,_action,true,_row param [7,0]] call ACME_fnc_ivFinishPlan) select 0;
};
if (_phase in ["advance","thread","retract"]) exitWith {
    if (_field && {_valid}) then {
        private _old=_job param [7,1];
        private _want=switch (_phase) do {case "advance":{6};case "thread":{11};default{13};};
        private _required=switch (_phase) do {case "advance":{1};case "thread":{6};default{11};};
        if (_old==_required && {_now>=(_job select 3)+0.1}) then {
            _job set [7,_want];_row set [16,_job];call _publish;
        };
    };
};
if (_field && {_valid} && {(_job param [7,1])!=13}) exitWith {};
if (_valid && {_now<(_job select 3)+(_job select 4)}) exitWith {}; // cannot accelerate clinical completion.
private _message="";
private _primaryFilm=_action=="dressing" && {_state param [4,false]} && {(_state param [5,0])==0} && {!(_state param [0,false])};
if (_action in ["dressing","line"] && {!_primaryFilm} && {!([_patient,_row] call ACME_fnc_ivFinishPatency)}) then {_valid=false;};
if (_valid) then {
    switch (_action) do {
        case "removeLock";
        case "removeSecondary";
        case "removeExtension";
        case "removeLine": {
            _state=[_state,_action] call ACME_fnc_ivFieldTransition;
            [_patient,_bp,_site] call ACME_fnc_ivAccessoryUnplug;
        };
        case "lock";
        case "field14";
        case "field16";
        case "removeDressing";
        case "extension";
        case "dressing";
        case "line": {_state=[_state,_action] call ACME_fnc_ivFieldTransition;};
        case "flush": {
            private _success=(_job select 5)=="blood_return_flush" && {[_patient,_row] call ACME_fnc_ivFinishPatency};
            _state set [1,_success];
            if (_success) then {
                [_patient,"crystalloidCredit",[0.010]] call ACME_fnc_ownerDispatch;
                _message="Blood return observed. Flushed 10 mL.";
            } else {_message="No blood return. No fluid injected.";};
        };
    };
    _row set [15,_state];
} else {_message="The IV procedure was interrupted.";};
_row set [16,[]];_record set [8,"done"];_history set [_ri,_record];
call _publish;
["done",true,_message,_row] call _reply;
