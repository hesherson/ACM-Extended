/* Convert a drawable ACM medication container classname back to its medication key without assuming ACM_ vs ACME_.
   B42 keeps the complete medication suffix rather than selecting one underscore-delimited token. That matters for
   medication keys that contain underscores, and it also preserves ACM's legacy Dimercaprol ampule, which inherits
   ACM_isVial = 1 even though its physical class is ACME_Ampule_Dimercaprol rather than ACME_Vial_*.
*/
params [["_class", "", [""]]];
if (_class == "") exitWith {""};
private _lower = toLowerANSI _class;
private _med = "";
{
    private _needle = _x;
    private _at = _lower find _needle;
    if (_at >= 0) exitWith {
        _med = _class select [_at + count _needle];
    };
} forEach ["_vial_", "_ampule_"];
_med
