from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="strict")


def test_duration_row_layout_executes_and_tracks_push_button():
    s = read("functions/fn_skBodyActionRender.sqf")
    assert "\n{\n    private _durGap" not in s
    assert "private _pushRect = +(ctrlPosition _btn);" in s
    assert "_durLabel ctrlSetPosition [_pushRect select 0, _durY, _labelW, _durH];" in s
    assert "private _editRect = [(_pushRect select 0) + _labelW + _durGap, _durY, _editW, _durH];" in s
    assert "_durEdit ctrlSetPosition _editRect;" in s


def test_blank_or_recommended_placeholder_keeps_push_enabled():
    s = read("functions/fn_skBodyActionRender.sqf")
    assert 'private _hasTypedDuration = !_ghost && {_rawDur != ""};' in s
    assert 'private _numDur = if (_hasTypedDuration) then {parseNumber _rawDur} else {3};' in s
    assert '_validPushTime = !_hasTypedDuration || {_numDur >= 1 && {_numDur <= 300}};' in s


def test_normal_push_blank_defaults_to_three_seconds():
    s = read("functions/fn_skConfirmInjection.sqf")
    assert "private _pushSec = 3;" in s
    assert 'if (_raw != "") then {' in s
    assert "if (_pushDurationValid) then {_pushSec = _typed;};" in s
    assert "Leave it blank to use 3 seconds." in s


def test_hardcore_push_blank_defaults_to_three_seconds():
    s = read("functions/fn_hardcorePushStart.sqf")
    assert "private _dur = 3;" in s
    assert "private _durValid = true;" in s
    assert 'if (_raw != "") then {' in s
    assert '_durValid = _dur >= 1 && {_dur <= 300};' in s


def test_recommended_times_remain_display_only_gray_guidance():
    body = read("functions/fn_skBodyActionRender.sqf")
    rec = read("functions/fn_medicationSuggestedPushSec.sqf")
    assert 'call ACME_fnc_medicationSuggestedPushSec' in body
    assert '_durHint ctrlSetTextColor [0.56,0.58,0.62,0.82];' in body
    assert '_durHint ctrlSetText _suggested;' in body
    assert '_durHint ctrlEnable false;' in body
    assert '_durEdit ctrlSetText _suggested;' not in body
    assert '["ACME_SK_GhostActive",true]' not in body
    for med, seconds in [
        ("Adenosine", 3),
        ("Ketamine", 30),
        ("CalciumChloride", 300),
        ("CalciumGluconate", 120),
        ("Amiodarone", 300),
        ("Norepinephrine", 60),
        ("Esmolol", 60),
        ("Lidocaine", 60),
        ("Magnesium", 300),
        ("Propofol", 30),
        ("Midazolam", 60),
        ("Fentanyl", 30),
        ("Morphine", 60),
        ("Rocuronium", 30),
    ]:
        assert f'case "{med}": {{{seconds}}};' in rec


def test_seconds_edit_preserves_focus_and_does_not_swallow_keys():
    body = read("functions/fn_skBodyActionRender.sqf")
    tick = read("functions/fn_skUiTick.sqf")
    assert 'ctrlAddEventHandler ["SetFocus"' in body
    assert 'ctrlAddEventHandler ["KeyDown"' not in body
    assert 'call ACME_fnc_skBodyActionRender;' not in body.split('ctrlAddEventHandler ["KeyUp"', 1)[1].split('}];', 1)[0]
    assert 'ctrlIDC _focus) != 84831' not in tick
    assert 'call ACME_fnc_skBodyActionRender;' in tick
    assert 'if (!_durFocused && {(ctrlPosition _durEdit) isNotEqualTo _editRect})' in body
    assert 'if ((ctrlEnabled _durEdit) isNotEqualTo _durationEnabled)' in body
    assert 'if ((ctrlShown _durEdit) isNotEqualTo _showDuration)' in body


