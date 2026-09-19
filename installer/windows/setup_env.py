"""Install TagLab's packages and networks into the installer's embedded Python.

The NSIS installer runs this once, with the embedded interpreter:

    python\\python.exe -u setup_env.py --torch auto|cpu|cu118|cu121|cu124 [--sam]

Everything goes into python\\Lib\\site-packages and app\\models inside the
installation folder. pip's cache is disabled, so nothing is left in the
user profile and the uninstaller can remove everything.

It replaces install.py for this layout: the same packages, but with pinned
versions (requirements-lock.txt), the GDAL/rasterio wheels shipped with the
installer, and the networks downloaded over HTTPS.
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE / 'app'
MODELS = APP / 'models'
WHEELS = HERE / 'wheels'
LOCK = HERE / 'requirements-lock.txt'
MODEL_HASHES = HERE / 'models.sha256'  # optional "<sha256>  <file>" lines

PIP_WHEEL = 'pip-26.2.1-py3-none-any.whl'
LOCAL_WHEELS = [
    'gdal-3.9.2-cp311-cp311-win_amd64.whl',
    'rasterio-1.3.11-cp311-cp311-win_amd64.whl',
]

TORCH = 'torch==2.5.1+{variant}'
TORCHVISION = 'torchvision==0.20.1+{variant}'
TORCH_INDEX = 'https://download.pytorch.org/whl/{variant}'
# Newest first: the CUDA version reported by the driver must be at least this.
CUDA_VARIANTS = [('cu124', (12, 4)), ('cu121', (12, 1)), ('cu118', (11, 8))]

MODELS_URL = 'https://taglab.isti.cnr.it/models/'
CORE_MODELS = [
    'dextr_corals.pth',
    'deeplab-resnet.pth.tar',
    'ritm_corals.pth',
    'pocillopora.net',
    'porites.net',
    'pocillopora_porite_montipora.net',
]
SAM_MODEL = 'sam_vit_h_4b8939.pth'

# rasterio must be imported before PyQt5 (TagLab issue #216).
SMOKE_TEST = (
    'import rasterio; from osgeo import gdal; from PyQt5 import QtWidgets; '
    'import torch, torchvision, cv2, skimage, sklearn, pandas, shapely, '
    'albumentations, pycocotools, ezdxf, segment_anything; '
    'print("torch", torch.__version__, "- CUDA available:", torch.cuda.is_available())'
)

_log_file = None


def log(message):
    print(message, flush=True)
    if _log_file is not None:
        _log_file.write(message + '\n')
        _log_file.flush()


def run(command):
    """Run a command, streaming its output to the installer window and the log."""
    log('> ' + ' '.join(command))
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    for line in process.stdout:
        log(line.rstrip())
    if process.wait() != 0:
        raise SystemExit(f'Command failed with exit code {process.returncode}: {command[0]}')


def pip(*args):
    run([
        sys.executable, '-m', 'pip', *args[:1],
        '--disable-pip-version-check', '--no-input', '--no-cache-dir',
        *args[1:],
    ])


def ensure_pip():
    try:
        import pip  # noqa: F401
    except ImportError:
        # pip can run from its own wheel to install itself. It is imported
        # from the wheel with -c: the embedded Python ignores PYTHONPATH, and
        # running "<wheel>/pip" makes pip refuse to modify itself on Windows.
        wheel = WHEELS / PIP_WHEEL
        bootstrap = (
            'import sys; sys.path.insert(0, sys.argv[1]); '
            'from pip._internal.cli.main import main; sys.exit(main(sys.argv[2:]))'
        )
        run([
            sys.executable, '-c', bootstrap, str(wheel),
            'install', '--no-index', '--no-warn-script-location', str(wheel),
        ])


def driver_cuda_version():
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r'CUDA Version:\s*(\d+)\.(\d+)', result.stdout) if result.returncode == 0 else None
    return (int(match[1]), int(match[2])) if match else None


def choose_torch_variant(requested):
    if requested != 'auto':
        return requested
    cuda = driver_cuda_version()
    if cuda is None:
        log('No NVIDIA driver found: using the CPU build of PyTorch.')
        return 'cpu'
    for variant, minimum in CUDA_VARIANTS:
        if cuda >= minimum:
            log(f'The NVIDIA driver supports CUDA {cuda[0]}.{cuda[1]}: using PyTorch {variant}.')
            return variant
    log(f'The NVIDIA driver only supports CUDA {cuda[0]}.{cuda[1]}: using the CPU build of PyTorch.')
    return 'cpu'


def install_packages(variant):
    # PyTorch first and only from its own index, so no other package is
    # resolved there; the lock file then finds torch already satisfied.
    pip(
        'install', '--no-warn-script-location', '--no-deps',
        '--index-url', TORCH_INDEX.format(variant=variant),
        TORCH.format(variant=variant), TORCHVISION.format(variant=variant),
    )
    pip('install', '--no-warn-script-location', '--only-binary=:all:', '-r', str(LOCK))
    # Their dependencies are in the lock file.
    pip('install', '--no-warn-script-location', '--no-deps', *[str(WHEELS / name) for name in LOCAL_WHEELS])
    pip('check')


def known_hashes():
    hashes = {}
    if MODEL_HASHES.is_file():
        for line in MODEL_HASHES.read_text(encoding='utf-8').splitlines():
            if line.strip():
                digest, name = line.split(maxsplit=1)
                hashes[name.strip()] = digest.lower()
    return hashes


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def download(name, expected, attempts=3):
    url = MODELS_URL + name
    target = MODELS / name
    partial = target.with_name(target.name + '.part')
    request = urllib.request.Request(url, headers={'User-Agent': 'TagLab-installer'})
    for attempt in range(1, attempts + 1):
        try:
            digest = hashlib.sha256()
            with urllib.request.urlopen(request, timeout=60) as response, open(partial, 'wb') as out:
                total = int(response.headers.get('Content-Length') or 0)
                received = 0
                next_report = 10
                while chunk := response.read(1 << 20):
                    out.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    if total and received * 100 // total >= next_report:
                        log(f'  {name}: {received * 100 // total}% of {total / 1e6:.0f} MB')
                        next_report += 10
            if total and received != total:
                raise OSError(f'incomplete download ({received} of {total} bytes)')
            if expected and digest.hexdigest() != expected:
                raise OSError('checksum mismatch')
            os.replace(partial, target)
            return
        except OSError as error:
            log(f'  attempt {attempt} of {attempts} failed: {error}')
            if attempt < attempts:
                time.sleep(5 * attempt)
    partial.unlink(missing_ok=True)
    raise SystemExit(f'Could not download {url}')


def download_models(names):
    MODELS.mkdir(parents=True, exist_ok=True)
    hashes = known_hashes()
    for name in names:
        target = MODELS / name
        expected = hashes.get(name)
        if target.is_file() and (expected is None or sha256_of(target) == expected):
            log(f'{name} already present.')
            continue
        log(f'Downloading {MODELS_URL}{name} ...')
        download(name, expected)


def main():
    global _log_file
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--torch', default='auto', choices=['auto', 'cpu'] + [v for v, _ in CUDA_VARIANTS])
    parser.add_argument('--sam', action='store_true', help='also download the SAM network (2.6 GB)')
    parser.add_argument('--skip-models', action='store_true', help='for testing the package installation only')
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()

    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        _log_file = open(args.log, 'a', encoding='utf-8')
    log(f'TagLab setup - Python {sys.version.split()[0]} at {sys.executable}')

    # Keep pip away from the user's own site-packages and configuration.
    os.environ['PYTHONNOUSERSITE'] = '1'
    os.environ['PIP_CONFIG_FILE'] = os.devnull

    ensure_pip()
    variant = choose_torch_variant(args.torch)
    install_packages(variant)
    if not args.skip_models:
        download_models(CORE_MODELS + ([SAM_MODEL] if args.sam else []))
    run([sys.executable, '-c', SMOKE_TEST])
    log('TagLab setup completed.')


if __name__ == '__main__':
    main()
