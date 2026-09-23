"""Apply the reviewed locality-scope refinement to the plain staged sources."""
from pathlib import Path
root=Path(__file__).parent
p=root/'locality.py';s=p.read_text()
changes=[
('test_lost_locality_retires_pfh_without_state_or_global_animation_writes','test_lost_locality_clears_private_state_without_global_animation_writes'),
('[_medic getVariable ["ACME_headElev_seqActive",false],"former owner cleared provider active flag"]','[!(_medic getVariable ["ACME_headElev_seqActive",true]),"former owner left private active flag"]'),
('=="{mode}" && {{(_medic getVariable ["ACME_headElev_medicAnimStage",99])=={stage}}},"former owner cleared mode/stage"','=="" && {{(_medic getVariable ["ACME_headElev_medicAnimStage",99])==-1}},"former owner left private mode/stage"'),
('[_medic getVariable ["ACME_DP_Paused",false] && {{_medic getVariable ["ACME_DP_TreatmentBusy",false]}},"former owner resumed pressure"]','[!(_medic getVariable ["ACME_DP_Paused",true]) && {{!(_medic getVariable ["ACME_DP_TreatmentBusy",true])}},"former owner left private pressure pause"]'),
('==_pin}},"former owner invalidated other controller"','==(_pin+1)}},"former owner lost private pin retirement"'),
('Former owner removes its PFH without publishing provider cleanup.','Former owner retires private state without publishing animation cleanup.'),
]
for old,new in changes:
    assert s.count(old)==1,old
    s=s.replace(old,new)
p.write_text(s)
p=root/'validate.py';s=p.read_text()
a=s.index('# AB: a former owner');b=s.index('assert digest(AFTER,SOURCE)',a)
s=s[:a]+'''# AB: retain all private retirement, but stop before any former-owner broadcast.
replace(SOURCE,'        ["ace_common_setAnimSpeedCoef", [_u, 1]] call CBA_fnc_globalEvent;',
    '        // Local-only bookkeeping above must retire even after locality is lost, so it cannot\\n'
    '        // strand this machine on a later return. Only the current owner may publish animation cleanup.\\n'
    '        if (!local _u) exitWith {};\\n'
    '        ["ace_common_setAnimSpeedCoef", [_u, 1]] call CBA_fnc_globalEvent;')
'''+s[b:]
s=s.replace('f9025fa419cb916e183906537625e09c65677b8097609aeebd2aeeff09ab8589','17b556412697829aa22f39eb60e3cb8686d8dbbccf9be8c32a3096a6b7c53fe2')
a=s.index('(AFTER/DOC_AB).write_text(');b=s.index('\nsha_ab=',a)
doc='''# Bounded AB: former-owner animation broadcast

Builds on bounded AA. The provider finalizer already cleared its private, non-public flags after losing locality, but also broadcast an animation-speed reset. That broadcast could reach the provider after another machine owned it.

The correction preserves every private retirement operation, including active/mode/stage cleanup, head-owned DP pause cleanup and pin-token retirement. It checks locality only before the existing global animation-speed event. Suppressing private retirement as well would leave stale locks on this machine, so that broader candidate was rejected during review. Normal local finalization is unchanged. Only headElevMedicSeq changes runtime, with no added timer, state key, network operation, animation or patient/gear rule.

Ten full-source execution cases use explicit locality/animation/network fixtures: 8 fail and 2 pass on original Y-Z runtime, all pass after correction. They cover both modes and four provider stages, no former-owner global event, intact private flag/pause/token cleanup, unchanged casualty placement, and still-local unconscious retirement. This does not migrate controllers, certify new-owner initialization, or handle ownership leaving and returning between PFH ticks. Those remain open. No live Arma or stable-release approval.

## Complete-checkout verification

'''
s=s[:a]+'(AFTER/DOC_AB).write_text('+repr(doc)+"+json.dumps(report,indent=2)+'\\n\\nThe full addon and root suites remain failing overall. No new skip or xfail. Fixtures record requests, not live UI, RTM, PhysX, networking or gear behavior. Protected snapshots are unchanged.\\n')"+s[b:]
s=s.replace('Bounded AB: retire former-owner provider PFH without cleanup writes','Bounded AB: suppress former-owner broadcast after private cleanup')
p.write_text(s)
for name in ('movement.py','locality.py','validate.py'):compile((root/name).read_text(),name,'exec')
print('Reviewed private-retirement refinement applied.')
