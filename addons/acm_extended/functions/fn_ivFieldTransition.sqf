/* Pure dependency graph. Array length four is retained for legacy assemblies. */
params ["_state","_action"];
private _next=+_state;
private _lock=_next param [4,false];
switch (_action) do {
    case "lock": {_next=[false,false,false,false,true,0];};
    case "field14";
    case "field16": {
        private _covered=(_next param [2,false]) || {_next param [6,false]};
        _next=[false,false,false,false,true,[14,16] select (_action=="field16"),_covered];
    };
    case "removeLock": {_next=[false,false,false,false];};
    case "removeSecondary": {
        private _baseDressed=_next param [6,false];
        _next=[false,false,false,false,true,0];
        if (_baseDressed) then {_next pushBack true;};
    };
    case "removeExtension": {
        if (_lock) then {_next set [0,false];_next set [1,false];_next set [3,false];}
        else {_next=[false,false,false,false];};
    };
    case "removeDressing": {
        // Peel the outer dressing first; a second peel removes the retained primary film.
        if (_next param [2,false]) then {_next set [2,false];} else {if (count _next>6) then {_next set [6,false];};};
    };
    case "removeLine": {_next set [3,false];};
    case "extension": {_next set [0,true];if (_lock) then {_next set [1,false];};};
    case "dressing": {_next set [2,true];};
    case "line": {_next set [3,true];};
};
_next
