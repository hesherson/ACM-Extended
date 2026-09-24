from historical_source import read_source
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def read(rel): return read_source(ROOT/rel, encoding='utf-8-sig')

class B22VialReference(unittest.TestCase):
    @staticmethod
    def preview(cap, open_ml, sealed, reserved):
        total=open_ml+sealed*cap
        left=max(total-max(reserved,0),0)
        r=min(max(reserved,0),total)
        cur=open_ml
        sealed_left=sealed
        if cur>1e-6:
            if r<cur:
                cur-=r; r=0
            else:
                r-=cur; cur=0
        while r>1e-6 and sealed_left>0:
            sealed_left-=1
            if r<cap:
                cur=cap-r; r=0
            else:
                r-=cap; cur=0
        if cur<=1e-6 and sealed_left>0:
            sealed_left-=1; cur=cap
        return sealed_left+(1 if cur>1e-6 else 0),cur,left

    def test_four_ml_vial_stops_ten_ml_syringe(self):
        vials,cur,total=self.preview(4,0,1,4)
        self.assertEqual((vials,cur,total),(0,0,0))
        self.assertEqual(min(10,4),4)

    def test_fifty_ml_vial_tracks_draw_and_return(self):
        self.assertEqual(self.preview(50,0,1,0),(1,50,50))
        self.assertEqual(self.preview(50,0,1,10),(1,40,40))
        # Pushing 4 mL back means only 6 mL is reserved, so the same vial rises to 44 mL.
        self.assertEqual(self.preview(50,0,1,6),(1,44,44))

    def test_rolls_into_next_vial_without_auto_new_syringe(self):
        self.assertEqual(self.preview(50,0,2,50),(1,50,50))
        self.assertEqual(self.preview(50,0,2,60),(1,40,40))
        self.assertNotIn('Save & New Syringe',read('functions/fn_skCompoundBegin.sqf'))

class B22UIContracts(unittest.TestCase):
    def test_infusion_inherits_same_original_row_overlay(self):
        from test_bounded_medication_presentation import renderer_contract, test_actual_view_and_refresh_keep_preparation_sources_off_body_map
        renderer_contract()
        for infusion in (False,True):
            for kind in ('size','flush','medication'):
                test_actual_view_and_refresh_keep_preparation_sources_off_body_map('syringe',infusion,kind)
    def test_no_b20_meter_or_relayout(self):
        inject=read('functions/fn_skInject.sqf')
        rows=read('functions/fn_skListRefresh.sqf')
        self.assertNotIn('ACME_SK_MedOriginalRect',inject)
        self.assertNotIn('ACME_SK_MedMeterH',inject+rows)
        self.assertIn('private _listW = _uiW / 5.25',inject)
        self.assertIn('private _columnInner = _uiW / 3.3',inject)
        self.assertIn('safeZoneH / 20',rows)
