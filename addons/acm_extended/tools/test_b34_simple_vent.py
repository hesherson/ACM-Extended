"""Offline source contracts and delivery-model invariants; does not execute SQF/Arma."""
from pathlib import Path
import math
import random
import unittest

ROOT = Path(__file__).resolve().parents[1]
def source(name):
    return (ROOT / 'functions' / f'fn_{name}.sqf').read_text(encoding='utf-8')


def delivery(rr=12, comp=1, auto=0, leak=.03, dys=0, arrest=False):
    """B34 adult Simple branch plus existing pressure limit/alveolar accounting."""
    vt = 420 if arrest else 500
    pip = 8 + 12 * (vt / 500) / max(.1, comp)
    scale = min(1, max(0, 35-auto) / pip)
    vti = vt * (1-.2*dys) * scale
    vte = vti * (1-leak)
    mv = rr*vte/1000
    adequacy = min(1.6, max(0, rr*max(vte-150, 0)/4200))
    return vte, mv, adequacy, min(pip, max(0,35-auto))+auto


class SimpleVentDelivery(unittest.TestCase):
    def test_rr_changes_delivery_in_both_directions(self):
        low, normal, fast = [delivery(rr=x) for x in [4,12,30]]
        self.assertLess(low[2], .4)
        self.assertGreater(normal[2], .9)
        self.assertGreater(fast[1], normal[1])
        self.assertGreater(fast[2], 1)

    def test_lung_injury_reduces_delivered_volume_under_pressure_limit(self):
        healthy = delivery()
        injured = delivery(comp=.2)
        self.assertLess(injured[0], healthy[0])
        self.assertLess(injured[2], .4)
        self.assertLessEqual(injured[3], 35)

    def test_mainstem_and_leaks_still_matter(self):
        self.assertLess(delivery(comp=.1)[2], delivery(comp=.2)[2])
        self.assertLess(delivery(leak=.25)[2], delivery(leak=.03)[2])
        self.assertLess(delivery(dys=1)[2], delivery(dys=0)[2])

    def test_high_rate_can_trap_gas_even_with_fixed_ie(self):
        expiration = lambda rr: (60/rr)*2/3
        self.assertGreater(expiration(12), 1.8)
        self.assertLess(expiration(60), 1.8)
        self.assertLess(delivery(auto=20)[2], delivery(auto=0)[2])

    def test_arrest_uses_limited_breath_but_operator_rate_is_not_replaced(self):
        self.assertLess(delivery(arrest=True)[0], delivery()[0])
        self.assertAlmostEqual(delivery(rr=20,arrest=True)[1], 2*delivery(rr=10,arrest=True)[1])

    def test_extreme_injury_outputs_remain_bounded(self):
        rng = random.Random(34)
        for _ in range(500):
            out = delivery(rng.uniform(1,60), rng.uniform(.1,1), rng.uniform(0,20), rng.uniform(0,.75), rng.uniform(0,1))
            self.assertTrue(all(math.isfinite(x) and x>=0 for x in out))
            self.assertLessEqual(out[0],500)
            self.assertLessEqual(out[2],1.6)
            self.assertLessEqual(out[3],35)


