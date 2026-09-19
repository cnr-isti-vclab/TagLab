"""Build the TagLab Windows installer.

    python build.py --ref <git ref> [--repo <path or URL>] [--makensis <path>]

Needs git, NSIS 3 (makensis) and Pillow (pip install pillow). It:

1. exports TagLab at the given ref (git archive, so no .git folder);
2. downloads the embedded Python, pip, GDAL and rasterio (pinned and
   checked against SHA-256);
3. assembles build/payload and the uninstall file list;
4. runs makensis on TagLab.nsi.

The packages and networks are downloaded by the installer itself
(setup_env.py). The installer is about 160 MB, 127 MB of which are the
optional sample projects.
"""

import argparse
import hashlib
import io
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / 'build'
PAYLOAD = BUILD / 'payload'

# installer/windows/ inside a TagLab checkout; otherwise clone upstream
CHECKOUT = HERE.parent.parent
DEFAULT_REPO = str(CHECKOUT) if (CHECKOUT / '.git').exists() else 'https://github.com/cnr-isti-vclab/TagLab'

# name -> (url, sha256)
DOWNLOADS = {
    'python-3.11.9-embed-amd64.zip': (
        'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip',
        '009d6bf7e3b2ddca3d784fa09f90fe54336d5b60f0e0f305c37f400bf83cfd3b',
    ),
    'pip-26.2.1-py3-none-any.whl': (
        'https://files.pythonhosted.org/packages/f3/6e/1736e5b4ae2b778ef2f81c47d797de9f891d4d8acb047a24ca37a60294dd/pip-26.2.1-py3-none-any.whl',
        '71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e',
    ),
    'gdal-3.9.2-cp311-cp311-win_amd64.whl': (
        'https://github.com/cgohlke/geospatial-wheels/releases/download/v2024.9.22/gdal-3.9.2-cp311-cp311-win_amd64.whl',
        '278f397c0f7d2b1ef07b770a3d39a4433b1040f9d86b13d6daaf146b74402de7',
    ),
    'rasterio-1.3.11-cp311-cp311-win_amd64.whl': (
        'https://github.com/cgohlke/geospatial-wheels/releases/download/v2024.9.22/rasterio-1.3.11-cp311-cp311-win_amd64.whl',
        '6414878cfda4690626139564c8c7eaf93cef505594df4aa5e3969d644d44fb69',
    ),
}

# Not needed in an installed copy: repository extras, old wheels for other
# Python versions, this installer, and the install/update scripts it replaces.
EXCLUDED = {
    '.github', '.gitignore', 'docs', 'installer', 'packages', 'sampleProjects',
    'screenshot.jpg', 'screenshot_masonry.png', 'dependencies.md',
    'install.py', 'install_conda_windows.py', 'update.py',
}

# The embedded Python only uses the paths listed here; site-packages and
# "import site" are needed for pip-installed packages.
PTH = 'python311.zip\n.\nLib\\site-packages\nimport site\n'

INSTALLER_FILES = ['taglab_launcher.py', 'setup_env.py', 'requirements-lock.txt']


def fetch(name, cache):
    url, expected = DOWNLOADS[name]
    target = cache / name
    if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        print(f'Downloading {url}')
        request = urllib.request.Request(url, headers={'User-Agent': 'TagLab-installer-build'})
        with urllib.request.urlopen(request, timeout=120) as response:
            target.write_bytes(response.read())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if digest != expected:
        raise SystemExit(f'SHA-256 mismatch for {name}: {digest}')
    return target


