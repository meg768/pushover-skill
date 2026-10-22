import contextlib
import base64
from http.client import IncompleteRead
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs


spec = importlib.util.spec_from_file_location(
    "send_pushover", Path(__file__).resolve().parents[1] / "scripts" / "send_pushover.py"
)
sender = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sender)


class SendPushoverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.credentials_file = Path(self.temp.name) / "credentials.json"
        config = patch.object(sender, "CREDENTIALS_FILE", self.credentials_file)
        config.start()
        self.addCleanup(config.stop)
        self.env = patch.dict(os.environ, {
            "PUSHOVER_API_TOKEN": "test-app-token",
            "PUSHOVER_USER_KEY": "test-user-key",
        }, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.http = patch.object(sender, "urlopen")
        self.urlopen = self.http.start()
        self.addCleanup(self.http.stop)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def run_cli(self, *args, stdin=""):
        with contextlib.redirect_stdout(self.stdout), contextlib.redirect_stderr(self.stderr):
            with patch.object(sender.sys, "stdin", io.StringIO(stdin)):
                return sender.main(list(args))

    def respond(self, result):
        self.urlopen.return_value.__enter__.return_value = io.BytesIO(json.dumps(result).encode())

    def test_success_posts_unicode_message_with_defaults(self):
        self.respond({"status": 1})
        self.assertEqual(self.run_cli("--message", "Klart – åäö 🎾"), 0)
        request = self.urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.pushover.net/1/messages.json")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(self.urlopen.call_args.kwargs["timeout"], 15)
        self.assertEqual(parse_qs(request.data.decode()), {
            "token": ["test-app-token"], "user": ["test-user-key"],
            "message": ["Klart – åäö 🎾"], "priority": ["0"],
        })
        self.assertIn("accepted", self.stdout.getvalue())

    def test_stdin_and_optional_fields(self):
        self.respond({"status": 1})
        self.assertEqual(self.run_cli(
            "--title", "Codex", "--device", "iphone", "--priority", "-1",
            stdin="Rad 1\nRad 2\n",
        ), 0)
        payload = parse_qs(self.urlopen.call_args.args[0].data.decode())
        self.assertEqual(payload["message"], ["Rad 1\nRad 2\n"])
        self.assertEqual(payload["title"], ["Codex"])
        self.assertEqual(payload["device"], ["iphone"])
        self.assertEqual(payload["priority"], ["-1"])

    def test_png_attachment_is_preserved_and_has_correct_mime_type(self):
        image = Path(self.temp.name) / 'poster.png'
        data = b'\x89PNG\r\n\x1a\n' + b'test image payload'
        image.write_bytes(data)
        self.respond({'status': 1})
        self.assertEqual(self.run_cli('--message', 'Affisch', '--attachment', str(image)), 0)
        payload = parse_qs(self.urlopen.call_args.args[0].data.decode())
        self.assertEqual(payload['attachment_type'], ['image/png'])
        self.assertEqual(base64.b64decode(payload['attachment_base64'][0]), data)
        self.assertNotIn(payload['attachment_base64'][0], self.stdout.getvalue())

    def test_jpeg_signature_determines_attachment_type(self):
        image = Path(self.temp.name) / 'photo.jpg'
        image.write_bytes(b'\xff\xd8\xff' + b'test image payload')
        self.respond({'status': 1})
        self.assertEqual(self.run_cli('--message', 'Bild', '--attachment', str(image)), 0)
        payload = parse_qs(self.urlopen.call_args.args[0].data.decode())
        self.assertEqual(payload['attachment_type'], ['image/jpeg'])

    def test_invalid_or_missing_attachment_never_sends(self):
        image = Path(self.temp.name) / 'poster.png'
        for data in (b'', b'not an image', b'\x89PNG\r\n\x1a\n' + b'x' * sender.MAX_ATTACHMENT_BYTES):
            with self.subTest(length=len(data)):
                image.write_bytes(data)
                self.assertEqual(self.run_cli('--message', 'Bild', '--attachment', str(image)), 1)
        image.unlink()
        self.assertEqual(self.run_cli('--message', 'Bild', '--attachment', str(image)), 1)
        self.urlopen.assert_not_called()

    def test_missing_credentials_do_not_send(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.run_cli("--message", "Klart"), 1)
        self.urlopen.assert_not_called()
        self.assertIn("PUSHOVER_API_TOKEN", self.stderr.getvalue())
        self.assertIn("PUSHOVER_USER_KEY", self.stderr.getvalue())

    def test_private_credentials_file_and_environment_override(self):
        self.credentials_file.write_text(json.dumps({
            "PUSHOVER_API_TOKEN": "local-token", "PUSHOVER_USER_KEY": "local-user",
        }))
        for env, token in (({}, "local-token"), ({"PUSHOVER_API_TOKEN": "override"}, "override")):
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                self.respond({"status": 1})
                self.assertEqual(self.run_cli("--message", "Klart"), 0)
                payload = parse_qs(self.urlopen.call_args.args[0].data.decode())
                self.assertEqual(payload["token"], [token])
                self.assertEqual(payload["user"], ["local-user"])

    def test_invalid_private_credentials_do_not_send_or_leak(self):
        for body in ('secret-malformed-json', '[]', '{"PUSHOVER_API_TOKEN": 123}'):
            with self.subTest(body=body), patch.dict(os.environ, {}, clear=True):
                self.credentials_file.write_text(body)
                self.assertEqual(self.run_cli("--message", "Klart"), 1)
        self.urlopen.assert_not_called()
        self.assertNotIn("secret-malformed-json", self.stderr.getvalue())

    def test_invalid_input_does_not_send(self):
        for args in (
            ("--message", " "), ("--message", "x" * 1025),
            ("--message", "x", "--title", "x" * 251),
            ("--message", "x", "--priority", "2"),
        ):
            with self.subTest(args=args), self.assertRaises(SystemExit) as result:
                self.run_cli(*args)
            self.assertEqual(result.exception.code, 2)
        self.urlopen.assert_not_called()

    def test_maximum_message_and_title_are_accepted(self):
        self.respond({"status": 1})
        self.assertEqual(self.run_cli("--message", "å" * 1024, "--title", "ä" * 250), 0)

    def test_http_error_is_redacted_and_not_retried(self):
        self.urlopen.side_effect = HTTPError(
            sender.ENDPOINT, 400, "Bad Request", {},
            io.BytesIO(b'{"status":0,"errors":["invalid test-app-token test-user-key"]}'),
        )
        self.assertEqual(self.run_cli("--message", "Klart"), 1)
        self.urlopen.assert_called_once()
        self.assertIn("HTTP 400", self.stderr.getvalue())
        self.assertNotIn("test-app-token", self.stderr.getvalue())
        self.assertNotIn("test-user-key", self.stderr.getvalue())

    def test_api_failure_is_not_reported_as_success(self):
        self.respond({"status": 0, "errors": ["user identifier is invalid"]})
        self.assertEqual(self.run_cli("--message", "Klart"), 1)
        self.assertIn("user identifier is invalid", self.stderr.getvalue())
        self.assertEqual(self.stdout.getvalue(), "")

    def test_network_errors_are_not_retried(self):
        for error in (URLError("connection reset"), TimeoutError(), IncompleteRead(b"")):
            with self.subTest(error=error):
                self.urlopen.reset_mock()
                self.urlopen.side_effect = error
                self.assertEqual(self.run_cli("--message", "Klart"), 1)
                self.urlopen.assert_called_once()
        self.assertIn("outcome unknown", self.stderr.getvalue())

    def test_malformed_response_is_not_retried(self):
        for body in (b"not JSON", b"[]", b"{}", b"\xff"):
            with self.subTest(body=body):
                self.urlopen.reset_mock()
                self.urlopen.return_value.__enter__.return_value = io.BytesIO(body)
                self.assertEqual(self.run_cli("--message", "Klart"), 1)
                self.urlopen.assert_called_once()
        self.assertIn("outcome unknown", self.stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
