/* B235: state [extension,tested,finalDressed,line,lock,secondaryGauge,baseDressed].
   The secondary catheter is hardware only: never a new venous access or patency roll. */
params ["_state", "_action", "_patent", ["_baseGauge",16]];
_state params [["_extension",false],["_tested",false],["_dressed",false],["_line",false],["_lock",false],["_secondary",0],["_baseDressed",false]];
switch (_action) do {
    case "lock": {
        if (_lock) exitWith {[false,"The saline lock is already connected.","",0]};
        if (_extension || {_line} || {_dressed}) exitWith {[false,"Remove the existing accessories first.","",0]};
        [true,"","lock_attach",0.8]
    };
    case "field14";
    case "field16": {
        if (!_lock) exitWith {[false,"Attach a saline lock first.","",0]};
        if !(_baseGauge in [14,16]) exitWith {[false,"Field IV requires a 14g or 16g primary catheter.","",0]};
        if (_secondary>0) exitWith {[false,"A catheter is already seated in this lock.","",0]};
        if (_extension || {_line}) exitWith {[false,"Remove the downstream apparatus first.","",0]};
        if (!_dressed && {!_baseDressed}) exitWith {[false,"Secure the primary saline lock with Tegaderm first.","",0]};
        [true,"","field_insert",0.5]
    };
    case "extension": {
        if (_extension) exitWith {[false,"The extension is already connected.","",0]};
        if (_line) exitWith {[false,"Remove the tubing first.","",0]};
        [true,"","extension_attach",0.8]
    };
    case "flush": {
        if (!_extension && {!_lock}) exitWith {[false,"Connect the extension first.","",0]};
        if (_line) exitWith {[false,"Tubing is already connected to this port.","",0]};
        [true,"",["resisted_no_return","blood_return_flush"] select _patent,[4.48,5.92] select _patent]
    };
    case "dressing": {
        // This is mechanical fixation only. Cover the primary lock before field insertion;
        // do not require a flush or imply that a compromised venous access is repaired.
        if (_lock && {_secondary==0} && {!_extension}) exitWith {
            if (_dressed || {_baseDressed}) then {[false,"The primary lock dressing is already applied.","",0]}
            else {[true,"","tegaderm_apply",1.2]}
        };
        if ((!_extension && {!_lock}) || {!_tested}) exitWith {[false,"Check the line with the saline flush first.","",0]};
        if (!_patent) exitWith {[false,"Recheck the line with the saline flush.","",0]};
        if (_dressed) exitWith {[false,"The dressing is already applied.","",0]};
        [true,"","tegaderm_apply",1.2]
    };
    case "line": {
        if ((!_extension && {!_lock}) || {!_tested} || {!_dressed}) exitWith {[false,"Check and secure the connection first.","",0]};
        if (!_patent) exitWith {[false,"Recheck the line with the saline flush.","",0]};
        if (_line) exitWith {[false,"The tubing is already connected.","",0]};
        [true,"","iv_line_attach",1]
    };
    case "removeLock": {[_lock,if (_lock) then {""} else {"No saline lock is attached."},"",0.05]};
    case "removeSecondary": {[_secondary>0,if (_secondary>0) then {""} else {"No field catheter is attached."},"",0.05]};
    case "removeExtension": {[_extension,if (_extension) then {""} else {"No extension is attached."},"",0.05]};
    case "removeDressing": {[_dressed || {_baseDressed},if (_dressed || {_baseDressed}) then {""} else {"No dressing is attached."},"",0.05]};
    case "removeLine": {[_line,if (_line) then {""} else {"No tubing is attached."},"",0.05]};
    default {[false,"Select an IV tool.","",0]};
}