def export_sources(repo, ref):
    if Path(repo).is_dir():
        repo_dir = Path(repo)
    else:
        repo_dir = BUILD / 'repo'
        if not repo_dir.is_dir():
            subprocess.run(['git', 'clone', '--filter=blob:none', repo, str(repo_dir)], check=True)
        subprocess.run(['git', '-C', str(repo_dir), 'fetch', '--tags', 'origin'], check=True)
    commit = subprocess.run(
        ['git', '-C', str(repo_dir), 'rev-parse', '--verify', f'{ref}^{{commit}}'],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    archive = subprocess.run(['git', '-C', str(repo_dir), 'archive', '--format=tar', commit], check=True, capture_output=True).stdout
    source = BUILD / 'source'
    shutil.rmtree(source, ignore_errors=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(source, filter='data')
    return source, commit


def copy_app(source):
    app = PAYLOAD / 'app'
    for item in source.iterdir():
        if item.name in EXCLUDED:
            continue
        if item.is_dir():
            shutil.copytree(item, app / item.name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(item, app / item.name)
    samples = source / 'sampleProjects'
    if samples.is_dir():
        shutil.copytree(samples, PAYLOAD / 'samples' / 'sampleProjects')


def prepare_python(cache):
    python = PAYLOAD / 'python'
    with zipfile.ZipFile(fetch('python-3.11.9-embed-amd64.zip', cache)) as archive:
        archive.extractall(python)
    (python / 'python311._pth').write_text(PTH, encoding='ascii')
    (python / 'Lib' / 'site-packages').mkdir(parents=True)
    wheels = PAYLOAD / 'wheels'
    wheels.mkdir()
    for name in DOWNLOADS:
        if name.endswith('.whl'):
            shutil.copy2(fetch(name, cache), wheels / name)


def make_icon():
    from PIL import Image
    png = PAYLOAD / 'app' / 'icons' / 'taglab240px.png'
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    Image.open(png).convert('RGBA').save(PAYLOAD / 'taglab.ico', sizes=sizes)


def nsis_path(relative):
    return '$INSTDIR\\' + str(relative).replace('/', '\\').replace('$', '$$')


def write_uninstall_list():
    """Delete exactly what was installed or generated in app\\, then empty folders."""
    sys.path.insert(0, str(HERE))
    from setup_env import CORE_MODELS, SAM_MODEL

    app = PAYLOAD / 'app'
    samples = PAYLOAD / 'samples'
    lines = ['; Generated by build.py - do not edit.']
    folders = {Path('app')}
    for root, prefix in ((app, Path('app')), (samples / 'sampleProjects', Path('app/sampleProjects'))):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*')):
            relative = prefix / path.relative_to(root)
            if path.is_dir():
                folders.add(relative)
            else:
                lines.append(f'Delete "{nsis_path(relative)}"')
    folders.add(Path('app/sampleProjects'))
    # generated at install time or by TagLab
    for name in CORE_MODELS + [SAM_MODEL]:
        lines.append(f'Delete "{nsis_path(Path("app/models") / name)}"')
        lines.append(f'Delete "{nsis_path(Path("app/models") / (name + ".part"))}"')
    lines.append(f'Delete "{nsis_path(Path("app/TagLab.log"))}"')
    for folder in sorted(folders):
        lines.append(f'RMDir /r "{nsis_path(folder / "__pycache__")}"')
    # deepest first; RMDir without /r only removes folders that are now empty
    for folder in sorted(folders, key=lambda p: len(p.parts), reverse=True):
        lines.append(f'RMDir "{nsis_path(folder)}"')
    (PAYLOAD / 'uninstall_app.nsh').write_text('\n'.join(lines) + '\n', encoding='utf-8-sig')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--repo', default=DEFAULT_REPO, help='TagLab git repository (path or URL)')
    parser.add_argument('--ref', required=True, help='commit, tag or branch to package')
    parser.add_argument('--version', help='installer version (default: TAGLAB_VERSION at --ref)')
    parser.add_argument('--makensis', default='makensis')
    parser.add_argument('--no-compile', action='store_true', help='only assemble build/payload')
    args = parser.parse_args()

    cache = BUILD / 'cache'
    cache.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(PAYLOAD, ignore_errors=True)
    PAYLOAD.mkdir(parents=True)

    source, commit = export_sources(args.repo, args.ref)
    version = args.version or (source / 'TAGLAB_VERSION').read_text(encoding='utf-8').strip()
    print(f'Packaging TagLab {version} ({commit[:10]})')

    copy_app(source)
    prepare_python(cache)
    for name in INSTALLER_FILES:
        shutil.copy2(HERE / name, PAYLOAD / name)
    if (HERE / 'models.sha256').is_file():
        shutil.copy2(HERE / 'models.sha256', PAYLOAD / 'models.sha256')
    make_icon()
    write_uninstall_list()
    (PAYLOAD / 'BUILD_INFO.txt').write_text(f'TagLab {version}\ncommit {commit}\n', encoding='utf-8')

    if args.no_compile:
        return
    outfile = HERE / 'dist' / f'TagLab-{version}-setup.exe'
    outfile.parent.mkdir(exist_ok=True)
    subprocess.run([
        args.makensis, '-V3',
        f'/DAPPVERSION={version}', f'/DPAYLOAD={PAYLOAD}', f'/DOUTFILE={outfile}',
        str(HERE / 'TagLab.nsi'),
    ], check=True)
    print(f'Installer: {outfile}')


if __name__ == '__main__':
    main()
