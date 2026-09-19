# TagLab Windows installer

An NSIS installer for Windows 10/11 (64-bit). It needs no administrator rights
and no Python on the machine.

## What it installs

The installer puts everything in `%LOCALAPPDATA%\Programs\TagLab`, per user:

| Folder / file | Content |
| --- | --- |
| `python\` | embedded CPython 3.11.9 (the version `install.py` requires) with all packages |
| `app\` | TagLab, exported from a git ref (no `.git`) |
| `wheels\` | pip, GDAL 3.9.2 and rasterio 1.3.11 wheels, the same ones `install.py` uses |
| `logs\` | `install.log`, `launcher.log` |
| `taglab_launcher.py` | what the shortcuts run |
| `setup_env.py` | run once during installation |

When the installer runs, `setup_env.py`:

- installs PyTorch 2.5.1 (CPU, or CUDA 12.4 / 12.1 / 11.8, chosen on a page or detected from the NVIDIA driver);
- installs the pinned packages from `requirements-lock.txt` and the GDAL/rasterio wheels;
- runs `pip check`;
- downloads the networks over HTTPS and checks them against `models.sha256` (SAM, 2.6 GB, is optional);
- ends with an import test.

pip's cache is disabled, so nothing is left in the user profile.

Shortcuts: Start menu (TagLab, TagLab with console, Uninstall) and, optionally, the desktop.

The uninstaller removes `python\`, `wheels\`, `logs\` and the shortcuts. In `app\` it removes only the files it
installed or that TagLab generated (networks, `TagLab.log`, `__pycache__`). If the user saved projects in the
program folder, those are kept and the uninstaller says so. It also removes TagLab's settings
(`HKCU\Software\VCLAB\TagLab`) and its own registry entries.

## The launcher

`taglab_launcher.py` fixes these problems of an installed copy without changing TagLab:

- **Import order.** It imports `rasterio` before PyQt5. Otherwise TagLab can exit silently on Windows (#216, PR #223).
- **Paths.** It sets the working directory and `sys.path` to `app\`. The embedded Python does not add the script
  folder, and TagLab opens some files relative to the working directory.
- **Version check.** TagLab's startup check would call `sys.exit(0)` once GitHub has a newer version: without `.git`
  the branch always looks like `main`. The launcher answers that check as "no update", because updates come from
  a new installer.
- **Errors.** It installs `sys.excepthook`. Under `pythonw`, PyQt5 would otherwise close TagLab on any exception
  raised in a slot, with no message. Errors go to `logs\launcher.log` and are shown once in a message box.

## Pinned versions

`requirements-lock.txt` is pip's resolution of `install.py`'s package list for CPython 3.11 / win_amd64, with these
changes:

- `numpy<2`: TagLab still uses `np.NaN`, which NumPy 2.0 removed.
- `albumentations==1.4.18`: 2.x silently ignores the `CoarseDropout` / `always_apply` arguments in
  `models/coral_dataset.py`.
- `opencv-python-headless` only: TagLab uses no cv2 GUI functions, and having both OpenCV packages installed
  makes them overwrite each other.

## Building

Requirements: git, NSIS 3.x (`makensis`), Python 3 with Pillow.

From this folder (`installer/windows/`):

```
python build.py --ref <commit|tag|branch> [--repo <path or URL>] [--makensis <path to makensis.exe>]
```

`--repo` defaults to the TagLab checkout containing this folder. The `installer/` folder itself is not packaged.

This writes `dist\TagLab-<TAGLAB_VERSION>-setup.exe`, about 160 MB, of which 127 MB are the optional sample
projects. The downloads that `build.py` embeds are pinned by SHA-256.

`models.sha256` lists the SHA-256 of the networks; `setup_env.py` checks every download against it and
re-downloads a file that does not match. The hashes were taken from an HTTPS download of the official server;
`sam_vit_h_4b8939.pth` also matches the MD5 prefix in its name (`4b8939…`), as Meta publishes it. Update the
file when the networks on the server change.

Silent install: `TagLab-…-setup.exe /S /CPU` (or `/TORCH=cpu|cu118|cu121|cu124`; `/D=<folder>` must be the last
argument). Silent uninstall: `Uninstall.exe /S`.
