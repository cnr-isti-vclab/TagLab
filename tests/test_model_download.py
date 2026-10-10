import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

from model_download import ModelDownloadError, ensure_model


class ModelDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name) / 'model.pth'
        self.payload = b'complete legacy checkpoint contents' * 16
        self.interrupt = False
        self.interrupt_once_at = None
        self.gets = 0
        self.requests = []
        self.advertise_length = True
        self.etag = '"checkpoint-v1"'
        self.ignore_range = False
        self.ignore_range_at = None
        self.changed_at = None
        self.omit_etag_at = None
        self.wrong_range = False
        self.wrong_total = False
        self.wrong_range_size = False
        self.transient_error_at = None
        self.modified = 'Wed, 09 Oct 2024 13:07:46 GMT'
        self.addCleanup(patch.stopall)
        patch('model_download._RANGE_SIZE', 64).start()
        patch('model_download._RETRY_DELAY', 0).start()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def validator_headers(self, start=None):
                if owner.etag is not None and (start is None or start != owner.omit_etag_at):
                    etag = '"changed-version"' if start == owner.changed_at and start is not None else owner.etag
                    # HTTP header names are case insensitive.
                    self.send_header('etag', etag)
                self.send_header('last-modified', owner.modified)

            def do_HEAD(self):
                self.send_response(200)
                if owner.advertise_length:
                    self.send_header('Content-Length', str(len(owner.payload)))
                self.validator_headers()
                self.end_headers()

            def do_GET(self):
                owner.gets += 1
                requested_range = self.headers.get('Range')
                owner.requests.append((requested_range, self.headers.get('If-Range')))
                start = 0
                end = len(owner.payload) - 1
                if requested_range:
                    start, end = map(int, requested_range.removeprefix('bytes=').split('-'))
                if owner.transient_error_at == start:
                    owner.transient_error_at = None
                    self.send_response(503)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                is_range = (requested_range is not None and not owner.ignore_range
                            and start != owner.ignore_range_at)
                self.send_response(206 if is_range else 200)
                self.validator_headers(start)
                data = owner.payload[start:end + 1] if is_range else owner.payload
                if is_range:
                    total = len(owner.payload) + (1 if owner.wrong_total else 0)
                    range_start = start + (1 if owner.wrong_range else 0)
                    self.send_header('Content-Range', 'bytes {}-{}/{}'.format(range_start, end, total))
                size = len(data) + (1 if owner.wrong_range_size and is_range else 0)
                self.send_header('Content-Length', str(size))
                self.end_headers()
                interrupted = owner.interrupt or owner.interrupt_once_at == start
                if owner.interrupt_once_at == start:
                    owner.interrupt_once_at = None
                if interrupted:
                    data = data[:12]
                try:
                    self.wfile.write(data)
                    self.wfile.flush()
                    if interrupted:
                        self.connection.shutdown(socket.SHUT_WR)
                except OSError:
                    # The client closes an ignored Range response before
                    # requesting the complete file.
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.url = 'http://127.0.0.1:{}/model.pth'.format(self.server.server_port)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_truncated_existing_file_is_repaired(self):
        self.destination.write_bytes(self.payload[:12])
        self.assertTrue(ensure_model(self.url, self.destination))
        self.assertEqual(self.destination.read_bytes(), self.payload)

    def test_complete_file_is_reused_without_downloading(self):
        self.destination.write_bytes(self.payload)
        self.assertFalse(ensure_model(self.url, self.destination))
        self.assertEqual(self.gets, 0)

    def test_ranges_use_if_range_and_exact_boundaries(self):
        self.assertTrue(ensure_model(self.url, self.destination))
        self.assertEqual(self.destination.read_bytes(), self.payload)
        expected = [('bytes={}-{}'.format(start, min(start + 64, len(self.payload)) - 1), self.etag)
                    for start in range(0, len(self.payload), 64)]
        self.assertEqual(self.requests, expected)

    def test_interrupted_range_is_retried_without_repeating_completed_ranges(self):
        self.interrupt_once_at = 64
        self.assertTrue(ensure_model(self.url, self.destination))
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertEqual([request[0] for request in self.requests[:4]],
                         ['bytes=0-63', 'bytes=64-127', 'bytes=64-127', 'bytes=128-191'])
        self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])

    def test_transient_http_failure_retries_only_affected_range(self):
        self.transient_error_at = 64
        self.assertTrue(ensure_model(self.url, self.destination))
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertEqual([request[0] for request in self.requests[:4]],
                         ['bytes=0-63', 'bytes=64-127', 'bytes=64-127', 'bytes=128-191'])

    def test_ignored_ranges_fall_back_to_a_complete_download(self):
        self.ignore_range = True
        self.assertTrue(ensure_model(self.url, self.destination))
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertEqual(self.requests, [('bytes=0-63', self.etag), (None, None)])

    def test_range_support_disappearing_discards_prefix_before_full_download(self):
        self.ignore_range_at = 64
        self.assertTrue(ensure_model(self.url, self.destination))
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertEqual(self.requests, [('bytes=0-63', self.etag),
                                        ('bytes=64-127', self.etag), (None, None)])

    def test_missing_or_weak_etag_uses_complete_transfers(self):
        for etag in (None, 'W/"checkpoint-v1"'):
            with self.subTest(etag=etag):
                self.etag = etag
                self.requests.clear()
                self.destination.unlink(missing_ok=True)
                self.assertTrue(ensure_model(self.url, self.destination))
                self.assertEqual(self.destination.read_bytes(), self.payload)
                self.assertEqual(self.requests, [(None, None)])

    def test_interrupted_complete_transfer_is_retried_from_zero(self):
        self.etag = None
        self.interrupt_once_at = 0
        self.assertTrue(ensure_model(self.url, self.destination))
        self.assertEqual(self.destination.read_bytes(), self.payload)
        self.assertEqual(self.requests, [(None, None), (None, None)])

    def test_changed_representation_preserves_previous_file(self):
        previous = self.payload[:8]
        self.destination.write_bytes(previous)
        self.changed_at = 64
        with self.assertRaisesRegex(ModelDownloadError, 'changed'):
            ensure_model(self.url, self.destination)
        self.assertEqual(self.destination.read_bytes(), previous)
        self.assertEqual(self.gets, 2)
        self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])

    def test_changed_representation_on_ignored_range_is_not_mixed_or_retried(self):
        self.changed_at = 64
        self.ignore_range_at = 64
        with self.assertRaisesRegex(ModelDownloadError, 'changed'):
            ensure_model(self.url, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.gets, 2)
        self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])

    def test_missing_range_validator_is_rejected(self):
        self.omit_etag_at = 64
        with self.assertRaisesRegex(ModelDownloadError, 'changed'):
            ensure_model(self.url, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.gets, 2)
        self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])

    def test_invalid_range_metadata_is_rejected(self):
        for field in ('wrong_range', 'wrong_total', 'wrong_range_size'):
            with self.subTest(field=field):
                setattr(self, field, True)
                with self.assertRaisesRegex(ModelDownloadError, '(range|length)'):
                    ensure_model(self.url, self.destination)
                self.assertFalse(self.destination.exists())
                self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])
                setattr(self, field, False)

    def test_interruption_leaves_no_final_file_and_retry_succeeds(self):
        self.interrupt = True
        with self.assertRaises(ModelDownloadError):
            ensure_model(self.url, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.gets, 3)
        self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])
        self.interrupt = False
        self.assertTrue(ensure_model(self.url, self.destination))
        self.assertEqual(self.destination.read_bytes(), self.payload)

    def test_failed_repair_preserves_existing_file(self):
        previous = self.payload[:8]
        self.destination.write_bytes(previous)
        self.interrupt = True
        with self.assertRaises(ModelDownloadError):
            ensure_model(self.url, self.destination)
        self.assertEqual(self.destination.read_bytes(), previous)
        self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])

    def test_failed_complete_download_preserves_previous_file(self):
        previous = self.payload[:8]
        self.destination.write_bytes(previous)
        self.etag = None
        self.interrupt = True
        with self.assertRaises(ModelDownloadError):
            ensure_model(self.url, self.destination)
        self.assertEqual(self.destination.read_bytes(), previous)
        self.assertEqual(self.gets, 3)
        self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])

    def test_server_without_size_does_not_mark_file_verified(self):
        self.destination.write_bytes(self.payload)
        self.advertise_length = False
        with self.assertRaises(ModelDownloadError):
            ensure_model(self.url, self.destination)
        self.assertEqual(self.gets, 0)

    def test_broken_zip_with_matching_size_is_repaired(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('checkpoint/data', b'tensor data')
        self.payload = buffer.getvalue()
        damaged = bytearray(self.payload)
        damaged[damaged.index(b'tensor data')] ^= 1
        self.destination.write_bytes(damaged)
        self.assertTrue(ensure_model(self.url, self.destination))
        self.assertEqual(self.destination.read_bytes(), self.payload)

    def test_zip_with_damaged_local_magic_is_repaired(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('checkpoint/data', b'tensor data')
        self.payload = buffer.getvalue()
        damaged = bytearray(self.payload)
        damaged[0] ^= 1
        self.destination.write_bytes(damaged)
        self.assertTrue(ensure_model(self.url, self.destination))
        self.assertEqual(self.destination.read_bytes(), self.payload)

    def test_corrupt_downloaded_zip_preserves_previous_file(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.writestr('checkpoint/data', b'tensor data')
        damaged = bytearray(buffer.getvalue())
        damaged[damaged.index(b'tensor data')] ^= 1
        self.payload = bytes(damaged)
        previous = b'previous partial download'
        self.destination.write_bytes(previous)
        with self.assertRaisesRegex(ModelDownloadError, 'corrupt'):
            ensure_model(self.url, self.destination)
        self.assertEqual(self.destination.read_bytes(), previous)
        self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])

    def test_truncated_zip_is_not_published(self):
        self.payload = b'PK\x03\x04' + b'missing central directory'
        with self.assertRaises(ModelDownloadError):
            ensure_model(self.url, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])


if __name__ == '__main__':
    unittest.main()
