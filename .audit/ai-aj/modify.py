from pathlib import Path
F=Path('addons/acm_extended/functions')
def once(p,old,new):
 t=p.read_text();assert t.count(old)==1,(p,old,t.count(old));p.write_text(t.replace(old,new))
p=F/'fn_skConfirmInjection.sqf'
once(p,'private _remainingFrac = 0;','private _remainingFrac = 0;\nprivate _confirmedEpiMl = -1;')
once(p,'    _remainingFrac = ((((_total - _pushMl)', '    _confirmedEpiMl = _pushMl;\n    _remainingFrac = ((((_total - _pushMl)')
# The existing two delayed callbacks carry the same confirmed amount as the stroke.
t=p.read_text();assert t.count('"_validContext","_retire"]')==2;assert t.count('_validContext,_retire],')==2
t=t.replace('"_validContext","_retire"]','"_validContext","_retire","_confirmedEpiMl"]').replace('_validContext,_retire],','_validContext,_retire,_confirmedEpiMl],')
p.write_text(t)
once(p,'            [_bodyPart,_pushSec] call ACME_fnc_skInjectSite;', '''            // Use the same measured aliquot as the stroke, not a later dose-selector value.
            if (_confirmedEpiMl >= 0) then {
                [_bodyPart,_pushSec,_confirmedEpiMl] call ACME_fnc_skInjectSite;
            } else {
                [_bodyPart,_pushSec] call ACME_fnc_skInjectSite;
            };''')
p=F/'fn_skInjectSite.sqf'
once(p,'params ["_bodyPart", ["_pushSec", 3]];', 'params ["_bodyPart", ["_pushSec", 3], ["_confirmedEpiMl", -1, [0]]];')
once(p,'''    private _choice = uiNamespace getVariable ["ACME_SK_EpiDoseChoice", 0];
    private _ml = ([1, 2, _total] select _choice) min _total;''', '''    // Normal timed confirmation supplies its captured amount. Legacy direct calls
    // retain the live selector; the measured worker still rejects insufficient solution.
    private _ml = _confirmedEpiMl;
    if (_ml == -1) then {
        private _choice = uiNamespace getVariable ["ACME_SK_EpiDoseChoice", 0];
        _ml = ([1, 2, _total] select _choice) min _total;
    };''')
