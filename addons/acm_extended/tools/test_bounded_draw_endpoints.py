"""Actual native drag and overage-repair requests, not rendered pixels or vial debits.

Native/compound endpoint expectations remain separate from the UI tick's stock
repair. This deliberately does not make the UI tick a second drag-loop writer.
"""
import re
import pytest
from source_scan import lex, matching
from test_menu_death_lifecycle import ROOT, adapt, execute
from test_bounded_staged_push_contracts import contains

F=ROOT/'addons/acm_extended/functions'
NATIVE=ROOT/'addons/circulation/functions/fnc_Syringe_Draw.sqf'


def block(text, marker):
    start=text.index(marker)+len(marker)-1
    assert text[start]=='{'
    ts=lex(text[start:]); end=matching(ts)[0]
    return text[start+1:start+ts[end].offset]


def assert_native_endpoints(native, tick):
    drag=block(native,'if (GVAR(SyringeDraw_Moving)) then {')
    assert contains(drag,'["limit", _acmeMed, GVAR(SyringeDraw_DrawnAmount), _acmeDisplay] call ACME_fnc_vialSession')
    assert contains(drag,'_effectiveMax = (_effectiveMax max 0) min _size;')
    assert contains(drag,'if ((_effectiveMax - _amountDrawn) <= 0.015 && {_newY >= _bottomLimit - (2 * pixelH)}) then {_amountDrawn = _effectiveMax;};')
    assert contains(drag,'if (_amountDrawn <= 0.015 && {_newY <= GVAR(SyringeDraw_Ctrl_LimitTop) + (2 * pixelH)}) then {_amountDrawn = 0;};')
    assert contains(drag,'GVAR(SyringeDraw_DrawnAmount) = _amountDrawn;')
    repair=block(tick,'if (_stage == "") then {')
    assert contains(repair,'if (_drawnNow > _hardMax + 0.0001) then { [_hardMax, _d, false] call ACME_fnc_syringeDrawSetAmount; };')
    assert not contains(repair,'ACM_circulation_SyringeDraw_DrawnAmount =')
    assert not contains(repair,'setMousePosition')


def native_code():
    text=block(NATIVE.read_text(),'if (GVAR(SyringeDraw_Moving)) then {')
    text=re.sub(r'private _ctrlPlunger = [^;]+;', 'private _ctrlPlunger=1;',text)
    text=re.sub(r'private _ctrlPlungerVisual = [^;]+;', 'private _ctrlPlungerVisual=2;',text)
    text=text.replace('getResolution','[0,0,0,0,0,0.55]').replace('getMousePosition','_mouse')
    text=text.replace('SYRINGEDRAW_MOUSE_X','0.5').replace('pixelH','_pixel')
    text=text.replace('setMousePosition ', '_mouseWrites pushBack ')
    for var,key in [('_ctrlPlungerVisual','visual'),('_ctrlPlunger','hit')]:
        text=text.replace('ctrlPosition '+var,'(_positions get "'+key+'")')
        text=text.replace(var+' ctrlSetPosition ', '_positions set ["'+key+'", ')
        text=re.sub(r'(_positions set \["'+key+r'", \[[^;]+\]);',r'\1];',text)
        text=text.replace(var+' ctrlCommit 0;', '_commits pushBack "'+key+'";')
    text=re.sub(r'linearConversion (\[[^;\n]+\])',r'(\1 call _linear)',text)
    return adapt(text,component='circulation')


def setup(size, amount, pixel=0.001):
    return f'''
        // Numeric stand-in for the engine command not implemented by SQF-VM.
        private _linear={{params ["_a","_b","_v","_lo","_hi","_clamp"]; private _r=(_v-_a)/(_b-_a); if (_clamp) then {{_r=(_r max 0) min 1}}; _lo+(_hi-_lo)*_r}};
        private _size={size}; private _limit={size*0.6}; private _pixel={pixel};
        private _mouse=[0.5,{0.2+amount/size*0.2+0.026}];
        private _positions=createHashMapFromArray [["hit",[0.3,0.2,0.1,0.052]],["visual",[0.3,0.19,0.1,0.052]]];
        private _mouseWrites=[]; private _commits=[]; private _sessions=[];
        uiNamespace setVariable ["ACM_circulation_SyringeDraw_DLG",missionNamespace];
        ACM_circulation_SyringeDraw_Medication="Ketamine";
        ACM_circulation_SyringeDraw_MaxDose=99;
        ACM_circulation_SyringeDraw_DrawnAmount=0;
        ACM_circulation_SyringeDraw_Ctrl_LimitTop=0.2;
        ACM_circulation_SyringeDraw_Ctrl_LimitBottom=0.4;
        ACM_circulation_SyringeDraw_Ctrl_LimitTopMouse=0.226;
        ACM_circulation_SyringeDraw_Ctrl_PlungerAdjustment=0.01;
        ACME_fnc_vialSession={{_sessions pushBack +_this; _limit}};
    '''


