import contextlib
import io
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch
import urllib.request


INSTALLER = Path(__file__).resolve().parents[1] / 'install.py'


class CudaDetectionTests(unittest.TestCase):
    def run_installer(self, output, return_code=0, args=()):
        console = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch('platform.system', return_value='Windows'))
            stack.enter_context(patch('sys.version_info', (3, 11, 0)))
            stack.enter_context(patch('sys.argv', [str(INSTALLER), *args]))
            probe = stack.enter_context(patch(
                'subprocess.getstatusoutput', return_value=(return_code, output)))
            installs = stack.enter_context(patch('subprocess.check_call'))
            stack.enter_context(patch('urllib.request.build_opener'))
            stack.enter_context(patch('urllib.request.install_opener'))
            stack.enter_context(patch('urllib.request.urlretrieve'))
            stack.enter_context(patch('os.remove'))
            stack.enter_context(patch('pathlib.Path.is_file', return_value=True))
            stack.enter_context(contextlib.redirect_stdout(console))
            result = runpy.run_path(str(INSTALLER), run_name='__main__')

        torch_calls = [
            call.args[0] for call in installs.call_args_list
            if any(str(arg).startswith('torch==') for arg in call.args[0])
        ]
        self.assertEqual(len(torch_calls), 1)
        self.assertEqual(torch_calls[0][4], result['torch_package'])
        return result, torch_calls[0], console.getvalue(), probe

    def test_both_header_formats_select_cuda(self):
        for label in ('CUDA Version:', 'CUDA UMD Version:'):
            with self.subTest(label=label):
                output = '| NVIDIA-SMI 616.56  Driver Version: 616.56  {} 13.4 |'.format(label)
                result, command, console, probe = self.run_installer(output)
                self.assertEqual(result['cuda_version'].strip(), '13.4')
                self.assertEqual(result['torch_compute_platform'], '12.4')
                self.assertIn('https://download.pytorch.org/whl/cu124', command)
                self.assertNotIn('Using Torch in CPU version.', console)
                probe.assert_called_once_with('nvidia-smi')

    def test_spacing_does_not_change_version_selection(self):
        for field in ('CUDA Version:12.1|', 'CUDA UMD Version:  12.1    |'):
            with self.subTest(field=field):
                result, command, _, _ = self.run_installer(field)
                self.assertEqual(result['cuda_version'], '12.1')
                self.assertEqual(result['torch_compute_platform'], '12.1')
                self.assertIn('https://download.pytorch.org/whl/cu121', command)

    def test_missing_or_unavailable_version_falls_back_to_cpu(self):
        for output in ('no CUDA version field', 'CUDA Version: N/A', 'CUDA UMD Version: N/A'):
            with self.subTest(output=output):
                result, command, console, _ = self.run_installer(output)
                self.assertEqual(result['torch_compute_platform'], 'cpu')
                self.assertNotIn('--index-url', command)
                self.assertIn('Could not read CUDA version.', console)
                self.assertIn('Using Torch in CPU version.', console)

    def test_failed_nvidia_smi_falls_back_to_cpu(self):
        result, _, console, _ = self.run_installer('nvidia-smi not found', return_code=1)
        self.assertEqual(result['torch_compute_platform'], 'cpu')
        self.assertIn('Using Torch in CPU version.', console)

    def test_unsupported_cuda_version_falls_back_to_cpu(self):
        result, _, console, _ = self.run_installer('CUDA Version: 10.2')
        self.assertEqual(result['torch_compute_platform'], 'cpu')
        self.assertIn('CUDA version not supported.', console)

    def test_explicit_cpu_option_skips_detection(self):
        result, _, console, probe = self.run_installer('CUDA UMD Version: 13.4', args=('cpu',))
        self.assertEqual(result['torch_compute_platform'], 'cpu')
        self.assertIn('Using Torch in CPU version.', console)
        probe.assert_not_called()


if __name__ == '__main__':
    unittest.main()
