#!/usr/bin/env python3
"""Retained Batch 3 minute-volume and custody contracts/models; preset tests retired in B4. These tests DO NOT execute SQF."""
from pathlib import Path
import math
import re
import unittest
from source_scan import lex
R=Path(__file__).resolve().parents[1]
def source(name): return (R/'functions'/('fn_'+name+'.sqf')).read_text(encoding='utf-8-sig')
def tokens(name): return [t.value for t in lex(source(name))]
def limits(low=3.0, high=10.0):
    low=low if isinstance(low,(int,float)) and not isinstance(low,bool) and math.isfinite(low) else 3.0
    high=high if isinstance(high,(int,float)) and not isinstance(high,bool) and math.isfinite(high) else 10.0
    low=round(min(29.5,max(0,low)),1)
    return low,round(min(30,max(low+0.5,high)),1)
def mv(rr,vte): return max(rr,0)*max(vte,0)/1000

def alarms(rr,vte,low=3,high=10,driving=True,age=12):
    lo,hi=limits(low,high); v=mv(rr,vte)
    return (v<lo,v>=hi) if driving and age>=12 else (False,False)
def near(distance,provider_vehicle=None,patient_vehicle=None,alive=True):
    return alive and ((patient_vehicle is not None and patient_vehicle==provider_vehicle) or distance<=5)

class DeviceModel:
    """In-session allocation reference model, not an implementation of Arma inventory or transport."""
    def __init__(self):
        self.inventory={'supplier':1,'operator':1}; self.phase='empty'; self.provider='supplier'; self.operator='supplier'; self.receipts={}; self.adds=0
    def attach(self,actor='supplier',available=True):
        if self.phase!='empty' or not available or self.inventory.get(actor,0)<1:return False
        self.phase='taking'; self.provider=actor
        return True
    def take(self,ok=True):
        if 'take' in self.receipts:return self.receipts['take']
        if self.phase!='taking':return False
        if ok:self.inventory[self.provider]-=1
        self.receipts['take']=ok
        return ok
    def take_ack(self,ok):
        if self.phase!='taking':return
        self.phase='attached' if ok else 'empty'
    def request_return(self,dead=False,manual=None,distance=0,pv=None,tv=None):
        if self.phase!='attached':return False
        if manual is None and not dead:return False
        actor=manual or self.provider
        if not near(distance,pv,tv):return False
        self.recipient=actor;self.phase='returning';return True
    def give(self,container=True):
        if self.receipts.get('give',False):return True
        if self.phase!='returning' or not container:return False
        self.inventory[self.recipient]=self.inventory.get(self.recipient,0)+1
        self.adds+=1;self.receipts['give']=True;return True
    def give_ack(self,ok):
        if self.phase=='returning' and ok:self.phase='finalizing'
    def finalize(self):
        if self.phase=='finalizing':self.phase='done'

class MinuteVolumeSource(unittest.TestCase):
    def test_alarm_and_live_display_share_total_volume(self):
        for name in ['ventAlarmTick','ventPanelRefresh']:
            self.assertIn('ACME_fnc_ventMinuteVolume',tokens(name))
        self.assertIn('ACM_breathing_RespirationRate',source('ventMinuteVolume'))
        self.assertIn('ACME_vent_vte',source('ventMinuteVolume'))
        self.assertIn('/ 1000',source('ventMinuteVolume'))
    def test_alarm_does_not_compare_adequacy(self):
        self.assertNotIn('ACME_vent_mvAdequacy',source('ventAlarmTick'))
        self.assertIn('ACME_vent_mvAdequacy',source('ventDriveTick'))
    def test_defaults_are_absolute_ten_and_three(self):
        s=source('ventMVLimits')
        self.assertIn('"ACME_vent_alertMVhighLpmDefault", 10.0',s)
        self.assertIn('"ACME_vent_alertMVlowLpmDefault", 3.0',s)
    def test_boundary_and_settle_window(self):
        s=source('ventAlarmTick')
        for fragment in ['_mvLpm >= _mvHigh','_mvLpm < _mvLow','ACME_vent_alarmSettleSec", 12','_driving && {_settled}']:
            self.assertIn(fragment,s)
    def test_knob_writes_same_fields_as_reader(self):
        for key in ['ACME_vent_alertMVlowLpm','ACME_vent_alertMVhighLpm']:
            for f in ['ventPanelKnob','ventMVLimits','ventDeviceFields','clinicalFields']:
                with self.subTest(field=key,file=f):self.assertIn(key,source(f))
    def test_display_shows_units_and_both_editable_values(self):
        s=source('ventCustomLayout')
        self.assertIn('["val", 4, _mvLo toFixed 1, 3]',s)
        self.assertIn('["val", 4, _mvHi toFixed 1, 4]',s)
        self.assertIn('["txt", "L/min"',s)
    def test_old_percentage_state_is_not_read_for_alarm(self):
        for name in ['ventAlarmTick','ventMVLimits','ventPanelKnob','ventCustomLayout']:
            self.assertNotIn('getVariable ["ACME_vent_alertMVhigh",',source(name))
            self.assertNotIn('getVariable ["ACME_vent_alertMVlow",',source(name))
    def test_limits_guard_finite_type_and_crossing(self):
        s=source('ventMVLimits')
        for token in ['finite','isEqualType','max','min']:self.assertIn(token,tokens('ventMVLimits'))
        self.assertIn('_low + 0.5',s)

