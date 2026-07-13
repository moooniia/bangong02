import json
import mimetypes
import socket
import sys
import threading
import time
import traceback
import urllib.parse
import webbrowser
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from invoice_assistant.archive import archive_records
from invoice_assistant.app_info import APP_NAME
from invoice_assistant.record_builder import scan_invoice_files
from invoice_assistant.report_exporter import export_invoice_report, records_from_dicts

ROOT = Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", ROOT))
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else ROOT
STATIC_DIR = RESOURCE_ROOT / "web"
DEFAULT_FOLDER = Path.home() / "Desktop" / "发票助手" / "文件"
OUTPUT_DIR = APP_DIR / "outputs"
LOG_PATH = APP_DIR / "发票工具箱.log"
_SCAN_JOBS = {}
_SCAN_JOBS_LOCK = threading.Lock()


def _write_log(message: str):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n"
    stream = getattr(sys, "stderr", None)
    if stream:
        try:
            stream.write(line)
            stream.flush()
        except Exception:
            pass
    try:
        with LOG_PATH.open("a", encoding="utf-8") as log_file:
            log_file.write(line)
    except Exception:
        pass


def _announce(message: str):
    stream = getattr(sys, "stdout", None)
    if stream:
        try:
            stream.write(f"{message}\n")
            stream.flush()
        except Exception:
            pass
    _write_log(message)


class LoggingThreadingHTTPServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        _write_log(f"请求处理失败 {client_address}:\n{traceback.format_exc()}")


class InvoiceAssistantHandler(BaseHTTPRequestHandler):
    server_version = "InvoiceAssistant2/0.1"

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/file":
            query = urllib.parse.parse_qs(parsed.query)
            target = Path(query.get("path", [""])[0]).expanduser().resolve()
            if not target.exists() or not target.is_file():
                self.send_error(404, "File not found")
                return
            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(target.stat().st_size))
            self.end_headers()
            return
        self.send_error(404, "Not found")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send_file(STATIC_DIR / "design.html")
            return
        if parsed.path.startswith("/static/"):
            rel = parsed.path.removeprefix("/static/")
            self._send_file((STATIC_DIR / rel).resolve())
            return
        if parsed.path == "/api/scan":
            query = urllib.parse.parse_qs(parsed.query)
            folder = Path(query.get("folder", [str(DEFAULT_FOLDER)])[0]).expanduser()
            self._handle_scan(folder)
            return
        if parsed.path == "/api/scan/progress":
            query = urllib.parse.parse_qs(parsed.query)
            self._send_scan_progress(query.get("id", [""])[0])
            return
        if parsed.path == "/api/file":
            query = urllib.parse.parse_qs(parsed.query)
            target = Path(query.get("path", [""])[0]).expanduser()
            self._send_local_file(target)
            return
        if parsed.path == "/api/preview":
            query = urllib.parse.parse_qs(parsed.query)
            target = Path(query.get("path", [""])[0]).expanduser()
            self._send_pdf_preview(target)
            return
        if parsed.path == "/api/select-folder":
            self._select_folder()
            return
        self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/scan/start":
            self._start_scan_job()
            return
        if parsed.path == "/api/export":
            self._handle_export()
            return
        self.send_error(404, "Not found")

    def log_message(self, fmt, *args):
        host = self.client_address[0] if self.client_address else "-"
        _write_log("%s - %s" % (host, fmt % args))

    def _handle_scan(self, folder: Path):
        if not folder.exists() or not folder.is_dir():
            self._send_json({"error": f"文件夹不存在：{folder}"}, status=400)
            return
        records = [record.as_dict() for record in scan_invoice_files(folder)]
        self._send_json({"folder": str(folder), "records": records})

    def _start_scan_job(self):
        try:
            payload = self._read_json()
            folder = Path(str(payload.get("folder", ""))).expanduser()
            if not folder.exists() or not folder.is_dir():
                self._send_json({"error": f"文件夹不存在：{folder}"}, status=400)
                return
            job_id = uuid.uuid4().hex
            job = {
                "id": job_id,
                "folder": folder,
                "status": "queued",
                "total": 0,
                "completed": 0,
                "current": "",
                "records": [],
                "error": "",
            }
            with _SCAN_JOBS_LOCK:
                _SCAN_JOBS[job_id] = job
            threading.Thread(target=_run_scan_job, args=(job_id,), daemon=True).start()
            self._send_json({"job_id": job_id})
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def _send_scan_progress(self, job_id: str):
        with _SCAN_JOBS_LOCK:
            job = _SCAN_JOBS.get(job_id)
            if not job:
                self._send_json({"error": "识别任务不存在"}, status=404)
                return
            snapshot = {
                "job_id": job["id"],
                "folder": str(job["folder"]),
                "status": job["status"],
                "total": job["total"],
                "completed": job["completed"],
                "current": job["current"],
                "records": [record.as_dict() for record in sorted(job["records"], key=lambda item: item.row_id)],
                "error": job["error"],
            }
        self._send_json(snapshot)

    def _select_folder(self):
        try:
            selected = _choose_windows_folder()
            self._send_json({"path": str(selected) if selected else ""})
        except Exception as exc:
            _write_log(f"文件夹选择失败：{traceback.format_exc()}")
            self._send_json({"error": str(exc)}, status=500)

    def _handle_export(self):
        try:
            payload = self._read_json()
            records = records_from_dicts(payload.get("records", []))
            folder = Path(payload.get("folder", "")).expanduser()
            output_folder = Path(payload.get("output_folder", "")).expanduser()
            archive_mode = str(payload.get("archive_mode", "month"))
            if output_folder.exists() and output_folder.is_dir():
                output_dir = output_folder
            elif folder.exists() and folder.is_dir():
                output_dir = folder
            else:
                output_dir = OUTPUT_DIR
            archive_records(records, output_dir, mode=archive_mode)
            output_path = output_dir / "发票报表_安全版_需人工确认.xlsx"
            export_invoice_report(records, output_path)
            self._send_json({"path": str(output_path), "records": [record.as_dict() for record in records]})
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length)
        return json.loads(data.decode("utf-8")) if data else {}

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        if not _is_relative_to(path, STATIC_DIR) or not path.exists() or not path.is_file():
            self.send_error(404, "Not found")
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_local_file(self, path: Path):
        path = path.resolve()
        if not path.exists() or not path.is_file():
            self.send_error(404, "File not found")
            return
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_pdf_preview(self, path: Path):
        if path.suffix.lower() != ".pdf" or not path.exists() or not path.is_file():
            self.send_error(404, "PDF file not found")
            return
        try:
            import fitz

            document = fitz.open(str(path))
            try:
                if not document.page_count:
                    self.send_error(404, "PDF has no pages")
                    return
                pixmap = document[0].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                body = pixmap.tobytes("png")
            finally:
                document.close()
        except Exception as exc:
            self.send_error(500, str(exc))
            return
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _choose_windows_folder() -> Path | None:
    if sys.platform != "win32":
        raise RuntimeError("文件夹选择器仅支持 Windows")
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    root.update()
    try:
        selected = filedialog.askdirectory(parent=root, title="请选择文件夹")
        return Path(selected) if selected else None
    finally:
        root.destroy()


