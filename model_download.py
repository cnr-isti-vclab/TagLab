"""Verify cached model sizes and publish downloads only after validation."""

import http.client
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
import zlib


class ModelDownloadError(RuntimeError):
    pass


class _IncompleteDownload(ModelDownloadError):
    pass


_RANGE_SIZE = 8 * 1024 * 1024
_ATTEMPTS = 3
_RETRY_DELAY = 1
_TIMEOUT = 60


def _retry(operation):
    for attempt in range(_ATTEMPTS):
        try:
            return operation()
        except (OSError, http.client.HTTPException, urllib.error.URLError,
                _IncompleteDownload) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code not in (
                    408, 429, 500, 502, 503, 504):
                raise
            if attempt == _ATTEMPTS - 1:
                raise
            time.sleep(_RETRY_DELAY * 2 ** attempt)


def _response_size(response):
    try:
        size = int(response.headers.get('Content-Length', ''))
    except ValueError:
        raise ModelDownloadError('The model server did not provide a valid Content-Length.')
    if size <= 0:
        raise ModelDownloadError('The model server reported an empty file.')
    return size


def _check_representation(response, metadata):
    if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
        raise ModelDownloadError('The model server returned an encoded representation.')
    for field in ('ETag', 'Last-Modified'):
        if metadata.get(field) is not None and response.headers.get(field) != metadata[field]:
            raise ModelDownloadError('The model changed during the download. Please retry.')


def _download_range(url, headers, metadata, start, end, expected_size):
    request_headers = dict(headers, Range='bytes={}-{}'.format(start, end))
    request_headers['If-Range'] = metadata['ETag']

    def attempt():
        request = urllib.request.Request(url, headers=request_headers)
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            _check_representation(response, metadata)
            if response.status == 200:
                # A server may ignore Range. Start one complete transfer instead
                # of appending a full file to a previously downloaded prefix.
                if _response_size(response) != expected_size:
                    raise ModelDownloadError('The model size changed during the download. Please retry.')
                return None
            expected_range = 'bytes {}-{}/{}'.format(start, end, expected_size)
            if response.status != 206 or response.headers.get('Content-Range') != expected_range:
                raise ModelDownloadError('The model server returned an unexpected byte range.')
            count = end - start + 1
            if _response_size(response) != count:
                raise ModelDownloadError('The model server returned an unexpected range length.')
            data = response.read(count + 1)
            if len(data) != count:
                raise _IncompleteDownload('The model byte range was interrupted. Please retry.')
            return data

    return _retry(attempt)


def _download_full(url, headers, metadata, expected_size, stream):
    def attempt():
        stream.seek(0)
        stream.truncate()
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            _check_representation(response, metadata)
            if response.status != 200 or _response_size(response) != expected_size:
                raise ModelDownloadError('The model size changed during the download. Please retry.')
            received = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                received += len(chunk)
                stream.write(chunk)
            if received != expected_size:
                raise _IncompleteDownload(
                    'Incomplete model: received {} bytes, expected {}. Please retry.'.format(
                        received, expected_size))

    _retry(attempt)


def _is_complete(path, expected_size):
    if not path.is_file() or path.stat().st_size != expected_size:
        return False
    try:
        with path.open('rb') as stream:
            is_zip = stream.read(4) == b'PK\x03\x04'
        if is_zip or zipfile.is_zipfile(path):
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
    for complete transport only, without executing pickle data. Servers with
    a strong ETag are downloaded in bounded ranges, retrying interrupted ranges
    without redownloading completed ones. Other servers use complete transfers.
    Temporary files are never reused across invocations and are removed on failure.
    """
    destination = Path(destination)
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'identity'}
    temporary = None
    try:
        def inspect_server():
            request = urllib.request.Request(url, method='HEAD', headers=headers)
            with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
                metadata = {field: response.headers.get(field)
                            for field in ('ETag', 'Last-Modified')}
                return _response_size(response), metadata

        expected_size, metadata = _retry(inspect_server)
        if _is_complete(destination, expected_size):
            return False

        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
                prefix=destination.name + '.', suffix='.part',
                dir=destination.parent, delete=False) as stream:
            temporary = Path(stream.name)
            etag = metadata.get('ETag') or ''
            if re.fullmatch(r'"[\x21\x23-\x7e\x80-\xff]*"', etag):
                for start in range(0, expected_size, _RANGE_SIZE):
                    end = min(start + _RANGE_SIZE, expected_size) - 1
                    data = _download_range(url, headers, metadata, start, end, expected_size)
                    if data is None:
                        _download_full(url, headers, metadata, expected_size, stream)
                        break
                    stream.write(data)
            else:
                # Weak or missing validators cannot safely identify the bytes
                # being combined from multiple requests.
                _download_full(url, headers, metadata, expected_size, stream)

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
