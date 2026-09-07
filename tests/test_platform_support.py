"""Hardware-independent regression tests; actual GPU rendering needs Blender."""
import os
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

from src._render_device import configure_cycles_device
from src._common import find_blender, run_blender_script


class Preferences:
    def __init__(self, available):
        self.available = available
        self.compute_device_type = 'NONE'
        self.devices = []
        self.metalrt = 'AUTO'

    def refresh_devices(self):
        backend = self.compute_device_type
        if backend not in self.available:
            raise RuntimeError('Unsupported backend')
        self.devices = [NS(type=kind, name=name, use=True)
                        for kind, name in self.available[backend]]


def fake_blender(available):
    prefs = Preferences(available)
    cy = NS(device='GPU', denoising_use_gpu=True, preview_denoising_use_gpu=True)
    bpy = NS(context=NS(scene=NS(cycles=cy), preferences=NS(
        addons={'cycles': NS(preferences=prefs)})), app=NS(version_string='test'))
    return bpy, prefs, cy


class DeviceTests(unittest.TestCase):
    def setup_device(self, system, available, profile=None):
        bpy, prefs, cy = fake_blender(available)
        with patch('platform.system', return_value=system):
            report = configure_cycles_device(bpy, profile or {'device': {'backend': 'AUTO'}})
        return report, prefs, cy

    def test_linux_prefers_optix_and_disables_cpu(self):
        report, prefs, cy = self.setup_device('Linux', {
            'OPTIX': [('OPTIX', 'RTX 5070 Ti'), ('CPU', 'CPU'), ('CUDA', 'RTX 5070 Ti')]})
        self.assertEqual(report['backend'], 'OPTIX')
        self.assertEqual([d.type for d in prefs.devices if d.use], ['OPTIX'])
        self.assertEqual(cy.device, 'GPU')
        self.assertFalse(cy.denoising_use_gpu)

    def test_linux_tries_cuda_after_empty_optix(self):
        report, _, _ = self.setup_device('Linux', {
            'OPTIX': [('CPU', 'CPU')], 'CUDA': [('CUDA', 'RTX')]})
        self.assertEqual(report['backend'], 'CUDA')
        self.assertEqual(report['attempts'][0]['backend'], 'OPTIX')

    def test_mac_uses_modern_metalrt(self):
        report, prefs, _ = self.setup_device('Darwin', {'METAL': [('METAL', 'M3 Max')]})
        self.assertEqual(report['devices'], ['M3 Max'])
        self.assertEqual(prefs.metalrt, 'ON')
        self.assertEqual(report['metal_devices'], ['M3 Max'])

    def test_missing_gpu_clears_saved_gpu_and_denoising(self):
        report, _, cy = self.setup_device('Linux', {})
        self.assertEqual(cy.device, 'CPU')
        self.assertFalse(cy.denoising_use_gpu)
        self.assertFalse(cy.preview_denoising_use_gpu)
        self.assertTrue(report['fallback_reason'])

    def test_explicit_cpu_and_legacy_disabled(self):
        for profile in ({'device': {'backend': 'CPU'}}, {'apple_silicon': {'enabled': False}}):
            report, _, cy = self.setup_device('Darwin', {}, profile)
            self.assertEqual(cy.device, 'CPU')
            self.assertIsNone(report['fallback_reason'])

    def test_strict_mode_and_invalid_backend(self):
        for backend in ('OPTIX', 'TYPO'):
            with self.assertRaises((RuntimeError, ValueError)):
                self.setup_device('Linux', {}, {'device': {
                    'backend': backend, 'fallback_to_cpu': False}})

    def test_legacy_metal_profile_on_linux_falls_back(self):
        report, _, cy = self.setup_device('Linux', {}, {
            'apple_silicon': {'enabled': True, 'compute_device_type': 'METAL'},
            'cycles': {'denoising_use_gpu': True}})
        self.assertEqual(cy.device, 'CPU')
        self.assertTrue(report['apple_silicon_error'])
        self.assertFalse(cy.denoising_use_gpu)

    def test_gpu_denoising_opt_in(self):
        _, _, cy = self.setup_device('Linux', {'OPTIX': [('OPTIX', 'RTX')]}, {
            'device': {'backend': 'OPTIX'}, 'cycles': {'denoising_use_gpu': True}})
        self.assertTrue(cy.denoising_use_gpu)
        self.assertTrue(cy.preview_denoising_use_gpu)


class StartupTests(unittest.TestCase):
    def test_override_precedes_environment(self):
        with patch.dict(os.environ, {'VMIRROR_BLENDER_EXE': '/env/blender'}), patch(
            'shutil.which', side_effect=lambda p: p) as which:
            self.assertEqual(find_blender('/explicit/blender'), '/explicit/blender')
            which.assert_called_once_with('/explicit/blender')

    def test_environment_and_invalid_path(self):
        with patch.dict(os.environ, {'VMIRROR_BLENDER_EXE': '/env/blender'}), patch(
            'shutil.which', return_value='/env/blender'):
            self.assertEqual(find_blender(), '/env/blender')
        with patch('shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'Configured Blender'):
                find_blender('/missing/blender')

    def test_headless_linux_preview_fails_before_launch(self):
        with patch('sys.platform', 'linux'), patch.dict(os.environ, {}, clear=True), patch(
            'subprocess.Popen') as popen:
            with self.assertRaisesRegex(RuntimeError, 'desktop session'):
                run_blender_script('blender', '', None, open_gui=True)
            popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
