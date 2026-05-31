#!/usr/bin/env python3
"""Lazy LLM server — auto-starts llama.cpp on first request, auto-kills after idle."""
import subprocess, os, time, json, sys, threading
from http.server import HTTPServer, BaseHTTPRequestHandler

MODEL = os.path.expanduser('~/llm/qwen2.5-coder-32b-q4_k_m.gguf')
PORT = 8081  # Listen on different port, let this proxy be the public face
BACKEND_PORT = 18080  # Internal port for llama.cpp
LOG = os.path.expanduser('~/llm/server.log')
IDLE_KILL = 300  # 5 minutes

server_proc = None
last_activity = 0
lock = threading.Lock()

def ensure_running():
    global server_proc, last_activity
    with lock:
        last_activity = time.time()
        if server_proc is None or server_proc.poll() is not None:
            print(f'[{time.strftime("%H:%M:%S")}] Starting llama.cpp...', flush=True)
            server_proc = subprocess.Popen([
                os.path.expanduser('~/.conda/envs/py310/bin/python'), '-m', 'llama_cpp.server',
                '--model', MODEL, '--n_gpu_layers', '99', '--n_ctx', '32768',
                '--host', '127.0.0.1', '--port', str(BACKEND_PORT), '--chat_format', 'chatml',
            ], stdout=open(LOG, 'a'), stderr=subprocess.STDOUT)
            # Wait for startup
            for _ in range(60):
                time.sleep(0.5)
                if server_proc.poll() is not None:
                    raise RuntimeError(f'Server exited: {server_proc.poll()}')
                try:
                    import urllib.request
                    urllib.request.urlopen(f'http://127.0.0.1:{BACKEND_PORT}/health', timeout=2)
                    print(f'[{time.strftime("%H:%M:%S")}] Server ready!', flush=True)
                    break
                except: pass
        return f'http://127.0.0.1:{BACKEND_PORT}'

def idle_monitor():
    global server_proc
    while True:
        time.sleep(60)
        with lock:
            if server_proc and server_proc.poll() is None:
                if time.time() - last_activity > IDLE_KILL:
                    print(f'[{time.strftime("%H:%M:%S")}] Idle timeout, stopping server...', flush=True)
                    server_proc.terminate()
                    server_proc = None

threading.Thread(target=idle_monitor, daemon=True).start()

class Proxy(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            backend = ensure_running()
            body_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(body_len)
            import urllib.request
            req = urllib.request.Request(backend + self.path, data=body, headers={'Content-Type': 'application/json'})
            resp = urllib.request.urlopen(req, timeout=300)
            data = resp.read()
            self.send_response(resp.status)
            for k, v in resp.getheaders():
                if k.lower() not in ('transfer-encoding',): self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            print(f'Error: {e}', flush=True)
            self.send_response(502)
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'ok', 'backend': f'http://127.0.0.1:{BACKEND_PORT}'}).encode())

    def log_message(self, fmt, *args): pass

print(f'Lazy Server on :{PORT} -> backend :{BACKEND_PORT} (idle kill: {IDLE_KILL}s)', flush=True)
HTTPServer(('0.0.0.0', PORT), Proxy).serve_forever()
