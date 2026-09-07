"""Real-asset API checks: framing, assemblies, caravan selection and environment."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import SceneBuilder, CameraRig, Renderer, ConfigExporter
from src._common import BPY_COMMON_PRELUDE, run_blender_script, _project_mkdtemp


CHECK = r'''
_open_blend(__INPUT__)
sc = bpy.context.scene
prefix = sc['vmirror_vehicle']
ego = bpy.data.objects[prefix + '_ego']
caravan = next((o for o in sc.objects if o.name.startswith('Caravan_')), None)
out = {'status': 'success', 'sides': {}, 'world': {}}
if caravan:
    assert caravan.parent == ego
    if sc.get('vmirror_caravan') == 'large2':
        assert abs(max(v.co.z for v in caravan.data.vertices) - 2.62525) < .001
        assert len(caravan.data.vertices) == 748579
for side in ('L', 'R'):
    mirror = bpy.data.objects[prefix + '_Mirror_' + side]
    assert mirror.parent == ego
    cam = bpy.data.objects[prefix + '_DriverCam_' + side]
    assert cam.parent == ego
    fit = _fit_mirror_camera(cam)
    assert fit is not None
    aux = bpy.data.objects.get(mirror.name + '_Aux')
    row = {'framing': fit, 'local_location': list(mirror.location)}
    if aux:
        main_z = min((mirror.matrix_local @ v.co).z for v in mirror.data.vertices)
        aux_z = max((aux.matrix_local @ v.co).z for v in aux.data.vertices)
        assert main_z > aux_z, (main_z, aux_z)
        row['vertical_gap_m'] = main_z - aux_z
    if sc['vmirror_mirror'].startswith('towing_main'):
        sign = -1 if side == 'L' else 1
        edge = max(sign*v.co.x for v in ego.data.vertices)
        if caravan:
            edge = max(edge, max(sign*(caravan.matrix_local@v.co).x for v in caravan.data.vertices))
        pieces = [mirror] + ([aux] if aux else [])
        inner = min(sign*(o.matrix_local@v.co).x for o in pieces for v in o.data.vertices)
        assert inner - edge >= .05 - 1e-5, inner-edge
        row['outboard_clearance_m'] = inner - edge
    out['sides'][side] = row
bg = next(n for n in sc.world.node_tree.nodes if n.type == 'BACKGROUND')
expected = __WORLD__
assert all(abs(a-b)<1e-6 for a,b in zip(bg.inputs['Color'].default_value, expected['color']))
assert abs(bg.inputs['Strength'].default_value - expected['strength']) < 1e-6
out['world'] = {'color': list(bg.inputs['Color'].default_value), 'strength': bg.inputs['Strength'].default_value}
sun = bpy.data.objects['Sun_Light']
assert abs(sun.data.energy - __SUN__) < 1e-6
out['sun_energy'] = sun.data.energy
_write_report(__REPORT__, out)
'''


def main():
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    tmp = ROOT / 'tmp' / ('geometry_check_' + stamp)
    out = ROOT / 'output' / 'geometry-check' / stamp
    tmp.mkdir(parents=True); out.mkdir(parents=True)
    summary = {}

    def record(key, report):
        summary[key] = report
        (out / 'reports.json').write_text(json.dumps(summary, indent=2))
        if report.get('status', 'success') != 'success':
            raise RuntimeError(f'{key}: {report}')
        print(key, 'success', flush=True)

    cases = [('api_default', 'passat', None, 'standard')]
    cases += [(v + '_towing', v, 'large2', 'towing') for v in ('passat', 'hilux', 'crv', 'polo')]
    cases += [('electric', 'hilux', 'large2', 'electric')]
    print('Results:', out, flush=True)
    for tag, vehicle, caravan, mirror in cases:
        b = SceneBuilder(vehicle=vehicle, caravan=caravan, mirror=mirror)
        if tag == 'polo_towing':
            b.vehicle_cfg['origin']['position'] = [2, 3, 0]
            b.vehicle_cfg['origin']['rotation'] = [0, 0, 20]
        if tag == 'electric':
            b.scene_cfg['sun_light']['energy'] = 2.25
        record(tag + '/scene', b.build(output=tmp / (tag + '.blend')))
        record(tag + '/camera', CameraRig(vehicle=vehicle, side='both').build(
            input=tmp / (tag + '.blend'), output=tmp / (tag + '_camera.blend')))
        r = Renderer()
        r.render_cfg['cycles']['samples'] = 32
        r.render_cfg['output']['resolution_percentage'] = 40
        if tag == 'electric':
            r.render_cfg['world']['color'] = [.22, .4, .65]
            r.render_cfg['world']['strength'] = .75
            # The render aspect may differ from the camera profile's aspect.
            r.render_cfg['output']['resolution_x'] = 1080
            r.render_cfg['output']['resolution_y'] = 1080
        for side in ('L', 'R'):
            record(tag + '/' + side, r.render(
                input=tmp / (tag + '_camera.blend'), output=out / f'{tag}_{side}.png',
                output_blend=tmp / (tag + '_render.blend'), timestamp=False,
                camera_name=f'{vehicle}_DriverCam_{side}'))
        rp = _project_mkdtemp('geometry_probe_') / 'report.json'
        body = CHECK.replace('__INPUT__', repr(str(tmp / (tag + '_render.blend'))))
        body = body.replace('__WORLD__', repr(r.render_cfg['world']))
        body = body.replace('__SUN__', repr(b.scene_cfg['sun_light']['energy']))
        body = body.replace('__REPORT__', repr(str(rp)))
        record(tag + '/checks', run_blender_script(b.blender_exe, BPY_COMMON_PRELUDE + body, rp, timeout=120))
        if tag == 'polo_towing':
            exported = ConfigExporter().export(blend=tmp / (tag + '_render.blend'),
                tag='roundtrip', out_root=str(out / 'export'))
            record(tag + '/export', exported)
            bundle = Path(exported['session_dir'])
            rb = SceneBuilder(vehicle=vehicle, caravan=caravan, mirror=mirror,
                mirror_path_L=str(bundle / 'mirrors/towing_main_L.yaml'),
                mirror_path_R=str(bundle / 'mirrors/towing_main_R.yaml'))
            rb.vehicle_cfg = b.vehicle_cfg
            rebuilt = rb.build(output=tmp / 'roundtrip.blend')
            original = summary[tag + '/scene']['mirrors']
            for key, m in original.items():
                for field in ('location', 'rotation_deg'):
                    assert max(abs(a-z) for a,z in zip(m[field], rebuilt['mirrors'][key][field])) < 2e-4
            record(tag + '/roundtrip', rebuilt)


if __name__ == '__main__':
    main()
