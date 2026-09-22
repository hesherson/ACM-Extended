"""Audit-branch-only preparation of mechanical historical-test migrations.

Applies opt-in source readers and release consistency checks to the pinned checkout.
No production path is written. Every hand-reviewed change follows in a plain patch.
The validation workflow verifies the final complete Git tree before running tests.
"""
import ast
import json
from pathlib import Path
import sys
ROOT=Path(sys.argv[1]).resolve()
TOOLS=ROOT/'addons/acm_extended/tools'
VERSION_TARGETS = {'test_b17_release.py': ['test_version_pair'], 'test_b18_ventway.py': ['test_version_pair'], 'test_b19_vials_pea_artifact.py': ['test_version_pair'], 'test_b20_vent_debug_narcbox.py': ['test_version_pair'], 'test_b21_rhythm_sync.py': ['test_version'], 'test_b25_vials_epi_iv_angles.py': ['test_version_pair'], 'test_b26_corrected_release.py': ['test_version_pair'], 'test_b27_junctional_cpr_bvm.py': ['test_version_pair'], 'test_b28_hpmk_acre.py': ['test_version'], 'test_b36_ej_orientation.py': ['test_requested_public_version_is_consistent'], 'test_b39_runtime_stamp_and_spawn.py': ['test_config_is_r3', 'test_runtime_version_comes_from_config'], 'test_b40_animation_audit.py': ['test_runtime_is_b41_r5'], 'test_b41_ui_airway_medication.py': ['test_b41_runtime_stamp'], 'test_b42_medication_menu_dp.py': ['test_b42_runtime_stamp'], 'test_b43_medication_recovery.py': ['test_b43_runtime_stamp'], 'test_b44_requested_fixes.py': ['test_b44_version'], 'test_b45_medication_steth_io_logs.py': ['test_b45_version_stamp'], 'test_b46_narcbox_medication_render.py': ['test_b46_version_stamp'], 'test_b47_animation_contracts.py': ['test_version_batch'], 'test_b48_medication_animation_orientation.py': ['test_version_batch'], 'test_b49_intubation_obtunded.py': ['test_version_batch'], 'test_b50_animation_medication_prepared.py': ['test_version_batch'], 'test_b51_medication_display_syringe_art.py': ['test_version_and_batch'], 'test_b57_pose_rules_narcbox_cohesion.py': ['test_version_is_r21_b57'], 'test_b58_syringe_carousel_tags.py': ['test_version_b58'], 'test_b59_shared_syringe_body_carousel.py': ['test_b59_version_and_registration'], 'test_b60_dynamic_syringe_body_tandem.py': ['test_b60_version_and_new_functions_registered'], 'test_b61_carousel_bodymap_refinement.py': ['test_b61_version_stamp'], 'test_b62_tag_editor_carousel_layout.py': ['test_b62_version_stamp_and_functions'], 'test_b63_tag_carousel_interaction.py': ['test_b63_version_stamp'], 'test_b64_syringe_tag_carousel_refinement.py': ['test_b64_version_stamp'], 'test_b66_syringe_carousel_main_tag.py': ['test_b66_version_stamp'], 'test_b67_cardiac_rosc_audit.py': ['test_b67_build_stamp_and_single_rosc_registration'], 'test_b68_syringe_tag_push_layout.py': ['test_b68_version_stamp'], 'test_b69_narcbox_carousel_visibility.py': ['test_b69_version_stamp'], 'test_b70_semifowler_bvm_thora_syringe.py': ['test_b70_version_stamp'], 'test_b71_tag_head_intubation.py': ['test_version_batch'], 'test_b72_chest_tag_head_provider.py': ['test_version_batch'], 'test_b73_syringe_tag_vial_carousel_anim.py': ['test_version_batch'], 'test_b75_direct_pressure_tag_flush.py': ['test_version_batch'], 'test_b76_carousel_push_memory.py': ['test_version'], 'test_b78_tag_hover_unification.py': ['test_version'], 'test_b79_version_milestone.py': ['test_b79_version_milestone'], 'test_b90_critical_provider_cpr_bvm.py': ['test_release_stamp'], 'test_na8_5_batch10.py': ['test_versions'], 'test_na8_5_batch8.py': ['test_version_pair'], 'test_na8_5_batch9.py': ['test_current_versions_agree']}


def imports_after_header(source, statement):
    tree=ast.parse(source); line=0
    for node in tree.body:
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str) and line==0:
            line=node.end_lineno
        elif isinstance(node,ast.ImportFrom) and node.module=='__future__':line=node.end_lineno
        else:break
    lines=source.splitlines(keepends=True); lines.insert(line,statement+'\n')
    return ''.join(lines)


def offsets(source):
    result=[0]
    for line in source.splitlines(keepends=True):result.append(result[-1]+len(line))
    return result

changed=[]
for path in sorted(list(TOOLS.glob('test_b*.py'))+list(TOOLS.glob('test_na*.py'))):
    source=path.read_text(); tree=ast.parse(source)
    if not any(t in source for t in ['postInit','debugMenu','overrides','fn_updateActions']):continue
    positions=offsets(source); edits=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='read_text':
            expression=ast.get_source_segment(source,node.func.value)
            call=ast.get_source_segment(source,node)
            args=call[call.index('.read_text(')+len('.read_text('):-1]
            replacement='read_source('+expression+(', '+args if args else '')+')'
            edits.append((positions[node.lineno-1]+node.col_offset,positions[node.end_lineno-1]+node.end_col_offset,replacement))
    if not edits:continue
    for start,end,replacement in sorted(edits,reverse=True):source=source[:start]+replacement+source[end:]
    source=imports_after_header(source,'from historical_source import read_source')
    assert sum(isinstance(n,ast.Assert) for n in ast.walk(tree)) == sum(isinstance(n,ast.Assert) for n in ast.walk(ast.parse(source)))
    path.write_text(source); changed.append(path.name)
assert len(changed)==78,changed

release_edits=0
for name, functions in VERSION_TARGETS.items():
    path=TOOLS/name; source=path.read_text(); tree=ast.parse(source); positions=offsets(source); edits=[]
    for function in ast.walk(tree):
        if not isinstance(function,(ast.FunctionDef,ast.AsyncFunctionDef)) or function.name not in functions:continue
        for node in ast.walk(function):
            if not (isinstance(node,ast.Assert) or (isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr.startswith('assert'))):continue
            strings=[n.value for n in ast.walk(node) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
            old=any(any(v in text.replace('\\','') for v in ['0.9.999','1.0.100','1.2.0-r0','ACME_buildBatch = "B']) for text in strings)
            if not old:continue
            edits.append((positions[node.lineno-1]+node.col_offset,positions[node.end_lineno-1]+node.end_col_offset,'assert_release_identity()'))
    if not edits:continue
    for start,end,replacement in sorted(edits,reverse=True):source=source[:start]+replacement+source[end:]
    if 'from historical_source import read_source' in source:
        source=source.replace('from historical_source import read_source','from historical_source import read_source, assert_release_identity',1)
    else:source=imports_after_header(source,'from historical_source import assert_release_identity')
    ast.parse(source);path.write_text(source);release_edits+=len(edits)
assert release_edits==111,release_edits
print('Mechanical changes: 78 opt-in locator modules, 111 obsolete release assertions.')
