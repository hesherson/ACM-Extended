/* Exact native fluid-card viewport, including its centered scrollbar gutter. */
params ["_layout"];
private _rect = +(_layout select 0);
private _canvasW = safeZoneW min (safeZoneH * 1.7777778);
private _viewportW = (_rect select 2) min (_canvasW * 0.202);
private _gap = (safeZoneH * 0.006 * (pixelW / pixelH)) max (5 * pixelW);
_rect set [0,(_rect select 0) + (((_rect select 2) - _viewportW) / 2)];
_rect set [2,(_viewportW - 3 * pixelW - _gap) max (10 * pixelW)];
_rect