def test_hardcore_push_plunger_tracks_authoritative_remaining_volume():
    carousel = read("functions/fn_skCarouselRender.sqf")
    tick = read("functions/fn_hardcorePushTick.sqf")
    assert 'ACME_SK_PushAnimPFH' in carousel
    assert '_normalPushAnimActive' in carousel
    assert 'if !(_normalPushAnimActive && {_slot == 2})' in carousel
    assert 'private _plUi = _open displayCtrl 84422;' in tick
    assert '_plUi ctrlSetPosition' in tick
    assert '_remainUi' in tick


def test_seconds_control_is_explicitly_editable_and_click_focuses_without_reset():
    config = read("config.cpp")
    block = config.split("class ACME_SK_PushDurationEdit:", 1)[1].split("};", 1)[0]
    for prop in ("type = 2;", "style = 0;", "canModify = 1;", "maxChars = 3;"):
        assert prop in block
    body = read("functions/fn_skBodyActionRender.sqf")
    assert 'ctrlCreate ["ACME_SK_PushDurationEdit",84831]' in body
    mouse = body.split('ctrlAddEventHandler ["MouseButtonDown",', 1)[1].split('}];', 1)[0]
    assert "ctrlSetFocus _ctrl" in mouse
    assert "ctrlSetText" not in mouse
    focus = body.split('ctrlAddEventHandler ["SetFocus",', 1)[1].split('}];', 1)[0]
    assert "ctrlSetText" not in focus
    assert '["ACME_SK_CarouselHeldDir",0]' in focus
    assert 'ctrlAddEventHandler ["KillFocus"' not in body


def test_carousel_shortcuts_yield_to_every_edit_control_before_processing_keys():
    source = read("functions/fn_skInject.sqf")
    for event in ("KeyDown", "KeyUp"):
        handler = source.split(f'displayAddEventHandler ["{event}",', 1)[1].split('}];', 1)[0]
        assert handler.index("ctrlType _focus == 2") < handler.index("switch (_key)")
        assert '["ACME_SK_CarouselHeldDir",0]' in handler
        assert '["ACME_SK_CarouselRepeatAt",0]' in handler


def test_push_duration_is_provider_owned_and_persists_per_syringe():
    body = read("functions/fn_skBodyActionRender.sqf")
    assert 'ACME_SK_PushDurationDrafts' in body
    assert 'ACME_SK_PushDurationFor' in body
    assert 'ACME_HCMedPushDefaultFor' not in body

    keyup = body.split('ctrlAddEventHandler ["KeyUp", {', 1)[1].split('}];', 1)[0]
    assert '_drafts set [_draftId,_clean];' in keyup

    # Routine pending-injection rendering may update only the grey recommendation, never the edit value.
    pending = body.split('if (_pending isEqualType [] && {count _pending >= 3}) then {', 1)[1]
    pending = pending.split('private _total =', 1)[0]
    assert '_durHint ctrlSetText _suggested;' in pending
    assert '_durEdit ctrlSetText' not in pending

    # An active Hardcore transaction must not overwrite the draft with its running/default duration.
    hc = body.split('if (_hcOwns) exitWith {', 1)[1].split('if (_pending isEqualType []', 1)[0]
    assert '_runningDuration' not in hc
    assert '_durEdit ctrlSetText' not in hc

    # The only post-creation text replacement is the one-time restore when the stable syringe ID changes.
    after_create = body.split('private _entry = _store select _idx;', 1)[1]
    assert 'private _restoredDuration = _durationDrafts getOrDefault [_id,""];' in after_create
    assert 'if (_durationFor != _id) then {' in after_create
    assert '_durationDrafts set [_durationFor,ctrlText _durEdit];' in after_create


def test_duration_row_is_reserved_before_carousel_hit_areas_are_measured():
    source = read("functions/fn_skCarouselRender.sqf")
    assert source.index("call ACME_fnc_skBodyActionRender;") < source.index("private _hoverBottom")
    assert 'ctrlShown _durationCtrl}) then {_durationCtrl} else {_actionCtrl}' in source
    assert 'ctrlPosition _boundCtrl' in source
    assert '_zone ctrlSetPosition [_rx,_hoverTop,_rw,_zoneH]' in source
    assert 'min _hoverBottom' in source
    assert '(_display displayCtrl 84832) ctrlShow false;' in read("functions/fn_skSetView.sqf")
