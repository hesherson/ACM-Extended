private _off = missionNamespace getVariable ["ACME_hang_handOffset", [-0.171827,-0.0742273,-0.00905121]];
private _rot = missionNamespace getVariable ["ACME_hang_bagEuler", [-110.246,67.3435,179.392]];
private _lineEnd = missionNamespace getVariable ["ACME_hang_linePatientOffset", [0.399215,-0.0718271,0.12404]];
private _lineRot = missionNamespace getVariable ["ACME_hang_linePatientEuler", [-186.934,-84.1472,180]];
private _text = format [
    "HAND %1 | BAG OFFSET %2 | BAG EULER %3 | IV PATIENT END %4 | IV END EULER %5",
    missionNamespace getVariable ["ACME_hang_handSel", "RightHand"],
    _off,
    _rot,
    _lineEnd,
    _lineRot
];
[_text, 12, (call ACME_fnc_controlledProvider)] call ace_common_fnc_displayTextStructured;