@pytest.mark.parametrize('size',[1,3,5,10])
@pytest.mark.parametrize('position',['empty','near_empty','middle','near_limit','beyond_limit'])
def test_native_drag_preserves_exact_numeric_endpoints_and_physical_bounds(size,position):
    maximum=size*0.6
    amount={'empty':-1,'near_empty':0.01,'middle':maximum/2,'near_limit':maximum-0.01,'beyond_limit':maximum+1}[position]
    expected={'empty':0,'near_empty':0,'middle':maximum/2,'near_limit':maximum,'beyond_limit':maximum}[position]
    expected_y=0.2+min(max(amount,0),maximum)/size*0.2
    execute(setup(size,amount)+native_code()+f'''
        [abs(ACM_circulation_SyringeDraw_DrawnAmount-{expected})<0.000005,"native numeric endpoint wrong"] call _check;
        [abs(ACM_circulation_SyringeDraw_MaxDose-{maximum})<0.000005,"session cap lost"] call _check;
        [abs(((_positions get "hit") select 1)-{expected_y})<0.000005,"hit geometry crossed the physical bound"] call _check;
        [abs(((_positions get "visual") select 1)-{expected_y-0.01})<0.000005,"visible plunger lost its offset"] call _check;
        [_commits isEqualTo ["hit","visual"],"both plunger controls not updated"] call _check;
        [_sessions isEqualTo [["limit","Ketamine",0,missionNamespace]],"same-frame session lookup changed"] call _check;
    ''')


@pytest.mark.parametrize('amount,pixel',[(0.01,0.000001),(0.02,0.001),(0.59,0.000001),(0.58,0.01)])
def test_endpoint_snap_requires_both_volume_and_pixel_proximity(amount,pixel):
    execute(setup(1,amount,pixel)+native_code()+f'''
        [abs(ACM_circulation_SyringeDraw_DrawnAmount-{amount})<0.000005,"non-endpoint volume was rounded"] call _check;
    ''')


@pytest.mark.parametrize('amount,maximum,repair',[(0,1,False),(0.5,1,False),(1,1,False),(1.00005,1,False),(1.001,1,True),(4,0,True)])
def test_tick_only_delegates_staged_overage_repair(amount,maximum,repair):
    text=(F/'fn_skUiTick.sqf').read_text()
    start=text.index('private _drawnNow = ')
    tail=text[start:]
    end=tail.index('\n        };')
    code=adapt(tail[:end])
    execute(f'''
        private _d=missionNamespace;private _hardMax={maximum}; private _repairs=[];
        ACM_circulation_SyringeDraw_DrawnAmount={amount};
        ACME_fnc_syringeDrawSetAmount={{_repairs pushBack +_this;}};
    '''+code+f'''
        [_repairs isEqualTo {'[[_hardMax,_d,false]]' if repair else '[]'},"incorrect stock-repair handoff"] call _check;
        [ACM_circulation_SyringeDraw_DrawnAmount=={amount},"tick became a second direct amount writer"] call _check;
    ''')


@pytest.mark.parametrize('which,old,new',[
 ('native','_amountDrawn = 0;','_amountDrawn = 0.01;'),
 ('native','_amountDrawn = _effectiveMax;','_amountDrawn = _size;'),
 ('native','&& {_newY >= _bottomLimit - (2 * pixelH)}','&& {true}'),
 ('native','_effectiveMax = (_effectiveMax max 0) min _size;','_effectiveMax = _size;'),
 ('tick','[_hardMax, _d, false] call ACME_fnc_syringeDrawSetAmount;','ACM_circulation_SyringeDraw_DrawnAmount = _hardMax;'),
])
def test_endpoint_contract_rejects_regressions_despite_comment_decoys(which,old,new):
    native=NATIVE.read_text();tick=(F/'fn_skUiTick.sqf').read_text()
    assert_native_endpoints(native,tick)
    text=native if which=='native' else tick
    assert old in text;text=text.replace(old,new,1)+'\n/* '+old+' */\n'
    with pytest.raises(AssertionError):
        assert_native_endpoints(text if which=='native' else native,text if which=='tick' else tick)