class MinuteVolumeModel(unittest.TestCase):
    def test_eight_point_five_does_not_trigger_high(self):self.assertEqual(alarms(17,500),(False,False))
    def test_ten_triggers_high(self):self.assertEqual(alarms(20,500),(False,True))
    def test_just_below_ten_does_not_trigger(self):self.assertFalse(alarms(19.99,500)[1])
    def test_edited_limit_clears_high(self):self.assertFalse(alarms(20,500,high=12)[1])
    def test_edited_limit_can_alarm_eight_point_five(self):self.assertTrue(alarms(17,500,high=8.5)[1])
    def test_low_is_effective(self):self.assertTrue(alarms(10,250,low=3)[0])
    def test_low_equality_not_below(self):self.assertFalse(alarms(10,300,low=3)[0])
    def test_settle_does_not_stop_measurement(self):
        self.assertEqual(mv(24,500),12)
        self.assertEqual(alarms(24,500,age=11.9),(False,False))
    def test_no_driving_no_minute_alarm(self):self.assertEqual(alarms(40,500,driving=False),(False,False))
    def test_invalid_limits_fall_back(self):self.assertEqual(limits('145',float('nan')),(3,10))
    def test_crossed_limits_are_separated(self):self.assertEqual(limits(12,10),(12,12.5))
    def test_ranges_are_clamped(self):self.assertEqual(limits(100,500),(29.5,30))
    def test_negative_readings_do_not_invert_sign(self):self.assertEqual(mv(-12,-500),0)

class CustodySource(unittest.TestCase):
    def test_supplier_is_separate_from_operator(self):
        self.assertIn('ACME_vent_supplier',source('ventCustodyAck'))
        self.assertIn('supplierUID',source('ventCustodyTick'))
        self.assertNotIn('ACME_vent_operator',source('ventCustodyTick'))
    def test_attach_removes_on_medic_owner_only(self):
        s=source('ventInventoryLocal');self.assertIn('!local _medic',s)
        self.assertEqual(s.count('call ACME_fnc_treatmentSupplyTake'),1)
        self.assertIn('["ACME_Ventilator"]',s)
        self.assertIn('call ACME_fnc_treatmentSupplyRefund',s)
        self.assertLess(s.index('call ACME_fnc_treatmentSupplyTake'),s.index('_ok = true;'))
    def test_allocate_before_removing(self):
        s=source('ventCustodyRequest');self.assertLess(s.index('_records set [_id, _r]'),s.index('call ACME_fnc_ventCustodyTick'))
        self.assertIn('_id in _records',s)
    def test_kill_event_and_bounded_active_scan(self):
        s=source('ventCustodyInit');self.assertIn('"EntityKilled"',s)
        t=source('ventCustodyTick');self.assertIn('keys _records',t);self.assertIn('removePerFrameHandler',t)
        self.assertNotIn('allUnits',tokens('ventCustodyTick'))
    def test_recovery_distance_includes_exact_five(self):self.assertIn('<= 5',source('ventRecoveryNear'))
    def test_vehicle_requires_nonnull_common_vehicle(self):
        s=source('ventRecoveryNear');self.assertIn('!isNull _vehicle',s);self.assertIn('(objectParent _medic) isEqualTo _vehicle',s)
    def test_body_deletion_retains_location(self):
        s=source('ventCustodyInit');self.assertIn('"EntityDeleted"',s);self.assertIn('getPosASL _unit',s);self.assertIn('objectParent _unit',s)
    def test_duplicate_inventory_receipt_precedes_mutation(self):
        s=source('ventInventoryLocal');self.assertLess(s.index('if !(_receipt isEqualTo []) exitWith'),s.index('_medic addItem'))
    def test_full_inventory_uses_worn_container(self):
        s=source('ventInventoryLocal')
        self.assertIn('addItemCargoGlobal ["ACME_Ventilator", 1]',s)
        for token in ['createVehicle','GroundWeaponHolder']:self.assertNotIn(token,tokens('ventInventoryLocal'))
    def test_return_finalization_has_identity_guard(self):
        s=source('ventPatientClear');self.assertIn('!= _id) exitWith',s)
        self.assertIn('"finalizing"',source('ventCustodyAck'))
    def test_clinical_teardown_prevents_restart(self):
        s=source('ventPatientClear');self.assertLess(s.index('"ACME_vent_circuit"'),s.index('"ACME_vent_driving"'))
        self.assertIn('ACME_vent_recovering',source('ventDriveTick'))
    def test_full_heal_retains_device_settings(self):
        s=source('clinicalReset');self.assertIn('ACME_fnc_ventDeviceFields',s)
        self.assertIn('_custody param [2, []]',s)
    def test_power_is_off_on_recovery(self):self.assertIn('"ACME_vent_powerOn", false',source('ventInventoryLocal'))
    def test_no_new_debug_rpt_calls(self):
        for f in ['ventCustodyTick','ventCustodyRequest','ventCustodyAck','ventInventoryLocal','ventCustodyInit']:
            self.assertNotIn('diag_log',tokens(f));self.assertNotIn('systemChat',tokens(f))
    def test_receipts_are_ephemeral_and_not_full_heal_cleared(self):self.assertIn('["ACME_vent_inventoryReceipts", "", false, false]',source('clinicalFields'))
    def test_device_defaults_do_not_leak_from_previous_patient(self):
        s=source('ventCustodyAck');self.assertIn('{_patient setVariable [_x, nil, true];} forEach _fields',s)
        self.assertIn('{_medic setVariable [_x, nil, true];} forEach _fields',source('ventInventoryLocal'))
    def test_return_clears_device_state_from_corpse(self):
        self.assertIn('forEach ([] call ACME_fnc_ventDeviceFields)',source('ventPatientClear'))
    def test_no_settings_borrowed_from_another_panel_viewer(self):self.assertIn('ACME_vent_custodyId',source('ventPanelOpen'))

