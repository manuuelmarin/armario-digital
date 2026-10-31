"""Real HTTP against an isolated loopback double, not a running language model."""

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from armario.ai_client import RESPONSE_LIMIT, TEXT_MODEL, VISION_MODEL, ModelError, OllamaClient


@pytest.fixture
def service(monkeypatch):
    state = {"requests": [], "digest": "a" * 64, "status": 200, "raw": None}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond(None)

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            self.respond(json.loads(body))

        def respond(self, body):
            state["requests"].append((self.path, body))
            payload = state["raw"]
            if payload is None:
                value = (
                    {"models": [{"name": TEXT_MODEL, "digest": state["digest"]}]}
                    if self.path == "/api/tags"
                    else {
                        "model": TEXT_MODEL,
                        "done": True,
                        "done_reason": "stop",
                        "message": {"content": '{"rankings":[]}'},
                    }
                )
                payload = json.dumps(value).encode()
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original = http.client.HTTPConnection

    def connection(host, port, timeout):
        assert (host, port) == ("127.0.0.1", 11434)
        return original(host, server.server_port, timeout=timeout)

    monkeypatch.setattr(http.client, "HTTPConnection", connection)
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_chat_protocol_releases_model_and_sends_text_only(service, monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://external.invalid:3128")
    value, digest = OllamaClient(timeout=2).chat(
        TEXT_MODEL, "System", "Only text", {"type": "object"}
    )
    assert value == {"rankings": []} and digest == "a" * 64
    assert [path for path, _ in service["requests"]] == ["/api/tags", "/api/chat", "/api/tags"]
    body = service["requests"][1][1]
    assert body["keep_alive"] == 0 and body["stream"] is False
    assert body["options"]["num_ctx"] == 8192
    assert not any("images" in message for message in body["messages"])


@pytest.mark.parametrize(
    "status,raw",
    [
        (302, b"redirect"),
        (503, b"service failure"),
        (200, b"not JSON"),
        (200, b"x" * (RESPONSE_LIMIT + 1)),
    ],
)
def test_transport_rejects_redirects_failures_bad_and_large_responses(service, status, raw):
    service.update(status=status, raw=raw)
    with pytest.raises(ModelError):
        OllamaClient(timeout=2).models()
    assert len(service["requests"]) == 1


def test_absent_and_cloud_models_never_trigger_download_or_fallback(service):
    service["raw"] = json.dumps({"models": [{"name": "qwen-cloud", "digest": "x"}]}).encode()
    with pytest.raises(ModelError, match="Falta el modelo local"):
        OllamaClient(timeout=2).chat(TEXT_MODEL, "System", "text", {})
    assert service["requests"] == [("/api/tags", None)]
    with pytest.raises(ModelError, match="no recibe imágenes"):
        # Availability is checked first; install the expected local text model in the double.
        service["raw"] = json.dumps({"models": [{"name": TEXT_MODEL, "digest": "a"}]}).encode()
        OllamaClient(timeout=2).chat(TEXT_MODEL, "System", "text", {}, image="base64-image")
    with pytest.raises(ModelError):
        OllamaClient(timeout=2).chat("arbitrary-model", "System", "text", {})


def test_incomplete_model_response_cannot_be_accepted(service, monkeypatch):
    client = OllamaClient(timeout=2)
    monkeypatch.setattr(client, "models", lambda: {TEXT_MODEL: "digest"})
    for response in (
        {"model": TEXT_MODEL, "done": False, "message": {"content": "{}"}},
        {"model": VISION_MODEL, "done": True, "message": {"content": "{}"}},
        {"model": TEXT_MODEL, "done": True, "done_reason": "length", "message": {"content": "{}"}},
    ):
        service["raw"] = json.dumps(response).encode()
        with pytest.raises(ModelError, match="incompleta"):
            client.chat(TEXT_MODEL, "System", "text", {})
