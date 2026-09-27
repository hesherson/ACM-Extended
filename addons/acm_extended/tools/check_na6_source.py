#!/usr/bin/env python3
"""NA6 source contracts. Structural evidence only; this does not compile or execute SQF."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from source_scan import lex, matching, split_args, render

NEW_HARDCORE = {'ACME_hc_rhythm','ACME_hc_nrb','ACME_hc_blastLung','ACME_hc_vent'}
LABELS = {
 'ACME_hc_descriptors':'[HARDCORE] Clinical Descriptors',
 'ACME_hc_junc':'[HARDCORE] Junctional Wounds',
 'ACME_hc_dp':'[HARDCORE] Direct Pressure',
 'ACME_hc_chestSeal':'[HARDCORE] Chest Seal Mini-game',
 'ACME_hc_hpmk':'[HARDCORE] Rewarming',
 'ACME_hc_tbi':'[HARDCORE] TBI',
 'ACME_hc_circ':'[HARDCORE] Shock',
 'ACME_hc_medications':'[HARDCORE] Medications',
 'ACME_hc_vesicant':'[HARDCORE] Extravasation',
 'ACME_hc_hypothermia':'[HARDCORE] Hypothermia',
 'ACME_hc_flight':'[HARDCORE] Flight Physiology',
 'ACME_hc_rhythm':'[HARDCORE] Cardiac Rhythms',
 'ACME_hc_nrb':'[HARDCORE] NRB Oxygen',
 'ACME_hc_blastLung':'[HARDCORE] Blast Lung / ARDS',
 'ACME_hc_vent':'[HARDCORE] Ventilation',
}

def array_args(ts):
    pairs=matching(ts)
    if not ts or ts[0].value!='[' or pairs.get(0)!=len(ts)-1:
        raise ValueError('Expected one complete array')
    return split_args(ts,1,len(ts)-1,pairs)

def settings(text: str) -> dict[str,dict]:
    ts=lex(text);pairs=matching(ts)
    start=next(i+2 for i,t in enumerate(ts[:-2]) if t.value=='_settings' and ts[i+1].value=='=' and ts[i+2].value=='[')
    rows={}
    for entry in split_args(ts,start+1,pairs[start],pairs):
        args=array_args(entry)
        name=args[0][0].value
        if name in rows:raise ValueError('Duplicate setting '+name)
        title=array_args(args[2])[0][0].value
        rows[name]={'name':name,'type':render(args[1]),'label':title,'category':render(args[3]),
                    'default':render(args[4]),'global':render(args[5]),'callback':render(args[6]),
                    'args':[render(a) for a in args]}
    return rows

def effective_map(text: str) -> dict[str,str]:
    return dict(re.findall(r'(ACME_hcEff_\w+)\s*=\s*missionNamespace\s+getVariable\s*\["(ACME_hc_\w+)",\s*false\]',text))

def code(text: str) -> str:
    return render(lex(text))

def run(root: Path, baseline: Path | None = None) -> dict:
    reads=lambda rel:(root/rel).read_text(encoding='utf-8-sig')
    pre=reads('XEH_preInit.sqf');opts=settings(pre)
    rr=reads('overrides/fn_updateActions.sqf');rrc=code(rr)
    hc=reads('functions/fn_applyHardcore.sqf');hcc=code(hc)
    callbacks=reads('XEH_settings.hpp');post=reads('functions/fn_postInit.sqf')
    checks=[]
    def check(name,passed,detail=''):
        checks.append({'name':name,'passed':bool(passed),'detail':detail})
    check('version_config', 'version = "0.9.999r-73-NA6";' in reads('config.cpp'))
    check('version_postinit','ACME_infusion_version = "0.9.999r-73-NA6";' in post)
    check('master_checkbox_removed','ACME_hc_master' not in opts)
    check('master_no_executable_read','ACME_hc_master' not in hcc and '_hcAll' not in hcc)
    actual={k:v for k,v in opts.items() if k.startswith('ACME_hc_')}
    check('all_fifteen_individual_hardcore_settings',set(actual)==set(LABELS))
    check('labels_exact',all(opts.get(k,{}).get('label')==label for k,label in LABELS.items()))
    check('hardcore_no_colons',all(':' not in row['label'] for row in actual.values()))
    check('hardcore_category',all(row['category']=='[ _cSys , "Hardcore" ]' for row in actual.values()))
    check('hardcore_defaults_and_global_policy',all(row['default']=='false' and row['global']=='1' for row in actual.values()))
    check('hardcore_callbacks_apply_live',all('ACME_fnc_applyHardcore' in row['callback'] for row in actual.values()))
    enables={k:v for k,v in opts.items() if k.startswith('ACME_sys_') and '_cSys' in v['category']}
    check('twelve_system_enables_consolidated',len(enables)==12 and all(row['category']=='[ _cSys , "Systems" ]' for row in enables.values()))
    check('requested_systems_in_group',all(opts.get(k,{}).get('category')=='[ _cSys , "Systems" ]' for k in ['ACME_sys_junc','ACME_sys_dp','ACME_sys_chestSeal','ACME_sys_hang']))
    check('enable_subcategory_removed','[_cSys, "Enable"]' not in pre)
    mapping=effective_map(hc)
    check('independent_effective_flags',
          len(mapping)==14 and set(mapping.values())==(set(LABELS)-{'ACME_hc_descriptors'}))
    check('hc_initialization_gate_precedes_capture',hc.index('ACME_hcReady')<hc.index('if (isNil "ACME_hcBase_captured")'))
    check('postinit_ready_before_apply','ACME_hcReady = true;\ncall ACME_fnc_applyHardcore;' in post)
    check('no_frame_gap_reset','diag_frameNo' not in rrc and 'ACME_menuLastFrame' not in rrc)
    check('no_namespace_dropdown_state',not re.search(r'uiNamespace\s+(?:set|get)Variable\s*\[\s*"ACME_menuOpen"',rrc))
    check('display_open_read',"_display getVariable ['ACME_menuOpen', []]" in rr)
    check('display_open_write',"_menu setVariable ['ACME_menuOpen', _open]" in rr)
    check('target_context_reset',"_target isNotEqualTo (_display getVariable ['ACME_menuTarget', objNull])" in rr)
    check('header_target_guard',"_button getVariable ['ACME_menuRowTarget', objNull]" in rr and "_menu getVariable ['ACME_menuTarget', objNull]" in rr)
    check('no_recursive_refresh','call ace_medical_gui_fnc_updateActions' not in rrc)
    check('no_native_index_invalidation','ACM_gui_lastActionsList' not in rrc and 'ACM_gui_lastMenuSub' not in rrc)
    check('ordered_display_handle_read',"+(_display getVariable ['ACME_menuButtons', []])" in rr)
    check('ordered_display_handle_write',"_display setVariable ['ACME_menuButtons', _actionButtons]" in rr)
    check('replace_only_wrong_class',"(_ctrl getVariable ['ACME_menuButtonClass', '']) isNotEqualTo _buttonClass" in rr)
    check('ordered_handle_assignment','_actionButtons set [_shownIndex, _ctrl]' in rr)
    check('trim_only_unused_tail','_actionButtons select [_shownIndex]' in rr and '_actionButtons resize _shownIndex' in rr)
    check('real_action_reopen_only',bool(re.search(r"if \(_groupKey isEqualTo ''\) then \{\s*_ctrl ctrlAddEventHandler \['ButtonClick', \{ace_medical_gui_pendingReopen = true;\}\]",rr)))
    check('live_action_conditions','call _condition' in rr and 'call _cond2' in rr)
    check('live_inventory_counts','call ace_medical_gui_fnc_countTreatmentItems' in rr)
    check('short_native_rows_have_item_default', "['_items', []]" in rr)
    check('native_action_callback_retained',"_ctrl ctrlAddEventHandler ['ButtonClick', _statement]" in rr)
    check('native_triage_retained','call ace_medical_gui_fnc_updateTriageCard' in rr)
    check('site_relabel_and_colorblind_retained','call ACME_fnc_ivSiteRelabel' in rr and 'call ACME_fnc_cbColor' in rr)
    check('no_network_or_extra_polling',not any(x in rrc for x in ['CBA_fnc_globalEvent','CBA_fnc_targetEvent','remoteExec','CBA_fnc_addPerFrameHandler','publicVariable']))
    check('group_setting_change_is_idempotent', "(_display getVariable ['ACME_menuNestSetting', _nestEnabled]) isNotEqualTo _nestEnabled" in rr and 'setVariable ["ACME_menuOpen"' not in callbacks)
    check('accessibility_refresh_preserves_groups','ACME_menuOpen' not in code(reads('functions/fn_menuLeftAlignTick.sqf')))
    if baseline:
        orig=settings((baseline/'XEH_preInit.sqf').read_text())
        check('only_intended_settings_added_removed',set(orig)-set(opts)=={'ACME_hc_master'} and set(opts)-set(orig)==NEW_HARDCORE)
        keep=set(opts)&set(orig)
        check('all_retained_setting_types_defaults_policies_unchanged',all(all(opts[k][v]==orig[k][v] for v in ['type','default','global']) for k in keep))
        unchanged_args=True
        for k in keep:
            allowed={2,3} if k in LABELS or k in enables else set()
            if k in {'ACME_hc_tbi','ACME_hc_circ'}:allowed.add(6)
            aa=orig[k]['args'];bb=opts[k]['args']
            if len(aa)!=len(bb) or any(a!=b for i,(a,b) in enumerate(zip(aa,bb)) if i not in allowed):unchanged_args=False
        check('other_preinit_setting_fields_preserved',unchanged_args)
        bh=(baseline/'functions/fn_applyHardcore.sqf').read_text()
        # All tuning assignments, excluding effective flags and readiness, must remain identical tokens.
        assignment=lambda t: re.findall(r'\b(ACME_(?!hcEff_|hcReady)\w+)\s*=\s*([^;]+);',code(t))
        check('hardcore_numeric_tuning_unchanged',assignment(bh)==assignment(hc))
        bp=(baseline/'functions/fn_postInit.sqf').read_text()
        expected=bp.replace('0.9.999r-73-NA5','0.9.999r-73-NA6').replace('call ACME_fnc_applyHardcore;','ACME_hcReady = true;\ncall ACME_fnc_applyHardcore;')
        check('postinit_only_version_and_readiness_changed',post==expected)
        bcfg=(baseline/'config.cpp').read_text()
        check('config_only_version_changed',reads('config.cpp')==bcfg.replace('version = "0.9.999r-73-NA5";','version = "0.9.999r-73-NA6";'))
        digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        same=lambda ps:all((root/p.relative_to(baseline)).is_file() and digest(p)==digest(root/p.relative_to(baseline)) for p in ps)
        media=[p for p in baseline.rglob('*') if p.suffix.lower() in {'.paa','.ogg','.wav','.wss','.p3d','.rtm'}]
        chest=list((baseline/'functions').glob('fn_chestSeal*.sqf'))
        other=[p for sub in ['functions','overrides'] for p in (baseline/sub).glob('*.sqf') if p.relative_to(baseline).as_posix() not in {'functions/fn_applyHardcore.sqf','functions/fn_postInit.sqf','functions/fn_menuLeftAlignTick.sqf','overrides/fn_updateActions.sqf'}]
        check('all_media_preserved',same(media),f'{len(media)} assets')
        check('all_chest_seal_functions_preserved',same(chest),f'{len(chest)} functions')
        check('other_clinical_and_minigame_sqf_preserved',same(other),f'{len(other)} SQF files')
    return {'scope':__doc__,'checks':checks,'passed':sum(c['passed'] for c in checks),'failed':sum(not c['passed'] for c in checks),
            'settings':opts,'effective_map':mapping}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('addon',type=Path);p.add_argument('--baseline',type=Path);p.add_argument('--json',type=Path);args=p.parse_args()
    result=run(args.addon,args.baseline)
    for c in result['checks']:print(('PASS' if c['passed'] else 'FAIL')+' '+c['name']+(' '+c['detail'] if c['detail'] else ''))
    print(f"{result['passed']} passed, {result['failed']} failed. Source checks only.")
    if args.json:args.json.write_text(json.dumps(result,indent=2)+'\n')
    return int(result['failed']>0)
if __name__=='__main__':raise SystemExit(main())
