#!/usr/bin/env python3
"""Read-only, fail-closed preparation audit; this is not routed/fabrication acceptance.

Native geometry is read through pcbnew. KiCad's opaque stackup/netclass SWIG
objects are supplemented by read-only saved S-expression/JSON settings. No save,
refill, repair, full-suite subprocess, or connectivity waiver occurs here.
Profiles are project-owned. Generic code and the profile callback are separate.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys

SCHEMA = 1
CHECKS = {'geometry', 'stackup', 'planes', 'vias', 'rules', 'routing', 'paste', 'labels', 'exclusions'}
EPS = 0.000002


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def close(actual, expected, tolerance=EPS):
    if isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(close(a, e, tolerance) for a, e in zip(actual, expected))
    return abs(actual - expected) <= tolerance


def sexpressions(text):
    """Strict read-only parser for saved settings and generated native rules."""
    token = re.compile(r'\s+|\#[^\n]*|\(|\)|"(?:\\.|[^"\\])*"|[^\s()"#]+')
    roots, stack, position = [], [], 0
    for match in token.finditer(text):
        if match.start() != position:
            raise ValueError('Invalid S-expression token')
        position = match.end()
        value = match.group()
        if value.isspace() or value.startswith('#'):
            continue
        if value == '(':
            item = []
            (stack[-1] if stack else roots).append(item)
            stack.append(item)
        elif value == ')':
            if not stack:
                raise ValueError('Unbalanced S-expression')
            stack.pop()
        else:
            if not stack:
                raise ValueError('Top-level S-expression atom')
            if value.startswith('"'):
                # KiCad uses escaped quotes/backslashes; leave other escapes literal.
                value = re.sub(r'\\(["\\])', r'\1', value[1:-1])
            stack[-1].append(value)
    if stack or position != len(text):
        raise ValueError('Incomplete S-expression')
    return roots


def children(node, key):
    return [item for item in node if isinstance(item, list) and item and item[0] == key]


def one(node, key):
    items = children(node, key)
    if len(items) != 1:
        raise ValueError(f'Expected exactly one {key}, found {len(items)}')
    return items[0]


def value(node, key):
    item = one(node, key)
    if len(item) < 2:
        raise ValueError(f'Missing value for {key}')
    return item[1]


def number(text):
    return float(str(text).removesuffix('mm'))


class Inputs:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.hashes = {}

    def read(self, path):
        path = (self.root / path).resolve()
        if not path.is_file():
            raise ValueError(f'Missing input: {path}')
        data = path.read_bytes()
        try:
            key = str(path.relative_to(self.root))
        except ValueError:
            key = str(path)
        self.hashes[key] = digest_bytes(data)
        return data

    def json(self, path):
        return json.loads(self.read(path))


def validate_profile(profile):
    required = {'schema_version', 'board', 'lock', 'augmentation', 'policy', 'rules_source', 'checks'}
    if not isinstance(profile, dict) or set(profile) != required:
        raise ValueError('Profile must contain exactly ' + ', '.join(sorted(required)))
    if profile['schema_version'] != SCHEMA:
        raise ValueError('Unsupported readiness profile version')
    if any(not isinstance(profile[k], str) or not profile[k].strip() for k in required - {'schema_version', 'checks'}):
        raise ValueError('Profile identifiers and input paths must be nonempty strings')
    if not isinstance(profile['checks'], dict) or set(profile['checks']) != CHECKS:
        raise ValueError('Profile must declare exactly all supported checks: ' + ', '.join(sorted(CHECKS)))
    if any(not isinstance(v, dict) or not v for v in profile['checks'].values()):
        raise ValueError('Empty or invalid check configuration')


class Audit:
    def __init__(self, board, profile, root, pcbnew, project_data, board_text, manifest_path=None):
        self.board, self.profile, self.pcbnew = board, profile, pcbnew
        self.inputs = Inputs(root)
        self.project = project_data
        self.board_text = board_text
        self.lock = self.inputs.json(profile['lock'])
        self.manifest = self.inputs.json(manifest_path) if manifest_path else self.lock['manifest']
        self.manifest_basis = str(manifest_path) if manifest_path else profile['lock']
        self.augmentation = self.inputs.json(profile['augmentation'])
        self.policy = self.inputs.json(profile['policy'])['boards'][profile['board']]
        self.operations = {op['id']: op['params'] for op in self.augmentation['operations']}
        self.findings, self.facts, self.executed = [], {}, []
        self.pads = [(f, p) for f in board.GetFootprints() for p in f.Pads()]
        self.footprints = {f.GetReference(): f for f in board.GetFootprints()}

    def fail(self, check, message):
        self.findings.append({'check': check, 'message': message})

    def require(self, check, predicate, message):
        if not predicate:
            self.fail(check, message)

    def operation(self, suffix):
        return self.operations[self.profile['board'] + '.augment.' + suffix]

    def mm(self, value):
        return self.pcbnew.ToMM(value)

    def xy(self, point):
        return [self.mm(point[0]), self.mm(point[1])]

    def config(self, check, required, optional=()):
        config = self.profile['checks'][check]
        if not set(required) <= set(config) or set(config) - set(required) - set(optional):
            raise ValueError(f'{check}: missing/unknown fields; requires {sorted(required)}')
        return config

    def geometry(self):
        c = self.config('geometry', {'basis'})
        if c['basis'] != 'accepted_manifest':
            raise ValueError('Unsupported geometry basis')
        spec = self.manifest['board']
        if spec['coordinate_system'] != 'center-x-right-y-up' or spec['outline']['kind'] != 'rectangle':
            raise ValueError('Only explicit rectangular center-x-right-y-up manifests are supported')
        self.require('geometry', self.board.GetCopperLayerCount() == spec['layer_count'], 'Copper layer count differs from manifest')
        origin = spec['kicad_origin_mm']
        center = spec['outline']['center_mm']
        cx, cy = origin[0] + center[0], origin[1] - center[1]
        w, h = spec['width_mm'], spec['height_mm']
        corners = [[cx-w/2, cy-h/2], [cx+w/2, cy-h/2], [cx+w/2, cy+h/2], [cx-w/2, cy+h/2]]
        edges = [g for g in self.board.GetDrawings() if g.GetLayer() == self.pcbnew.Edge_Cuts]
        pairs = []
        for edge in edges:
            if not isinstance(edge, self.pcbnew.PCB_SHAPE) or edge.GetShape() != self.pcbnew.SHAPE_T_SEGMENT:
                self.fail('geometry', 'Unexpected non-line outline geometry')
                continue
            points = [self.xy(edge.GetStart()), self.xy(edge.GetEnd())]
            indices = [next((i for i, p in enumerate(corners) if close(p, point)), -1) for point in points]
            pairs.append(sorted(indices))
        expected = sorted([sorted([i, (i+1)%4]) for i in range(4)])
        self.require('geometry', sorted(pairs) == expected, 'Outline must be the four exact manifest rectangle edges')
        holes = [(f.GetReference(), p) for f, p in self.pads if p.GetAttribute() == self.pcbnew.PAD_ATTRIB_NPTH]
        self.require('geometry', len(holes) == len(spec['holes']), 'NPTH/locator count differs from manifest')
        for hole in spec['holes']:
            xy = [origin[0] + hole['x_mm'], origin[1] - hole['y_mm']]
            matching = [p for ref, p in holes if ref == hole['ref'] and close(self.xy(p.GetPosition()), xy)
                        and close(self.xy(p.GetDrillSize()), [hole['drill_mm']]*2)]
            self.require('geometry', len(matching) == 1, 'Missing/moved/resized NPTH ' + hole['stable_id'])
        self.facts['geometry'] = {'width_mm': w, 'height_mm': h, 'layers': self.board.GetCopperLayerCount(),
                                  'footprints': len(self.footprints), 'npth_count': len(holes), 'manifest_basis': self.manifest_basis}

    def stackup(self):
        c = self.config('stackup', {'copper_mm', 'dielectric_mm', 'dielectric_er', 'finish', 'nominal_order_mm', 'order_note_tokens', 'process_document'})
        if not c['copper_mm'] or not c['dielectric_mm'] or not c['order_note_tokens'] or not c['process_document']:
            raise ValueError('Stackup profile cannot omit physical construction/order-note evidence')
        root = sexpressions(self.board_text)[0]
        stack = one(one(root, 'setup'), 'stackup')
        layers = children(stack, 'layer')
        copper = [float(value(l, 'thickness')) for l in layers if value(l, 'type') == 'copper']
        dielectric = [l for l in layers if l[1].startswith('dielectric ')]
        thickness = [float(value(l, 'thickness')) for l in dielectric]
        er = [float(value(l, 'epsilon_r')) for l in dielectric]
        total = sum(float(value(l, 'thickness')) for l in layers if children(l, 'thickness'))
        self.require('stackup', close(copper, c['copper_mm']), 'Saved copper thicknesses differ')
        self.require('stackup', close(thickness, c['dielectric_mm']), 'Saved dielectric thicknesses differ')
        self.require('stackup', close(er, c['dielectric_er']), 'Saved dielectric constants differ')
        self.require('stackup', value(stack, 'copper_finish') == c['finish'], 'Surface finish differs')
        self.require('stackup', close(self.mm(self.board.GetDesignSettings().GetBoardThickness()), total), 'Board header differs from physical stack sum')
        self.require('stackup', close(c['nominal_order_mm'], self.operation('stackup')['thickness_mm']), 'Order nominal differs from canonical augmentation')
        process_document = self.inputs.read(c['process_document']).decode()
        notes = process_document + '\n' + '\n'.join(t.GetText() for t in self.text_items() if t.GetLayer() not in [self.pcbnew.F_SilkS, self.pcbnew.B_SilkS])
        for token in c['order_note_tokens']:
            self.require('stackup', token.lower() in notes.lower(), 'Missing selected process/order evidence: ' + token)
        self.facts['stackup'] = {'copper_mm': copper, 'dielectric_mm': thickness, 'dielectric_er': er,
                                 'native_total_mm': round(total, 7), 'nominal_order_mm': c['nominal_order_mm'],
                                 'finish': value(stack, 'copper_finish'), 'readback': 'native header plus saved stackup (opaque SWIG descriptor)', 'process_document': c['process_document']}

    def planes(self):
        c = self.config('planes', {'operation', 'clearance_mm', 'minimum_thickness_mm', 'pad_connection', 'thermal_gap_mm', 'thermal_spoke_mm'})
        spec = self.operation(c['operation'])['planes']
        zones = [z for z in self.board.Zones() if not z.GetIsRuleArea()]
        self.require('planes', len(zones) == len(spec['layers']), 'Missing or undeclared copper pours')
        facts = []
        for layer in spec['layers']:
            lid = self.board.GetLayerID(layer)
            matches = [z for z in zones if set(z.GetLayerSet().Seq()) == {lid} and z.GetNetname() == spec['net']]
            self.require('planes', len(matches) == 1, f'Requires one {spec["net"]} pour on {layer}')
            if len(matches) != 1:
                continue
            z = matches[0]
            poly = z.Outline()
            actual = [self.xy(poly.CVertex(i)) for i in range(poly.TotalVertices())]
            self.require('planes', close(actual, spec['outline']), f'{layer}: pour boundary differs from augmentation')
            expected_connection = {'solid': self.pcbnew.ZONE_CONNECTION_FULL, 'tht_thermal': self.pcbnew.ZONE_CONNECTION_THT_THERMAL}[c['pad_connection']]
            self.require('planes', z.GetPadConnection() == expected_connection, f'{layer}: pad connection differs')
            for getter, expected, label in [('GetLocalClearance', c['clearance_mm'], 'clearance'), ('GetMinThickness', c['minimum_thickness_mm'], 'minimum thickness'), ('GetThermalReliefGap', c['thermal_gap_mm'], 'thermal gap'), ('GetThermalReliefSpokeWidth', c['thermal_spoke_mm'], 'thermal spoke')]:
                self.require('planes', close(self.mm(getattr(z, getter)()), expected), f'{layer}: {label} differs')
            self.require('planes', z.GetIslandRemovalMode() == self.pcbnew.ISLAND_REMOVAL_MODE_ALWAYS, f'{layer}: floating island removal disabled')
            filled = z.IsFilled() and z.HasFilledPolysForLayer(lid) and z.GetFilledPolysList(lid).TotalVertices() > 0
            self.require('planes', filled, f'{layer}: saved zone fill is absent')
            facts.append({'net': z.GetNetname(), 'layer': layer, 'filled': bool(filled), 'filled_area_mm2': round(z.GetFilledArea()/1e12, 4)})
        self.facts['planes'] = facts

    def vias(self):
        c = self.config('vias', {'operation', 'tent_all', 'extra_policy_vias'})
        if c['tent_all'] is not True:
            raise ValueError('Explicit both-side tenting policy required')
        settings = self.board.GetDesignSettings()
        self.require('vias', settings.m_TentViasFront and settings.m_TentViasBack, 'New vias must default to tenting on both sides')
        spec = self.operation(c['operation'])
        net = self.operation('routing-guardrails-zone')['planes']['net']
        expected = [(net, row) for row in spec['placements_native_xy_diameter_drill_mm']]
        if c['extra_policy_vias']:
            for v in self.policy['sensor_field']['prepared_vias']:
                row = v['position_mm'] + [v['width_mm'], v['drill_mm']]
                if not any(n == v['net'] and close(r, row) for n, r in expected):
                    expected.append((v['net'], row))
        if not expected:
            raise ValueError('Prepared via expectations cannot be empty')
        vias = [v for v in self.board.GetTracks() if isinstance(v, self.pcbnew.PCB_VIA)]
        for net, row in expected:
            matches = [v for v in vias if v.GetNetname() == net and close(self.xy(v.GetPosition()), row[:2])
                       and close([self.mm(v.GetWidth(self.pcbnew.F_Cu)), self.mm(v.GetDrillValue())], row[2:])]
            self.require('vias', len(matches) == 1, f'Prepared {net} via missing/changed at {row[:2]}')
        for via in vias:
            self.require('vias', via.TopLayer() == self.pcbnew.F_Cu and via.BottomLayer() == self.pcbnew.B_Cu,
                         'Non-through via ' + via.m_Uuid.AsString())
            self.require('vias', via.IsTented(self.pcbnew.F_Cu) and via.IsTented(self.pcbnew.B_Cu),
                         'Untented via ' + via.m_Uuid.AsString())
        self.facts['vias'] = {'prepared': len(expected), 'saved': len(vias), 'tenting': 'both sides'}

    def rules(self):
        c = self.config('rules', {'exact_generated_file', 'audit_escapes'})
        if c != {'exact_generated_file': True, 'audit_escapes': True}:
            raise ValueError('Exact rules and escape audit must be enabled')
        source = self.inputs.read(self.profile['rules_source'])
        native = self.inputs.read(self.board_path.with_suffix('.kicad_dru'))
        self.require('rules', source == native, 'Native custom rules differ from generated source')
        rules = sexpressions(native.decode())
        self.require('rules', len([r for r in rules if r and r[0] == 'rule']) > 0, 'No installed native rules')
        by_name = {r[1]: r for r in rules if r and r[0] == 'rule'}
        for net, policy in self.policy['nets'].items():
            for escape in policy['escapes']:
                pads = [p for f, p in self.pads if f.GetReference() == escape['ref'] and p.GetNumber() == escape['pad']]
                for i, pad in enumerate(pads):
                    label = f'Neck {net} {escape["ref"]}.{escape["pad"]}.{i}'
                    rule = by_name.get(label)
                    if rule is None:
                        self.fail('rules', 'Missing bounded escape rule ' + label)
                        continue
                    expected = f"A.NetName == '{net}' && A.enclosedByArea('{label}')"
                    self.require('rules', value(rule, 'condition') == expected, label + ': escape must enclose complete track')
                    width = next((x for x in children(rule, 'constraint') if x[1] == 'track_width'), [])
                    self.require('rules', close(number(value(width, 'min')), escape['minimum_width_mm']) and
                                 close(number(value(width, 'opt')), policy['minimum_width_mm']), label + ': escape min or trunk optimum differs')
                    matches = [z for z in self.board.Zones() if z.GetZoneName() == label]
                    self.require('rules', len(matches) == 1 and matches[0].GetIsRuleArea(), label + ': missing named rule area')
                    if len(matches) == 1:
                        box, n = pad.GetBoundingBox(), escape['inflate_mm']
                        expected_box = [self.mm(box.GetLeft())-n, self.mm(box.GetTop())-n, self.mm(box.GetRight())+n, self.mm(box.GetBottom())+n]
                        points = [self.xy(matches[0].Outline().CVertex(j)) for j in range(matches[0].Outline().TotalVertices())]
                        x0, y0, x1, y1 = expected_box
                        expected_points = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
                        self.require('rules', close(points, expected_points), label + ': rule area has moved or expanded')
                        self.require('rules', set(matches[0].GetLayerSet().Seq()) == {self.pcbnew.F_Cu, self.pcbnew.B_Cu}, label + ': escape layer set differs')
        self.facts['rules'] = {'sha256': digest_bytes(native), 'native_rule_count': len(by_name)}

    def routing(self):
        c = self.config('routing', {'default_width_mm', 'default_via_mm', 'classes', 'netclass_assignments', 'callback'})
        classes = {c['name']: c for c in self.project['net_settings']['classes']}
        if not c['classes']:
            raise ValueError('Every saved netclass needs declared numerical routing settings')
        self.require('routing', set(classes) == set(c['classes']), 'Saved netclass set differs from declared profile')
        default = classes['Default']
        self.require('routing', close(default['track_width'], c['default_width_mm']), 'Default track width differs')
        self.require('routing', close([default['via_diameter'], default['via_drill']], c['default_via_mm']), 'Default via size differs')
        for name, expected in c['classes'].items():
            actual = classes.get(name, {})
            for key, val in expected.items():
                self.require('routing', key in actual and close(actual[key], val), f'Netclass {name}.{key} differs')
        for net, expected_class in c['netclass_assignments'].items():
            matches = [p for _, p in self.pads if p.GetNetname() == net]
            self.require('routing', bool(matches) and all(str(p.GetNetClassName()).split(',')[0] == expected_class for p in matches), f'{net}: required {expected_class} native netclass assignment missing')
        # pcbnew resolves actual netclass priority/pattern matching. Composite class
        # names appear in inheritance priority order; use first defined width.
        net_facts = {}
        for net, rule in self.policy['nets'].items():
            pad = next((p for _, p in self.pads if p.GetNetname() == net), None)
            if pad is None:
                self.fail('routing', 'Policy net is absent: ' + net)
                continue
            names = str(pad.GetNetClassName()).split(',')
            widths = [classes[name]['track_width'] for name in names if name in classes and 'track_width' in classes[name]]
            actual = widths[0] if widths else None
            self.require('routing', actual is not None and close(actual, rule['minimum_width_mm']), net + ': native resolved netclass is not trunk width')
            net_facts[net] = {'class': names, 'width_mm': actual}
        callback = c['callback']
        if set(callback) != {'module', 'function'} or not callback['module'] or not callback['function']:
            raise ValueError('Routing callback must name module and function')
        path = (self.inputs.root / callback['module']).resolve()
        self.inputs.read(path)
        module_spec = importlib.util.spec_from_file_location('readiness_project_routing', path)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        findings = getattr(module, callback['function'])(self.board, self.policy, self.pcbnew)
        if not isinstance(findings, list) or any(not isinstance(f, str) for f in findings):
            raise ValueError('Routing callback must return a list of finding strings')
        for finding in findings:
            self.fail('routing', finding)
        self.facts['routing'] = {'default_width_mm': default['track_width'], 'default_via_mm': c['default_via_mm'], 'rail_classes': net_facts}

    def paste(self):
        c = self.config('paste', {'operation', 'expected_front_apertures', 'minimum_area_ratio', 'no_paste_refs', 'no_paste_pads', 'masked_only_refs', 'hand_solder_refs', 'forbidden_layers', 'special_windows', 'assembly_exclusions'})
        thickness = self.operation(c['operation'])['stencil_thickness_mm']
        if thickness <= 0 or c['minimum_area_ratio'] <= 0 or c['expected_front_apertures'] <= 0:
            raise ValueError('Positive stencil dimensions/count/criterion required')
        forbidden = {self.board.GetLayerID(l) for l in c['forbidden_layers']}
        no_paste_refs = set(c['no_paste_refs'])
        for ref in no_paste_refs | set(c['hand_solder_refs']) | set(c['masked_only_refs']):
            self.require('paste', ref in self.footprints, 'Missing explicit assembly reference ' + ref)
        for ref in c['assembly_exclusions']:
            fp = self.footprints.get(ref)
            self.require('paste', fp is not None and fp.IsExcludedFromBOM() and fp.IsExcludedFromPosFiles(), ref + ': copper-only/pigtail footprint must be excluded from BOM and placement export')
        for ref, numbers in c['no_paste_pads'].items():
            for num in numbers:
                self.require('paste', any(f.GetReference() == ref and p.GetNumber() == num for f, p in self.pads), f'Missing explicit no-paste pad {ref}.{num}')
        apertures = []
        back_count = 0
        for fp, pad in self.pads:
            ref, num = fp.GetReference(), pad.GetNumber()
            layers = set(pad.GetLayerSet().Seq())
            paste = layers & {self.pcbnew.F_Paste, self.pcbnew.B_Paste}
            self.require('paste', not layers & forbidden, f'{ref}.{num}: forbidden mounting-face opening/layer')
            if num in c['no_paste_pads'].get(ref, []):
                self.require('paste', self.pcbnew.F_Cu in layers and self.pcbnew.F_Mask in layers, f'{ref}.{num}: no-paste copper/mask was removed')
            if ref in no_paste_refs or num in c['no_paste_pads'].get(ref, []):
                self.require('paste', not paste, f'{ref}.{num}: hand-solder/duplicate/electrode pad has paste')
            if ref in c['masked_only_refs']:
                self.require('paste', not layers & {self.pcbnew.F_Mask, self.pcbnew.B_Mask, self.pcbnew.F_Paste, self.pcbnew.B_Paste}, f'{ref}.{num}: fixed copper must have no mask/paste openings')
            if ref in c['hand_solder_refs']:
                self.require('paste', self.pcbnew.F_Cu in layers and self.pcbnew.F_Mask in layers and not paste, f'{ref}.{num}: hand-solder pad requires copper/mask and no paste')
            if pad.GetAttribute() in [self.pcbnew.PAD_ATTRIB_PTH, self.pcbnew.PAD_ATTRIB_NPTH]:
                self.require('paste', not paste, f'{ref}.{num}: through-hole/locator has paste')
            for layer in paste:
                back_count += int(layer == self.pcbnew.B_Paste)
                self.require('paste', layer == self.pcbnew.F_Paste, 'Unexpected back paste aperture')
                copper_layer = self.pcbnew.F_Cu if layer == self.pcbnew.F_Paste else self.pcbnew.B_Cu
                margins = pad.GetSolderPasteMargin(copper_layer)
                self.require('paste', close(self.xy(margins), [0, 0]), f'{ref}.{num}: selected 1:1 stencil has an effective paste margin')
                if not close(self.xy(margins), [0, 0]):
                    continue  # no incorrect area claim for altered rounded-corner margins
                shape = pad.GetShape()
                kind = {self.pcbnew.PAD_SHAPE_RECT: 'rect', self.pcbnew.PAD_SHAPE_ROUNDRECT: 'roundrect', self.pcbnew.PAD_SHAPE_CIRCLE: 'circle', self.pcbnew.PAD_SHAPE_OVAL: 'oval'}.get(shape)
                if kind is None:
                    self.fail('paste', f'{ref}.{num}: unsupported aperture shape; exact area cannot be claimed')
                    continue
                w, h = self.xy(pad.GetSize())
                radius = self.mm(pad.GetRoundRectCornerRadius()) if kind == 'roundrect' else 0
                area, perimeter = aperture_metrics(kind, w, h, radius)
                ratio = area / (perimeter * thickness)
                self.require('paste', ratio + EPS >= c['minimum_area_ratio'], f'{ref}.{num}: stencil area ratio {ratio:.4f} too small')
                box = pad.GetBoundingBox()
                apertures.append({'ref': ref, 'pad': num, 'uuid': pad.m_Uuid.AsString(), 'size_mm': [w, h],
                                  'area_ratio': ratio, 'box': [box.GetLeft(), box.GetTop(), box.GetRight(), box.GetBottom()]})
        for item in self.graphic_items():
            if item.GetLayer() in forbidden:
                self.fail('paste', 'Graphic/text on forbidden mounting-face layer')
            if item.GetLayer() in [self.pcbnew.F_Paste, self.pcbnew.B_Paste]:
                self.fail('paste', 'Non-pad paste geometry requires a separately implemented aperture audit')
        for i, a in enumerate(apertures):
            for b in apertures[i+1:]:
                # Conservative bound, never invent a union area for overlap.
                if boxes_overlap(a['box'], b['box']):
                    self.fail('paste', f'Potential overlapping paste apertures: {a["ref"]}.{a["pad"]} / {b["ref"]}.{b["pad"]}')
        self.require('paste', len(apertures) == c['expected_front_apertures'], 'Paste aperture count differs')
        for window in c['special_windows']:
            matches = [a for a in apertures if a['ref'] == window['ref'] and a['pad'] == window['pad']]
            self.require('paste', len(matches) == window['count'] and all(close(a['size_mm'], window['size_mm']) for a in matches), 'Special stencil windows differ for ' + window['ref'] + '.' + window['pad'])
        self.facts['paste'] = {'front_apertures': len(apertures), 'back_apertures': back_count,
                               'stencil_thickness_mm': thickness, 'minimum_area_ratio': round(min((a['area_ratio'] for a in apertures), default=0), 6),
                               'overlap_method': 'conservative native bounding boxes; overlapping shapes fail without a union-area claim'}

    def graphic_items(self):
        items = list(self.board.GetDrawings())
        for footprint in self.board.GetFootprints():
            items.extend(footprint.GraphicalItems())
            items.extend([footprint.Reference(), footprint.Value()])
        return [item for item in items if not hasattr(item, 'IsVisible') or item.IsVisible()]

    def text_items(self):
        return [item for item in self.graphic_items() if isinstance(item, self.pcbnew.PCB_TEXT)]

    def labels(self):
        c = self.config('labels', {'operation', 'required_text', 'forbidden_layers'})
        expected = self.operation(c['operation']).get('labels', [])
        if not expected and not c['required_text']:
            raise ValueError('Required label set cannot be empty')
        labels = self.text_items()
        for text, x, y in expected:
            self.require('labels', any(t.GetText() == text and t.GetLayer() == self.pcbnew.F_SilkS and close(self.xy(t.GetPosition()), [x, y]) for t in labels), 'Missing/moved front label: ' + text)
        for text in c['required_text']:
            self.require('labels', any(t.GetText() == text and t.GetLayer() == self.pcbnew.F_SilkS for t in labels), 'Missing front service label: ' + text)
        forbidden = {self.board.GetLayerID(l) for l in c['forbidden_layers']}
        self.require('labels', not any(t.GetLayer() in forbidden for t in labels), 'Silkscreen on forbidden side')
        self.facts['labels'] = {'required': len(expected) + len(c['required_text']), 'visible_native_texts': len(labels)}

    def exclusions(self):
        c = self.config('exclusions', {'exact_policy', 'ignored_checks_operation'})
        if c['exact_policy'] is not True:
            raise ValueError('Exact exclusion policy must be enabled')
        settings = self.project['board']['design_settings']
        expected = []
        for exclusion in self.policy.get('native_drc_exclusions', []):
            if exclusion['type'] != 'padstack' or len(exclusion['items']) != 1 or exclusion['severity'] != 'warning':
                raise ValueError('Only explicit single-item padstack exclusions are supported')
            item = exclusion['items'][0]
            expected.append('|'.join(['padstack', str(round(item['pos']['x']*1e6)), str(round(item['pos']['y']*1e6)), item['uuid'], '00000000-0000-0000-0000-000000000000']))
        actual = settings['drc_exclusions']
        self.require('exclusions', all(isinstance(e, list) and len(e) == 2 and e[1].strip() for e in actual), 'Native exclusions require individual reasons')
        self.require('exclusions', sorted(e[0] for e in actual) == sorted(expected), 'Native exclusion identities differ from exact policy')
        severities = settings['rule_severities']
        ignored = sorted(k for k, v in severities.items() if v == 'ignore')
        allowed = self.operation(c['ignored_checks_operation'])['allowed_initial_drc_ignored_checks']
        self.require('exclusions', ignored == sorted(allowed), 'Ignored DRC categories differ from declared native defaults')
        self.require('exclusions', severities.get('padstack') == 'warning', 'Padstack category was globally disabled or changed')
        self.facts['exclusions'] = {'item_bound': len(actual), 'ignored_categories': ignored}

    def run(self, board_path):
        self.board_path = Path(board_path).resolve()
        for check in sorted(CHECKS):
            before = len(self.findings)
            try:
                getattr(self, check)()
            except Exception as error:
                self.fail(check, 'Audit could not establish required facts: ' + str(error))
            self.executed.append({'id': check, 'passed': len(self.findings) == before})
        return {'schema_version': SCHEMA, 'board': self.profile['board'], 'stage': 'routing_preparation',
                'passed': not self.findings, 'findings': self.findings, 'checks': self.executed,
                'facts': self.facts, 'input_sha256': dict(sorted(self.inputs.hashes.items()))}


def boxes_overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def aperture_metrics(shape, width, height, radius=0):
    """Exact area/perimeter for explicitly supported, zero-margin apertures."""
    if min(width, height) <= 0 or radius < 0 or radius > min(width, height)/2 + EPS:
        raise ValueError('Invalid aperture dimensions')
    if shape == 'rect':
        return width*height, 2*(width+height)
    if shape == 'roundrect':
        return width*height-(4-math.pi)*radius**2, 2*(width+height)-(8-2*math.pi)*radius
    if shape == 'circle':
        if not close(width, height):
            raise ValueError('Non-circular circle aperture')
        return math.pi*width**2/4, math.pi*width
    if shape == 'oval':
        diameter, length = min(width, height), abs(width-height)
        return math.pi*diameter**2/4+diameter*length, math.pi*diameter+2*length
    raise ValueError('Unsupported aperture shape: ' + shape)


def interactive_session(content):
    """Describe saved local editor state without claiming current GUI behavior."""
    facts = {'basis': 'local .kicad_prl saved editor state',
             'runtime_state_verified': False, 'preparation_gate': False,
             'note': 'Unsaved GUI choices are unobserved. Native API width/index defaults do not prove editor preferences. Numerical netclasses and native rule min/opt widths are checked separately; an enabled auto_track_width value alone does not prove a width-rule violation.'}
    if content is None:
        return dict(facts, status='not_present', saved_preferences={})
    try:
        data = json.loads(content)
        preferences = {}
        for section in ('board', 'pcbnew'):
            settings = data.get(section, {})
            if isinstance(settings, dict) and 'auto_track_width' in settings:
                preferences[section + '.auto_track_width'] = settings['auto_track_width']
        return dict(facts, status='observed_saved_state', saved_preferences=preferences)
    except (ValueError, AttributeError, TypeError) as error:
        return dict(facts, status='unreadable_saved_state', saved_preferences={}, error=str(error))


def audit_project(board_path, profile, root, manifest_path=None):
    """Load a saved project read-only and return deterministic preparation facts."""
    try:
        validate_profile(profile)
        import pcbnew
        from kicad_native import NativeProject
        path = Path(board_path).resolve()
        project_path = path.with_suffix('.kicad_pro')
        initial_files = {p: p.read_bytes() for p in [path, project_path]}
        local_path = path.with_suffix('.kicad_prl')
        if local_path.exists():
            initial_files[local_path] = local_path.read_bytes()
        project_data = json.loads(initial_files[project_path])
        board_text = initial_files[path].decode()
        with NativeProject(path, read_only=True) as native:
            native.board.SynchronizeNetsAndNetClasses(False)
            audit = Audit(native.board, profile, root, pcbnew, project_data, board_text, manifest_path)
            result = audit.run(path)
        result['facts']['interactive_session'] = interactive_session(initial_files.get(local_path))
        if local_path not in initial_files and local_path.exists():
            result['passed'] = False
            result['findings'].append({'check': 'inputs', 'message': 'Local editor state appeared during audit: ' + str(local_path)})
        for p, content in initial_files.items():
            try:
                key = str(p.relative_to(Path(root).resolve()))
            except ValueError:
                key = str(p)
            result['input_sha256'][key] = digest_bytes(content)
        # A GUI save or concurrent source change invalidates the entire readback.
        for key, expected in result['input_sha256'].items():
            actual_path = Path(root) / key
            if digest_bytes(actual_path.read_bytes()) != expected:
                result['passed'] = False
                result['findings'].append({'check': 'inputs', 'message': 'Input changed during audit: ' + key})
        result['profile_sha256'] = digest_bytes(json.dumps(profile, sort_keys=True, separators=(',', ':')).encode())
        return result
    except Exception as error:
        return {'schema_version': SCHEMA, 'board': profile.get('board') if isinstance(profile, dict) else None,
                'stage': 'routing_preparation', 'passed': False, 'findings': [{'check': 'load', 'message': str(error)}],
                'checks': [], 'facts': {}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--board', required=True)
    parser.add_argument('--profiles', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--board-path', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--manifest', type=Path, help='Explicit rebuilt target manifest for a pre-acceptance ECO')
    args = parser.parse_args(argv)
    try:
        catalog_bytes = args.profiles.read_bytes()
        catalog = json.loads(catalog_bytes)
        if catalog['schema_version'] != SCHEMA:
            raise ValueError('Unsupported profile catalog version')
        result = audit_project(args.board_path, catalog['boards'][args.board], args.root, args.manifest)
        result.setdefault('input_sha256', {})[str(args.profiles.resolve())] = digest_bytes(catalog_bytes)
        if args.profiles.read_bytes() != catalog_bytes:
            result['passed'] = False
            result['findings'].append({'check': 'inputs', 'message': 'Profile catalog changed during audit'})
    except (ValueError, KeyError, OSError) as error:
        result = {'schema_version': SCHEMA, 'passed': False, 'findings': [{'check': 'profile', 'message': str(error)}], 'checks': [], 'facts': {}}
    text = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end='')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