def _run_scan_job(job_id: str):
    with _SCAN_JOBS_LOCK:
        job = _SCAN_JOBS.get(job_id)
        if not job:
            return
        job["status"] = "running"

    def report_progress(completed: int, total: int, path: Path, record):
        with _SCAN_JOBS_LOCK:
            job = _SCAN_JOBS.get(job_id)
            if not job:
                return
            job["total"] = total
            job["completed"] = completed
            job["current"] = path.name
            job["records"].append(record)

    try:
        with _SCAN_JOBS_LOCK:
            folder = _SCAN_JOBS[job_id]["folder"]
        records = scan_invoice_files(folder, progress=report_progress)
        with _SCAN_JOBS_LOCK:
            job = _SCAN_JOBS.get(job_id)
            if job:
                job["records"] = records
                job["total"] = len(records)
                job["completed"] = len(records)
                job["current"] = ""
                job["status"] = "completed"
    except Exception as exc:
        _write_log(f"识别任务失败 {job_id}：\n{traceback.format_exc()}")
        with _SCAN_JOBS_LOCK:
            job = _SCAN_JOBS.get(job_id)
            if job:
                job["status"] = "failed"
                job["error"] = str(exc)


def _make_server(start_port: int):
    if start_port == 0:
        server = LoggingThreadingHTTPServer(("127.0.0.1", 0), InvoiceAssistantHandler)
        return server, server.server_address[1]
    for port in range(start_port, start_port + 20):
        try:
            server = LoggingThreadingHTTPServer(("127.0.0.1", port), InvoiceAssistantHandler)
            return server, port
        except OSError:
            continue
    raise RuntimeError(f"无法启动本机服务，端口 {start_port}-{start_port + 19} 都不可用")


def _wait_until_ready(port: int, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main():
    start_port = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    server, port = _make_server(start_port)
    url = f"http://127.0.0.1:{port}"
    _announce(f"{APP_NAME}已启动：{url}")

    def open_browser_later():
        time.sleep(0.5)
        try:
            webbrowser.open(url)
        except Exception:
            _write_log(f"浏览器打开失败：\n{traceback.format_exc()}")

    threading.Thread(target=open_browser_later, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _write_log(f"程序启动失败:\n{traceback.format_exc()}")
        raise



