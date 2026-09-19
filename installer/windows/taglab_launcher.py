"""Start TagLab from the Windows installer layout.

The shortcuts run this file with the embedded interpreter
(python\\pythonw.exe, or python.exe for the console shortcut). It works
around problems of an installed copy without modifying TagLab itself:

- The embedded Python does not put the script folder on sys.path, and
  TagLab opens some files relative to the working directory, so both are
  set to app\\.
- rasterio must be imported before PyQt5, otherwise TagLab can exit
  silently on Windows (TagLab issue #216, PR #223).
- At startup TagLab compares its version with GitHub and calls
  sys.exit(0) when it is out of date and the branch looks like "main",
  which is always the case without a .git folder. An installed copy would
  stop opening the day a new version is published, with no visible
  message. The installer is the update path here, so that check is
  answered as "no update".
- Under pythonw there is no console, and PyQt5 aborts on any exception
  raised in a slot. Exceptions are written to logs\\launcher.log and
  shown once in a message box instead of closing TagLab.
"""

import os
import runpy
import sys
import traceback
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, 'app')
LOG_DIR = os.path.join(HERE, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'launcher.log')

_shown_errors = set()


def _log(text):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, 'a', encoding='utf-8') as log:
        log.write(f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {text}\n')


def _show_error(title, text):
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is not None:
            QMessageBox.critical(None, title, text)
            return
    except Exception:
        pass
    import ctypes
    ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)


def _excepthook(exc_type, exc, tb):
    details = ''.join(traceback.format_exception(exc_type, exc, tb))
    _log('Unhandled exception\n' + details)
    # One box per distinct error, so a repeating one (e.g. from a timer) does not flood the screen.
    where = traceback.extract_tb(tb)[-1] if tb else None
    key = (exc_type.__name__, where.filename if where else '', where.lineno if where else 0)
    if key not in _shown_errors:
        _shown_errors.add(key)
        _show_error(
            'TagLab',
            f'{exc_type.__name__}: {exc}\n\n'
            f'TagLab keeps running, but the last operation may not have completed.\n'
            f'Details: {LOG_FILE}',
        )


def _skip_version_check():
    original = urllib.request.urlopen

    def urlopen(url, *args, **kwargs):
        target = getattr(url, 'full_url', url)
        if isinstance(target, str) and target.endswith('/TAGLAB_VERSION'):
            raise OSError('version check skipped: this copy is updated by the installer')
        return original(url, *args, **kwargs)

    urllib.request.urlopen = urlopen


def main():
    if sys.stdout is None:  # pythonw: keep TagLab's print() output
        os.makedirs(LOG_DIR, exist_ok=True)
        sys.stdout = sys.stderr = open(LOG_FILE, 'a', encoding='utf-8', buffering=1)

    os.environ.setdefault('NO_ALBUMENTATIONS_UPDATE', '1')
    os.chdir(APP)
    sys.path.insert(0, APP)
    _skip_version_check()
    sys.excepthook = _excepthook

    script = os.path.join(APP, 'TagLab.py')
    sys.argv[0] = script
    try:
        import rasterio  # noqa: F401  (before PyQt5, see above)

        runpy.run_path(script, run_name='__main__')
    except SystemExit:
        raise
    except BaseException:
        details = traceback.format_exc()
        _log('TagLab could not start\n' + details)
        _show_error('TagLab', f'TagLab could not start.\n\n{details.strip().splitlines()[-1]}\n\nDetails: {LOG_FILE}')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
