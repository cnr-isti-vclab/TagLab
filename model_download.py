"""Verify cached model sizes and publish downloads only after validation."""

import os
from pathlib import Path
import tempfile
import urllib.request
import zipfile
import zlib


class ModelDownloadError(RuntimeError):
    pass


def _response_size(response):
    try:
        size = int(response.headers.get('Content-Length', ''))
    except ValueError:
        raise ModelDownloadError('The model server did not provide a valid Content-Length.')
    if size <= 0:
        raise ModelDownloadError('The model server reported an empty file.')
    return size


def _is_complete(path, expected_size):
    if not path.is_file() or path.stat().st_size != expected_size:
        return False
    try:
        with path.open('rb') as stream:
            is_zip = stream.read(4) == b'PK\x03\x04'
        if is_zip:
            with zipfile.ZipFile(path) as archive:
                return archive.testzip() is None
    except (OSError, EOFError, zipfile.BadZipFile, zlib.error):
        return False
    # Older PyTorch checkpoints use a pickle-based format. Do not unpickle
    # downloaded data here; transport length is their completion check.
    return True


def ensure_model(url, destination):
    """Return True if a model was downloaded, False if the cache was verified.

    The installer needs network access to verify the server's file size.
    ZIP checkpoints also receive a CRC check; legacy checkpoints are checked
    for complete transport only, without executing pickle data.
    """
    destination = Path(destination)
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'identity'}
    temporary = None
    try:
        request = urllib.request.Request(url, method='HEAD', headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            expected_size = _response_size(response)
        if _is_complete(destination, expected_size):
            return False

        destination.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            if _response_size(response) != expected_size:
                raise ModelDownloadError('The model size changed during the download. Please retry.')
            with tempfile.NamedTemporaryFile(
                    prefix=destination.name + '.', suffix='.part',
                    dir=destination.parent, delete=False) as stream:
                temporary = Path(stream.name)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    stream.write(chunk)

        if not _is_complete(temporary, expected_size):
            received = temporary.stat().st_size
            raise ModelDownloadError(
                'Incomplete or corrupt model: received {} bytes, expected {}. Please retry.'.format(
                    received, expected_size))
        os.replace(temporary, destination)
        temporary = None
        return True
    except ModelDownloadError:
        raise
    except Exception as error:
        raise ModelDownloadError('Cannot verify or download {}: {}'.format(destination.name, error)) from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