class CustodyModelTests(unittest.TestCase):
    def deployed(self):
        d=DeviceModel();self.assertTrue(d.attach());d.take_ack(d.take());return d
    def test_five_meters_qualifies(self):self.assertTrue(near(5))
    def test_over_five_waits(self):self.assertFalse(near(5.01))
    def test_different_vehicles_use_distance(self):self.assertFalse(near(8,'a','b'))
    def test_same_vehicle_ignores_seat_distance(self):self.assertTrue(near(15,'heli','heli'))
    def test_two_null_vehicle_pointers_do_not_match(self):self.assertFalse(near(15))
    def test_no_return_to_dead_supplier(self):self.assertFalse(near(0,alive=False))
    def test_other_panel_operator_does_not_gain_device(self):
        d=self.deployed();d.operator='operator';d.request_return(dead=True);d.give_ack(d.give());d.finalize()
        self.assertEqual(d.inventory,{'supplier':1,'operator':1});self.assertEqual(d.adds,1)
    def test_second_simultaneous_attach_cannot_take_item(self):
        d=DeviceModel();self.assertTrue(d.attach());self.assertFalse(d.attach('operator'));self.assertEqual(d.inventory['operator'],1)
    def test_failed_take_cannot_create_return(self):
        d=DeviceModel();d.attach();d.take_ack(d.take(False));self.assertFalse(d.request_return(dead=True));self.assertFalse(d.give())
    def test_repeated_take_before_ack_removes_once(self):
        d=DeviceModel();d.attach();d.take();d.take();self.assertEqual(d.inventory['supplier'],0)
    def test_far_death_then_approach(self):
        d=self.deployed();self.assertFalse(d.request_return(dead=True,distance=6));self.assertTrue(d.request_return(dead=True,distance=5))
    def test_live_patient_does_not_auto_return(self):self.assertFalse(self.deployed().request_return(dead=False))
    def test_manual_return_can_go_to_treating_provider(self):
        d=self.deployed();d.request_return(manual='operator');d.give_ack(d.give());d.finalize();self.assertEqual(d.inventory['operator'],2)
    def test_duplicate_return_ack_and_kill_do_not_duplicate_item(self):
        d=self.deployed();d.request_return(dead=True);d.give();d.give();d.give_ack(True);d.give_ack(True);d.finalize()
        self.assertEqual(d.adds,1);self.assertFalse(d.request_return(dead=True))
    def test_missing_container_keeps_debt_until_available(self):
        d=self.deployed();d.request_return(dead=True);self.assertFalse(d.give(False));self.assertEqual(d.phase,'returning')
        d.give_ack(d.give());d.finalize();self.assertEqual(d.adds,1)

if __name__=='__main__':unittest.main()
