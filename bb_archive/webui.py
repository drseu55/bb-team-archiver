import io
import os
import queue
import socket
import sys
import threading
import time
import webbrowser

try:
    from flask import Flask, render_template_string, Response, request, send_from_directory
except ImportError:
    print(
        "Flask is required for the web UI.\n"
        "Install it with:  pip install flask"
    )
    sys.exit(1)

HTML = """\
<!DOCTYPE html>
<html lang="bg">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BB-Team Archiver</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Oxygen,Ubuntu,sans-serif;
  background:#f4f5f7;color:#1a1a2e;line-height:1.6;padding:20px}
.container{max-width:600px;margin:0 auto}
h1{font-size:1.5rem;margin-bottom:4px;color:#16213e}
p{color:#666;font-size:0.9rem;margin-bottom:20px}
.card{background:#fff;border-radius:8px;padding:20px 24px;
  box-shadow:0 1px 3px rgba(0,0,0,.08)}
.row{margin-bottom:14px}
.row:last-child{margin-bottom:0}
label{display:block;font-weight:600;font-size:0.85rem;margin-bottom:3px;color:#16213e}
input[type=text],input[type=number]{width:100%;padding:8px 10px;border:1px solid #e0e0e0;
  border-radius:4px;font-size:0.95rem;outline:none}
input:focus{border-color:#e94560}
.check-row{display:flex;align-items:center;gap:8px;margin-bottom:0}
.check-row input{width:auto}
.btn{padding:10px 28px;background:#e94560;color:#fff;border:none;border-radius:6px;
  font-size:1rem;cursor:pointer;font-weight:600;width:100%;margin-top:8px}
.btn:hover{background:#d63850}
.btn:disabled{opacity:.6;cursor:not-allowed}
#output{background:#1a1a2e;color:#e0e0e0;padding:14px 16px;border-radius:6px;
  margin-top:16px;white-space:pre-wrap;font-family:Consolas,Monaco,'Courier New',monospace;
  font-size:0.85rem;line-height:1.5;display:none;max-height:400px;overflow-y:auto}
.msg-done{color:#4ade80;font-weight:600}
.msg-fail{color:#f87171;font-weight:600}
.open-link{display:inline-block;margin-top:8px;padding:8px 16px;
  background:#16213e;color:#fff;border-radius:6px;text-decoration:none;font-weight:600}
.open-link:hover{background:#e94560}
.archive-link{display:block;padding:6px 0;color:#16213e;text-decoration:none;font-size:0.9rem}
.archive-link:hover{color:#e94560}
.hint{font-size:0.8rem;color:#999;margin-top:2px}
</style>
</head>
<body>
<div class="container">
<h1>BB-Team Archiver</h1>
<p>Изтегли тема от bb-team.org за офлайн четене</p>
<div class="card">
<form id="form">
<div class="row">
<label>ID на темата</label>
<input type="number" name="thread_id" placeholder="например 43647" required>
<div class="hint">Номерът от URL-а: /viewthread/&lt;ID&gt;</div>
</div>
<div class="row" style="display:flex;gap:10px">
<div style="flex:1">
<label>Начална страница</label>
<input type="number" name="start" value="1" min="1">
</div>
<div style="flex:1">
<label>Крайна страница</label>
<input type="number" name="end" value="0" min="0">
<div class="hint">0 = всички</div>
</div>
</div>
<div class="row">
<label>Папка за запис</label>
<input type="text" name="output" placeholder="остави празно за thread_XXX">
</div>
<div class="row" style="display:flex;gap:10px">
<div style="flex:1">
<label>Закъснение (сек)</label>
<input type="number" name="delay" value="1.5" step="0.1" min="0">
</div>
<div style="flex:1">
<label>Паралелни заявки</label>
<input type="number" name="jobs" value="1" min="1" max="20">
</div>
</div>
<div class="row check-row">
<input type="checkbox" name="no_images" id="noimg">
<label for="noimg" style="margin:0">Пропусни изображенията</label>
</div>
<button type="submit" class="btn" id="go-btn">Архивирай</button>
</form>
</div>
<pre id="output"></pre>
<div id="archive-list-container"></div>
</div>
<script>
document.getElementById('form').onsubmit = async function(e) {
  e.preventDefault();
  var btn = document.getElementById('go-btn');
  btn.disabled = true;
  btn.textContent = 'Архивиране…';
  var out = document.getElementById('output');
  out.style.display = 'block';
  out.textContent = '';
  var fd = new FormData(this);
  try {
    var resp = await fetch('/archive', {method:'POST', body:fd});
    var reader = resp.body.getReader();
    var dec = new TextDecoder();
    while (true) {
      var r = await reader.read();
      if (r.done) break;
      var text = dec.decode(r.value, {stream:true});
      var viewIdx = text.indexOf('__VIEW__:');
      if (viewIdx !== -1) {
        var before = text.slice(0, viewIdx);
        if (before) {
          out.innerHTML += before.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        }
        var sid = text.slice(viewIdx + 9).trim();
        var viewUrl = window.location.origin + '/view/' + encodeURIComponent(sid) + '/index.html';
        out.innerHTML += '<br><a href="' + viewUrl + '" class="open-link" target="_blank">📂 Отвори архива</a><br>';
      } else {
        out.innerHTML += text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      }
      out.scrollTop = out.scrollHeight;
    }
  } catch(e) {
    out.textContent += '\\nГрешка: ' + e.message + '\\n';
  }
  btn.disabled = false;
  btn.textContent = 'Архивирай';
};
setInterval(async function() {
  var el = document.getElementById('archive-list-container');
  if (!el) return;
  var resp = await fetch('/archive-list');
  var html = await resp.text();
  el.innerHTML = html;
}, 3000);
</script>
</body>
</html>
"""

