# BB-Team Archiver

Download BB-Team forum threads for offline reading — multi-page HTML with embedded images, avatars, and JSON metadata.

## Requirements

- Python 3.9+

```bash
pip install requests beautifulsoup4 lxml
```

For the web UI:

```bash
pip install flask
```

## Usage

### CLI

```bash
python -m bb_archive <thread_id>
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--start N` | 1 | First page |
| `--end N` | all | Last page |
| `--output / -o DIR` | `thread_<id>` | Output directory |
| `--delay SEC` | 1.5 | Seconds between requests |
| `--jobs N` | 1 | Concurrent page fetches |
| `--no-images` | — | Skip images and avatars |

### Web UI

```bash
python -m bb_archive ui
```

Opens a browser at `http://127.0.0.1:8080`. Fill in the thread ID and click Archive — progress streams in real-time. When done, click the button to browse the result.

Optional flags: `--host 0.0.0.0 --port 8080`

## Standalone executable

```bash
pip install pyinstaller flask
pyinstaller --onefile --name bb-archive run.py
```

Output: `dist/bb-archive` (Linux) / `dist/bb-archive.exe` (Windows). No Python required on the target machine.

**Linux:** after downloading, make it executable:
```bash
chmod +x bb-archive-linux
./bb-archive-linux ui
```

**Windows:** double-click the `.exe` or run from Command Prompt — no extra steps needed.

### Cross-platform builds

Push to `main` and the CI workflow (`.github/workflows/build.yml`) automatically builds Linux + Windows binaries and creates a GitHub Release.

## Output

- `index.html` / `page_NN.html` — self-contained pages with pagination bar and "Go to page" input
- `images/` — downloaded content images and user avatars
- `metadata.json` — all posts in structured JSON format
