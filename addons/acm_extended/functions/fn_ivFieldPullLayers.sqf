/* Choose children by attachment hierarchy, not by the rendered row index. */
params ["_d","_row","_kind","_native"];
private _result=[[_native],_native];
{
    _x params ["_uid","_acc","_film","_lock","_secondary",["_baseFilm",controlNull]];
    if (_uid==(_row param [14,""])) exitWith {
        private _layers=switch (_kind) do {
            case "catheter": {[_native,_acc,_film,_lock,_secondary]+([[],[_baseFilm]] select (!isNull _baseFilm))};
            case "removeLock": {[_lock,_secondary,_acc,_film]+([[],[_baseFilm]] select (!isNull _baseFilm))};
            case "removeSecondary": {[_secondary,_acc,_film]};
            case "removeDressing": {[if ((_row param [15,[]]) param [2,false]) then {_film} else {_baseFilm}]};
            default {[_acc]};
        };
        if (_kind=="removeLine") then {
            _acc ctrlSetText "\acm_extended\ui\iv\finish\cursor_line_ca.paa";
            private _old=uiNamespace getVariable ["ACME_IV_PullExtra",controlNull];
            if (!isNull _old) then {ctrlDelete _old;};
            uiNamespace setVariable ["ACME_IV_PullExtra",controlNull];
            if ((_row param [15,[]]) param [0,false]) then {
                private _base=_d ctrlCreate ["ACME_IV_HubMark",-1];
                _base ctrlEnable false;_base ctrlSetText "\acm_extended\ui\iv\finish\extension_ca.paa";
                [_base,[_row,false] call ACME_fnc_ivFieldAccessoryRow] call ACME_fnc_ivFinishPose;
                _base ctrlShow true;uiNamespace setVariable ["ACME_IV_PullExtra",_base];
            };
        };
        _result=[_layers,_layers select 0];
    };
} forEach (_d getVariable ["ACME_IV_FinishCtrls",[]]);
_result