app = Flask(__name__)
_archives: dict[str, tuple[str, str]] = {}  # session_id -> (thread_id, abs_dir)
_nonce = 0


def _scan_archives() -> None:
    for entry in sorted(os.listdir(os.getcwd())):
        if not entry.startswith("thread_"):
            continue
        path = os.path.join(os.getcwd(), entry)
        if not os.path.isdir(path) or not os.path.isfile(os.path.join(path, "index.html")):
            continue
        tid = entry.removeprefix("thread_")
        sid = f"d_{entry}"
        if sid not in _archives:
            _archives[sid] = (tid, path)


def _archive_list_html() -> str:
    items = ""
    for sid, (tid, _) in sorted(_archives.items(), reverse=True):
        items += f'<a href="/view/{sid}/index.html" class="archive-link" target="_blank">Thread #{tid}</a>\n'
    if not items:
        return ""
    return (
        '<div class="card" style="margin-top:16px">'
        '<div style="font-weight:600;font-size:0.85rem;margin-bottom:4px;color:#16213e">'
        "Архивирани теми</div>" + items + "</div>"
    )


@app.route("/")
def index():
    return HTML.replace(
        '<div id="archive-list-container"></div>',
        f'<div id="archive-list-container">{_archive_list_html()}</div>',
    )


@app.route("/archive-list")
def archive_list():
    return _archive_list_html()


@app.route("/archive", methods=["POST"])
def archive():
    thread_id = request.form["thread_id"]

    start = request.form.get("start", "").strip()
    end = request.form.get("end", "").strip()
    out_param = request.form.get("output", "").strip()
    delay = request.form.get("delay", "").strip()
    jobs = request.form.get("jobs", "").strip()
    no_images = request.form.get("no_images")

    if out_param:
        output_dir = out_param
    else:
        output_dir = f"thread_{thread_id}"
    abs_dir = os.path.abspath(output_dir)
    global _nonce
    _nonce += 1
    session_id = f"a{_nonce}"

    def generate():
        argv = ["bb-archive", thread_id]
        if start and start != "1":
            argv.extend(["--start", start])
        if end and end != "0":
            argv.extend(["--end", end])
        if out_param:
            argv.extend(["-o", out_param])
        if delay and delay != "1.5":
            argv.extend(["--delay", delay])
        if jobs and jobs != "1":
            argv.extend(["--jobs", jobs])
        if no_images:
            argv.append("--no-images")

        q: queue.Queue = queue.Queue()

        class Capture:
            encoding = "utf-8"
            errors = "replace"

            def __init__(self, q):
                self._q = q

            def write(self, s):
                self._q.put(s)

            def flush(self):
                pass

        def run():
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            old_argv = sys.argv
            sys.stdout = Capture(q)
            sys.stderr = sys.stdout
            sys.argv = argv
            try:
                from .cli import main

                main()
            except SystemExit:
                pass
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                sys.argv = old_argv
                q.put(None)

        threading.Thread(target=run, daemon=True).start()

        while True:
            line = q.get()
            if line is None:
                break
            yield line

        yield "\n✅ Archive complete!\n"
        _archives[session_id] = (thread_id, abs_dir)
        yield f"__VIEW__:{session_id}\n"

    return Response(generate(), mimetype="text/plain")


@app.route("/view/<session_id>/<path:filename>")
def view_archive(session_id, filename):
    entry = _archives.get(session_id)
    if not entry:
        return "Archive not found", 404
    return send_from_directory(entry[1], filename)


def main(args=None):
    host = "127.0.0.1"
    port = 8080
    if args:
        i = 0
        while i < len(args):
            if args[i] == "--host" and i + 1 < len(args):
                host = args[i + 1]
                i += 2
            elif args[i] == "--port" and i + 1 < len(args):
                port = int(args[i + 1])
                i += 2
            else:
                i += 1

    url = f"http://{host}:{port}"
    print(f"  Web UI: {url}")

    _scan_archives()

    def _start():
        app.run(host=host, port=port, debug=False)

    t = threading.Thread(target=_start, daemon=True)
    t.start()

    for _ in range(15):
        time.sleep(0.3)
        s = socket.socket()
        s.settimeout(0.5)
        try:
            s.connect((host, port))
            s.close()
            break
        except Exception:
            s.close()

    webbrowser.open(url)
    t.join()
