"""Small real-scene acceptance check; run from either computer after setup."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import CameraRig, Renderer, SceneBuilder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', default='AUTO',
                        choices=['AUTO', 'CPU', 'METAL', 'OPTIX', 'CUDA', 'HIP', 'ONEAPI'])
    parser.add_argument('--require-gpu', action='store_true', help='Fail instead of CPU fallback')
    parser.add_argument('--preview', action='store_true', help='Leave a triple-pane GUI preview open')
    args = parser.parse_args()
    if args.require_gpu and args.backend == 'CPU':
        parser.error('--require-gpu cannot be combined with --backend CPU')
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    tmp = ROOT / 'tmp' / ('platform_check_' + stamp)
    out = ROOT / 'output' / 'platform-check' / stamp
    tmp.mkdir(parents=True)
    out.mkdir(parents=True)
    reports = {}

    def record(stage, report):
        reports[stage] = report
        (out / 'reports.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
        if report.get('status') != 'success':
            raise RuntimeError('%s failed: %s' % (stage, report.get('error')))
        device = report.get('render') or {}
        print(stage + ': success', device.get('backend', ''), device.get('devices', ''), flush=True)

    print('Results:', out, flush=True)
    try:
        record('scene', SceneBuilder(scene='lane_change', vehicle='hilux', caravan='large2',
                                     mirror='standard').build(output=tmp / 'scene.blend'))
        record('camera', CameraRig(side='both', vehicle='hilux', camera='wide').build(
            input=tmp / 'scene.blend', output=tmp / 'camera.blend'))
        renderer = Renderer(render_profile='configs/render/wide.yaml')
        # Only in-memory overrides: never change baseline configs or assets.
        renderer.render_cfg['device'].update(backend=args.backend,
                                            fallback_to_cpu=not args.require_gpu)
        renderer.render_cfg['output']['resolution_percentage'] = 35
        renderer.render_cfg['cycles']['samples'] = 32
        for side in ('L', 'R'):
            record(side, renderer.render(input=tmp / 'camera.blend', output=out / (side + '.png'),
                                         timestamp=False, camera_name='hilux_DriverCam_' + side))
        if args.preview:
            record('preview', renderer.preview(input=tmp / 'camera.blend', layout='triple'))
            print('Preview startup succeeded; visually check both panes. Close the window when done.')
    except Exception as exc:
        reports['failure'] = str(exc)
        (out / 'reports.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
        raise
    print('Reports and left/right images:', out)


if __name__ == '__main__':
    main()