class SimpleVentContracts(unittest.TestCase):
    def test_shared_resolver_never_writes_device_choices(self):
        s=source('ventEffectiveSettings')
        self.assertNotIn('setVariable',s)
        self.assertIn('ACME_vent_simpleMode", false',s)
        simple=s[s.index('if (_simple) exitWith'):s.index('private _mode =')]
        for key in ('ACME_vent_mode','ACME_vent_vt','ACME_vent_peep','ACME_vent_fio2','ACME_vent_alertPLimit','ACME_vent_weight'):
            self.assertNotIn(key,simple)
        self.assertIn('420',simple)
        self.assertIn('500',simple)
        self.assertIn('95',simple)
        self.assertNotIn('ACME_nrb_delivering',simple)

    def test_all_cross_system_dial_consumers_use_effective_settings(self):
        for f in ('ventDriveTick','ventAlarmTick','ventBatteryTick','blastLungTick','altitudeTick','oxygenDelivery','tbiHandle','hcVentTick','ventSimpleManualBreath'):
            self.assertIn('call ACME_fnc_ventEffectiveSettings',source(f),f)

    def test_simple_mode_uses_real_hardware_and_airway(self):
        s=source('ventDriveTick')
        for key in ('ACME_vent_circuit','ACME_vent_powerOn','ACME_vent_battery','ACME_vent_battExternal','ACME_vent_batteryEnabled'):
            self.assertIn(key,s)
        self.assertIn('if (_simple) then {_ifaceOK = _securedAirway;}',s)
        self.assertIn('_connected && _configured && _ifaceOK && _hardwareOK',s)
        case=s[s.index('case "SIMPLE":'):s.index('case "SIMV PC":')]
        self.assertIn('_mandatoryBpm = _bpm',case)
        self.assertNotIn('_spontBpm =',case)
        self.assertNotIn('cprRate',case)

    def test_cpr_cost_is_based_on_rate_in_simple(self):
        s=source('ventDriveTick')
        self.assertIn('_simple && {_cprBpm <= 10}',s)
        self.assertIn('linearConversion [10, 30, _cprBpm, 0, 1, true]',s)

    def test_no_stop_transition_or_circulation_shortcut(self):
        s=source('ventDriveTick')
        self.assertIn('if (_wasDriving || {(_patient getVariable ["ACM_breathing_BVM_provider", objNull]) isEqualTo _patient})',s)
        ptx=source('ptxContext')
        self.assertNotIn('ACME_vent_mode',ptx)
        self.assertIn('getVariable ["ACME_vent_driving", false]',ptx)
        self.assertIn('getVariable ["ACME_vent_connected", false]',ptx)
        for forbidden in ('ACME_fnc_rhythmSet','ACME_fnc_onCardiacArrest','setUnconscious'):
            self.assertNotIn(forbidden,s)

    def test_simple_manual_breath_runs_on_captured_patient_owner(self):
        request=source('ventManualBreath')
        self.assertIn('ACME_ventSimpleManualBreath',request)
        worker=source('ventSimpleManualBreath')
        for marker in ('!local _patient','_hops < 4','ACME_vent_custodyId','ACME_vent_recovering','ACME_ventRecoveryNear','ACME_vent_manualBreathT','ACME_fnc_procedureAllowed'):
            if marker=='ACME_ventRecoveryNear': marker='ACME_fnc_ventRecoveryNear'
            self.assertIn(marker,worker)
        self.assertNotIn('uiNamespace',worker)
        self.assertNotIn('ACME_vent_iface',worker)
        self.assertIn('ACME_ventSimpleManualBreath',source('ventCustodyInit'))

    def test_manual_request_is_epoch_timed_and_idempotent(self):
        s=source('ventSimpleManualBreath')
        for token in ('ACME_fnc_clinicalEpoch','_episodeId !=','_id in _receipts','count _receipts > 64'):
            self.assertIn(token,s)
        # _issued is a provider-client timestamp and must never be compared to the casualty owner's CBA clock.
        self.assertNotIn('_age > 3',s)
        self.assertIn('ACME_vent_simpleManualReceipts", _receipts, false',s)
        request=source('ventManualBreath')
        simple=request[request.index('if (missionNamespace getVariable ["ACME_vent_simpleMode"'):request.index('private _configured =')]
        self.assertNotIn('ACME_vent_manualGaugeT',simple)
        self.assertIn('ACME_ventSimpleManualAccepted',source('ventCustodyInit'))
        self.assertLess(s.index('_id in _receipts'),s.index('ACME_vent_manualBreathT'))

    def test_manual_volume_contributes_once_and_ages_out(self):
        s=source('ventDriveTick')
        self.assertIn('CBA_missionTime - (_x select 0) <= 60',s)
        self.assertIn('_mvDelivered = _mvDelivered + (_exhaled / 1000)',s)
        self.assertIn('_mvAlv = _mvAlv + ((_exhaled - 150) max 0)',s)
        self.assertIn('ACME_vent_effectiveRR", _effBpm + _simpleManualRR',s)
        # Automatic sensor accumulator does not count the manual RR twice.
        self.assertIn('_dt * ((_effBpm max 0) / 60)',s)
        self.assertIn('(count _times) + (count _manual)',s)
        low=delivery(rr=4)[2]
        exhaled=delivery()[0]
        with_manual=min(1.6,low+12*max(0,exhaled-150)/4200)
        self.assertGreater(with_manual,low)
        self.assertGreater(with_manual,1)
        self.assertIn('ACME_vent_simpleManualVolumes", []',source('ventPatientClear'))

    def test_circuit_loss_and_aftercare_gates(self):
        self.assertIn('_simple && {!(_patient getVariable ["ACME_vent_circuit", false])}',source('ventAlarmTick'))
        self.assertIn('[_medic, "ventilator", true] call ACME_fnc_procedureAllowed',source('ventDisconnectPatient'))
        self.assertIn('[_medic, "ventilator", true] call ACME_fnc_procedureAllowed',source('ventCustodyRequest'))

    def test_new_device_gate_before_inventory_mutation(self):
        for f in ('ventConnectPatient','ventCustodyRequest','ventInventoryLocal'):
            self.assertIn('[_medic, "ventilator"] call ACME_fnc_procedureAllowed',source(f))
        inv=source('ventInventoryLocal')
        self.assertLess(inv.index('call ACME_fnc_procedureAllowed'),inv.index('call ACME_fnc_treatmentSupplyTake'))

if __name__=='__main__': unittest.main()
