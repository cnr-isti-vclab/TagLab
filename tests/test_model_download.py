import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import tempfile
import threading
import unittest
import zipfile

from model_download import ModelDownloadError, ensure_model


class ModelDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name) / 'model.pth'
        self.payload = b'complete legacy checkpoint contents' * 16
        self.interrupt = False
        self.gets = 0
        self.advertise_length = True
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_HEAD(self):
                self.send_response(200)
                if owner.advertise_length:
                    self.send_header('Content-Length', str(len(owner.payload)))
                self.end_headers()

            def do_GET(self):
                owner.gets += 1
                self.send_response(200)
                self.send_header('Content-Length', str(len(owner.payload)))
                self.end_headers()
                data = owner.payload[:12] if owner.interrupt else owner.payload
                self.wfile.write(data)
                self.wfile.flush()
                if owner.interrupt:
                    self.connection.shutdown(socket.SHUT_WR)

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

    def test_interruption_leaves_no_final_file_and_retry_succeeds(self):
        self.interrupt = True
        with self.assertRaises(ModelDownloadError):
            ensure_model(self.url, self.destination)
        self.assertFalse(self.destination.exists())
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

    def test_truncated_zip_is_not_published(self):
        self.payload = b'PK\x03\x04' + b'missing central directory'
        with self.assertRaises(ModelDownloadError):
            ensure_model(self.url, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(Path(self.temp.name).glob('*.part')), [])


if __name__ == '__main__':
    unittest.main()
