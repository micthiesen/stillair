"""Host schema/math tests and native in-memory corruption probes.

Native probes never save the production projects. They prove bad preparation is
rejected, not routing completion or electrical/physical performance.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pcb_readiness import (Audit, CHECKS, Inputs, aperture_metrics, audit_project,
                           boxes_overlap, digest_bytes, interactive_session, main, sexpressions, validate_profile)

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / 'pcb/tools/readiness-profiles.json'

try:
    import pcbnew
    import wx
except ImportError:
    pcbnew = None


def profiles():
    return json.loads(PROFILE_PATH.read_text())['boards']


def sample_profile():
    return {'schema_version': 1, 'board': 'example', 'lock': 'lock.json',
            'augmentation': 'augment.json', 'policy': 'policy.json', 'rules_source': 'rules.txt',
            'checks': {name: {'required': True} for name in CHECKS}}


class HostTests(unittest.TestCase):
    def test_empty_profile_cannot_pass(self):
        result = audit_project('/missing.kicad_pcb', {}, ROOT)
        self.assertFalse(result['passed'])
        self.assertEqual(result['checks'], [])

    @unittest.skipUnless(PROFILE_PATH.exists(), 'Project-owned profiles are not installed in this peer')
    def test_real_profiles_complete(self):
        for profile in profiles().values():
            validate_profile(profile)
            self.assertEqual(set(profile['checks']), CHECKS)

    def test_missing_unknown_empty_and_duplicate_check_configuration(self):
        base = sample_profile()
        for change in ['missing', 'unknown', 'empty', 'wrong_type']:
            profile = copy.deepcopy(base)
            if change == 'missing':
                del profile['checks']['paste']
            elif change == 'unknown':
                profile['checks']['ready'] = {'approved': True}
            elif change == 'empty':
                profile['checks']['paste'] = {}
            else:
                profile['checks'] = []
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_profile(profile)

    def test_unknown_profile_version_and_fields(self):
        profile = sample_profile()
        profile['schema_version'] = 2
        with self.assertRaises(ValueError):
            validate_profile(profile)
        profile['schema_version'] = 1
        profile['skip'] = ['paste']
        with self.assertRaises(ValueError):
            validate_profile(profile)

    def test_strict_settings_parser(self):
        self.assertEqual(sexpressions('# comment\n(rule "A\\\"B" (condition "x"))'), [['rule', 'A"B', ['condition', 'x']]])
        for text in ['(rule', 'rule)', '(rule))', '(rule "unterminated)', '']:
            with self.subTest(text=text):
                if text:
                    with self.assertRaises(ValueError):
                        sexpressions(text)
                else:
                    self.assertEqual(sexpressions(text), [])

    def test_stencil_shapes_have_exact_metrics(self):
        area, perimeter = aperture_metrics('roundrect', 1.45, .30, .05)
        self.assertAlmostEqual(area / (perimeter * .1), 1.2678201220014331)
        self.assertEqual(aperture_metrics('rect', 1, 2), (2, 6))
        self.assertEqual(aperture_metrics('oval', 1, 1), aperture_metrics('circle', 1, 1))

    def test_unsupported_or_invalid_aperture_fails_closed(self):
        for args in [('custom', 1, 1), ('trapezoid', 1, 1), ('roundrect', 1, 1, .6), ('circle', 1, 2), ('rect', 0, 1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                aperture_metrics(*args)

    def test_overlap_is_not_counted_as_two_disjoint_apertures(self):
        self.assertTrue(boxes_overlap([0, 0, 2, 2], [1, 1, 3, 3]))
        self.assertFalse(boxes_overlap([0, 0, 2, 2], [2, 0, 4, 2]))

    def test_interactive_session_is_observation_not_a_gate(self):
        for enabled in (True, False):
            facts = interactive_session(json.dumps({'board': {'auto_track_width': enabled}}).encode())
            self.assertEqual(facts['saved_preferences']['board.auto_track_width'], enabled)
            self.assertFalse(facts['runtime_state_verified'])
            self.assertFalse(facts['preparation_gate'])
        self.assertEqual(interactive_session(None)['status'], 'not_present')
        self.assertEqual(interactive_session(b'not json')['status'], 'unreadable_saved_state')

    def test_catalog_change_during_audit_fails_and_binds_original_bytes(self):
        with tempfile.TemporaryDirectory(prefix='pcb-readiness-catalog-') as directory:
            path = Path(directory)/'profiles.json'
            output = Path(directory)/'result.json'
            original = json.dumps({'schema_version': 1, 'boards': {'example': sample_profile()}}).encode()
            path.write_bytes(original)
            def replace_catalog(*args):
                path.write_text('{}')
                return {'passed': True, 'findings': [], 'checks': [], 'facts': {}}
            with patch('pcb_readiness.audit_project', side_effect=replace_catalog):
                code = main(['--board', 'example', '--profiles', str(path), '--root', directory,
                             '--board-path', str(Path(directory)/'unused.kicad_pcb'), '--output', str(output)])
            result = json.loads(output.read_text())
            self.assertEqual(code, 1)
            self.assertFalse(result['passed'])
            self.assertEqual(result['input_sha256'][str(path.resolve())], digest_bytes(original))
            self.assertTrue(any('catalog changed' in f['message'] for f in result['findings']))

    def test_inputs_bind_files_and_fail_missing(self):
        with tempfile.TemporaryDirectory(prefix='pcb-readiness-host-') as directory:
            p = Path(directory) / 'profile.json'
            p.write_text('{}')
            inputs = Inputs(directory)
            self.assertEqual(inputs.json('profile.json'), {})
            self.assertEqual(inputs.hashes['profile.json'], digest_bytes(b'{}'))
            with self.assertRaises(ValueError):
                inputs.read('missing')


@unittest.skipUnless(pcbnew is not None and PROFILE_PATH.exists(), 'Native KiCad/project profiles unavailable; run kicad_python.sh for native probes')
class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = wx.App.Get() or wx.App(False)
        cls.quiet = wx.LogNull()
        cls.file_hashes = {p: digest_bytes(p.read_bytes()) for name in profiles()
                           for p in (ROOT/f'pcb/{name}/kicad').glob(f'{name}.kicad_*')}

    @classmethod
    def tearDownClass(cls):
        for path, expected in cls.file_hashes.items():
            if digest_bytes(path.read_bytes()) != expected:
                raise AssertionError('Production file changed during read-only probes: ' + str(path))

    def load(self, name='controller'):
        path = ROOT / f'pcb/{name}/kicad/{name}.kicad_pcb'
        # Read-only native load, deliberately no SaveBoard/SaveProject call.
        self.manager = pcbnew.GetSettingsManager()
        self.manager.LoadProject(str(path.with_suffix('.kicad_pro')), False)
        self.project = self.manager.GetProject(str(path.with_suffix('.kicad_pro')))
        board = pcbnew.LoadBoard(str(path))
        board.SetProject(self.project)
        board.SynchronizeNetsAndNetClasses(False)
        audit = Audit(board, profiles()[name], ROOT, pcbnew,
                      json.loads(path.with_suffix('.kicad_pro').read_text()), path.read_text())
        audit.board_path = path
        return audit

    def assert_rejects(self, audit, check):
        result = audit.run(audit.board_path)
        self.assertFalse(result['passed'])
        self.assertTrue(any(f['check'] == check for f in result['findings']), result['findings'])
        self.assertEqual({c['id'] for c in result['checks']}, CHECKS)
        return result

    def test_all_saved_projects_pass_without_changes(self):
        for name in profiles():
            with self.subTest(board=name):
                audit = self.load(name)
                result = audit.run(audit.board_path)
                self.assertTrue(result['passed'], result['findings'])
                self.assertEqual(len(result['checks']), len(CHECKS))
                self.assertGreater(result['facts']['paste']['minimum_area_ratio'], .66)

    def test_public_api_hashes_native_inputs_and_accepts_manifest_override(self):
        name = 'sensor'
        path = ROOT / f'pcb/{name}/kicad/{name}.kicad_pcb'
        with tempfile.TemporaryDirectory(prefix='pcb-readiness-manifest-') as directory:
            manifest = json.loads((ROOT / profiles()[name]['lock']).read_text())['manifest']
            manifest_path = Path(directory) / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest))
            result = audit_project(path, profiles()[name], ROOT, manifest_path)
            self.assertTrue(result['passed'], result['findings'])
            self.assertEqual(result['input_sha256'][str(manifest_path.resolve())], digest_bytes(manifest_path.read_bytes()))
            self.assertEqual(result['input_sha256'][str(path.relative_to(ROOT))], digest_bytes(path.read_bytes()))
            manifest['board']['width_mm'] = 19
            manifest_path.write_text(json.dumps(manifest))
            result = audit_project(path, profiles()[name], ROOT, manifest_path)
            self.assertFalse(result['passed'])
            self.assertTrue(any(f['check'] == 'geometry' for f in result['findings']))

    def test_local_editor_state_is_read_and_hashed_without_changing_it(self):
        path = ROOT/'pcb/controller/kicad/controller.kicad_pcb'
        local = path.with_suffix('.kicad_prl')
        if not local.exists():
            self.skipTest('No saved local editor state')
        content = local.read_bytes()
        result = audit_project(path, profiles()['controller'], ROOT)
        self.assertTrue(result['passed'], result['findings'])
        self.assertEqual(result['facts']['interactive_session'], interactive_session(content))
        self.assertEqual(result['input_sha256'][str(local.relative_to(ROOT))], digest_bytes(content))
        self.assertEqual(local.read_bytes(), content)

    def test_local_editor_state_race_invalidates_readback(self):
        path = ROOT/'pcb/controller/kicad/controller.kicad_pcb'
        local = path.with_suffix('.kicad_prl')
        if not local.exists():
            self.skipTest('No saved local editor state')
        read = Path.read_bytes
        count = 0
        def changing_read(p):
            nonlocal count
            if p.resolve() == local.resolve():
                count += 1
                if count > 1:
                    return b'{"board":{"auto_track_width":false}}'
            return read(p)
        with patch.object(Path, 'read_bytes', changing_read):
            result = audit_project(path, profiles()['controller'], ROOT)
        self.assertFalse(result['passed'])
        self.assertTrue(any(f['check'] == 'inputs' for f in result['findings']), result['findings'])

    def test_missing_pour_fails(self):
        a = self.load()
        zone = next(z for z in a.board.Zones() if not z.GetIsRuleArea())
        a.board.RemoveNative(zone)
        self.assert_rejects(a, 'planes')

    def test_missing_saved_fill_fails(self):
        a = self.load('sensor')
        z = next(z for z in a.board.Zones() if not z.GetIsRuleArea())
        z.SetIsFilled(False)
        self.assert_rejects(a, 'planes')

    def test_wrong_pour_net_clearance_and_thermal_mode_fail(self):
        a = self.load('mains')
        z = next(z for z in a.board.Zones() if not z.GetIsRuleArea())
        z.SetNet(a.board.FindNet('V5_PSU'))
        self.assert_rejects(a, 'planes')
        a = self.load('mains')
        z = next(z for z in a.board.Zones() if not z.GetIsRuleArea())
        z.SetLocalClearance(pcbnew.FromMM(.01))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_NONE)
        self.assert_rejects(a, 'planes')

    def test_moved_mount_and_outline_fail(self):
        a = self.load()
        a.footprints['H1'].Move(pcbnew.VECTOR2I(pcbnew.FromMM(1), 0))
        self.assert_rejects(a, 'geometry')
        a = self.load()
        edge = next(g for g in a.board.GetDrawings() if g.GetLayer() == pcbnew.Edge_Cuts)
        edge.Move(pcbnew.VECTOR2I(pcbnew.FromMM(1), 0))
        self.assert_rejects(a, 'geometry')

    def test_wrong_header_or_stack_fails(self):
        a = self.load('sensor')
        a.board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(1.6))
        self.assert_rejects(a, 'stackup')
        a = self.load('sensor')
        a.board_text = a.board_text.replace('(thickness 0.2104 locked)', '(thickness 0.1104 locked)', 1)
        self.assert_rejects(a, 'stackup')

    def test_wrong_via_size_or_tenting_fails(self):
        a = self.load('sensor')
        v = next(t for t in a.board.GetTracks() if isinstance(t, pcbnew.PCB_VIA))
        v.SetDrill(pcbnew.FromMM(.4))
        self.assert_rejects(a, 'vias')
        a = self.load('sensor')
        v = next(t for t in a.board.GetTracks() if isinstance(t, pcbnew.PCB_VIA))
        v.SetBackTentingMode(pcbnew.TENTING_MODE_NOT_TENTED)
        self.assert_rejects(a, 'vias')

    def test_usb_shell_and_duplicate_paste_are_rejected(self):
        for number in ['SH', 'B1']:
            a = self.load()
            pad = next(p for p in a.footprints['J4'].Pads() if p.GetNumber() == number)
            layers = pad.GetLayerSet()
            layers.AddLayer(pcbnew.F_Paste)
            pad.SetLayerSet(layers)
            self.assert_rejects(a, 'paste')

    def test_effective_inherited_paste_margin_is_rejected(self):
        a = self.load('mains')
        a.board.GetDesignSettings().m_SolderPasteMargin = pcbnew.FromMM(-.05)
        self.assert_rejects(a, 'paste')

    def test_unsupported_actual_aperture_fails(self):
        a = self.load()
        p = next(p for _, p in a.pads if p.IsOnLayer(pcbnew.F_Paste))
        p.SetShape(pcbnew.PAD_SHAPE_TRAPEZOID)
        result = self.assert_rejects(a, 'paste')
        self.assertTrue(any('unsupported aperture shape' in f['message'] for f in result['findings']))

    def test_sensor_mask_opening_and_pigtail_paste_fail(self):
        for ref, layer in [('E1', pcbnew.B_Mask), ('J1', pcbnew.F_Paste)]:
            a = self.load('sensor')
            p = next(iter(a.footprints[ref].Pads()))
            layers = p.GetLayerSet()
            layers.AddLayer(layer)
            p.SetLayerSet(layers)
            self.assert_rejects(a, 'paste')

    def test_sensor_assembly_exclusion_removed_is_rejected(self):
        a = self.load('sensor')
        a.footprints['J1'].SetExcludedFromPosFiles(False)
        self.assert_rejects(a, 'paste')

    def test_new_via_tenting_default_is_rejected(self):
        a = self.load('mains')
        a.board.GetDesignSettings().m_TentViasBack = False
        self.assert_rejects(a, 'vias')

    def test_removed_label_is_detected(self):
        a = self.load()
        text = next(t for t in a.text_items() if t.GetText() == 'RESET')
        text.SetText('RESET MISSING')
        self.assert_rejects(a, 'labels')

    def test_native_memory_router_choice_does_not_certify_saved_gui_state(self):
        a = self.load('mains')
        a.board.GetDesignSettings().m_UseConnectedTrackWidth = True
        result = a.run(a.board_path)
        self.assertTrue(result['passed'], result['findings'])
        self.assertNotIn('interactive_session', result['facts'])

    def test_narrow_class_and_enlarged_escape_are_rejected(self):
        a = self.load('mains')
        next(c for c in a.project['net_settings']['classes'] if c['name'] == 'Motor')['track_width'] = .3
        self.assert_rejects(a, 'routing')
        a = self.load('mains')
        z = next(z for z in a.board.Zones() if z.GetZoneName().startswith('Neck'))
        z.Move(pcbnew.VECTOR2I(pcbnew.FromMM(.1), 0))
        self.assert_rejects(a, 'rules')

    def test_native_rule_tampering_fails(self):
        a = self.load('mains')
        with tempfile.TemporaryDirectory(prefix='pcb-readiness-rules-') as directory:
            path = Path(directory)/'mains.kicad_pcb'
            path.with_suffix('.kicad_dru').write_text('(version 1)\n(rule "bad" (constraint track_width (min 0.01mm)))')
            a.board_path = path
            self.assert_rejects(a, 'rules')

    def test_extra_exclusion_or_global_padstack_ignore_fails(self):
        a = self.load('sensor')
        a.project['board']['design_settings']['drc_exclusions'].append(['padstack|0|0|unexpected|0', 'not reviewed'])
        self.assert_rejects(a, 'exclusions')
        a = self.load('sensor')
        a.project['board']['design_settings']['rule_severities']['padstack'] = 'ignore'
        self.assert_rejects(a, 'exclusions')

    def test_unknown_nested_setting_fails_closed(self):
        a = self.load()
        a.profile['checks']['paste']['skip_area'] = True
        self.assert_rejects(a, 'paste')


if __name__ == '__main__':
    unittest.main()
