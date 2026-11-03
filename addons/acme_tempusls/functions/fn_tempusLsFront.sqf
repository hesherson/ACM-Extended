params ["_o", "_px", "_pz", ["_lift", 0]];
private _bl = _o selectionPosition ["scr_bl", "Memory"];
private _ex = ((_o selectionPosition ["scr_br", "Memory"]) vectorDiff _bl) vectorMultiply (1 / 128.1);
private _ez = ((_o selectionPosition ["scr_tl", "Memory"]) vectorDiff _bl) vectorMultiply (1 / 96.1);
private _n = vectorNormalized (_ex vectorCrossProduct _ez);
private _m = _bl vectorAdd (_ex vectorMultiply (_px + 82.1)) vectorAdd (_ez vectorMultiply (_pz - 54.55)) vectorAdd (_n vectorMultiply (_lift / 1000));
[_o modelToWorldVisualWorld _m, _o vectorModelToWorldVisual _n]
