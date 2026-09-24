"""Regression contracts for indented posture labels and standalone Dog Tags."""
from historical_source import read_source
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
def src(name):return read_source(ROOT/'functions'/f'fn_{name}.sqf', encoding='utf-8-sig')

def labels():
    table=src('medDescriptor').split('case "position":',1)[1].split('// breathing.',1)[0]
    return {key:(plain,clinical) for key,plain,clinical in re.findall(r'\["(elevate30|lower0)",\s*\["([^"]+)",\s*"([^"]+)"\]\]',table)}

class LabelsAndOrder(unittest.TestCase):
    def test_posture_wording_has_exact_plain_and_clinical_pairs(self):
        self.assertEqual(labels(),{'elevate30':('Elevate Head to 30°',"Place in Semi-Fowler's position"),
                                   'lower0':('Lower Head to Flat','Place in Supine position')})
        self.assertIn('getVariable ["ACME_hc_descriptors", false]',src('medDescriptor'))

    def test_class_resolution_precedes_gate_and_place_trimming(self):
        s=src('ivSiteRelabel')
        resolution=s.index('if (_positionKey != "") exitWith')
        self.assertLess(s.index('case "acme_elevatehead"'),resolution)
        self.assertLess(s.index('case "acme_lowerhead"'),resolution)
        self.assertLess(resolution,s.index('getVariable ["ACME_hc_descriptors"'))
        self.assertLess(resolution,s.index('if (_new find "Place " == 0)'))
        self.assertIn('(_text select [0,_leading]) + (["position", _positionKey]',s)
        self.assertIn('(_chars select _leading) in [9,32]',s)

    def test_posture_actions_are_head_only_and_stay_in_examine(self):
        c=read_source(ROOT/'config.cpp', encoding='utf-8-sig')
        for name in ('ACME_ElevateHead','ACME_LowerHead'):
            b=c.split('class '+name+':',1)[1].split('\n    };',1)[0]
            self.assertIn('allowedSelections[] = {"Head"};',b)
            self.assertIn('category = "examine";',b)
        self.assertIn('displayName = "Elevate Head to 30°";',c)

    def test_dog_tags_have_no_group_and_keep_native_condition(self):
        self.assertNotIn('"checkdogtags"',src('menuExamineGroups'))
        self.assertIn('if (_name == "checkdogtags") exitWith {["examine", "", false]};',src('menuActionInfo'))
        c=read_source(ROOT/'config.cpp', encoding='utf-8-sig')
        b=c.split('class CheckDogTags:',1)[1].split('};',1)[0]
        self.assertIn('condition = "ACME_fnc_canCheckPatientDogtags";',b)
        collector=read_source(ROOT/'overrides/fn_collectActions.sqf')
        self.assertIn('_orderedExamine + _rest + _dogTags;',collector)
        self.assertIn('!= "checkdogtags"',collector)

    def test_default_palette_and_optional_separate_colors(self):
        p=src('postInit')
        self.assertIn('ACME_menuHeaderColorDefault = [1, 0.96, 0.84, 1];',p)
        self.assertIn('ACME_menuRowColorDefault = [1, 1, 1, 1];',p)
        self.assertIn('ACME_menuRowColorAlternate = [1, 1, 1, 1];',p)
        settings=read_source(ROOT/'XEH_settings.hpp')
        header=settings.split('"ACME_menuColorHeaders"',1)[1].split('call CBA_fnc_addSetting',1)[0]
        self.assertIn('OFF (default): all dropdown headings use cream text',header)
        self.assertIn('Regular action rows use uniform white text',header)
        self.assertRegex(header,r'\n\s*false,\n\s*2,')
        self.assertNotIn('ACME_menuOpenDimFactor =',p)

if __name__=='__main__':unittest.main()
