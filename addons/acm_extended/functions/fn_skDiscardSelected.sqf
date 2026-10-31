/* B76: permanently discard the selected prepared syringe after the two-press confirmation.
   Virtual mixtures/flushes were source-funded when prepared, so discarding removes only their stored record.
   Native single-drug syringes also remove the exact matching filled magazine if it is still present. */
disableSerialization;
private _store = [ACE_player] call ACME_fnc_skStoreEnsureIds;
private _idx = [_store,false] call ACME_fnc_skSelectedIndex;
if (_idx < 0 || {_idx >= count _store}) exitWith {false};
private _entry = +(_store select _idx);
private _id = _entry param [11,"",[""]];
if (_id == "" || {(uiNamespace getVariable ["ACME_SK_DiscardArmedId",""]) != _id}) exitWith {false};
if ((_entry param [13,"",[""]]) == "inventoryB279") exitWith {[ACE_player,_entry] call ACME_fnc_skInventoryDiscard};
_entry params [["_med","",[""]],["_size",10,[0]],["_amt",0,[0]]];
private _kind = _entry param [6,"",[""]];
private _virtual = _kind in ["compoundB13","dilutionB13","epiMixB12"];
if (!_virtual && {_med != ""} && {_amt > 0}) then {
    private _magClass = format ["ACM_Syringe_%1_%2",_size,_med];
    private _ammo = round (_amt * 100);
    private _container = objNull;
    {
        if (!isNull _x && {((magazinesAmmoCargo _x) findIf {(_x select 0) == _magClass && {(_x select 1) == _ammo}}) >= 0}) exitWith {_container = _x;};
    } forEach [uniformContainer ACE_player,vestContainer ACE_player,backpackContainer ACE_player];
    if (!isNull _container && {_ammo > 0}) then {_container addMagazineAmmoCargo [_magClass,-1,_ammo];};
};
_store deleteAt _idx;
[ACE_player, _store] call ACME_fnc_narcStoreCommit;
uiNamespace setVariable ["ACME_SK_DiscardArmedId",""];
uiNamespace setVariable ["ACME_SK_PendingInjection",[]];
[_idx] call ACME_fnc_skAfterStoredRemoval;
call ACME_fnc_skBodyActionRender;
true
