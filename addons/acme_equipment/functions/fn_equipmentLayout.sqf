/* Patient's anatomical frame: X right, Y toward head. Both monitor slots are independent. */
params ["_kind"];
switch (_kind) do {
    case "vent": {[0.65,0.70]};
    case "accu": {[-0.65,0.70]};
    case "pro": {[0.80,-0.10]};
    case "ls": {[1.30,-0.40]};
    default {[-0.85,-0.85]};
}
