import json
import sys
import threading
import hashlib
from pathlib import Path

from invoice_assistant.record_builder import SUPPORTED_SUFFIXES, scan_invoice_files
from invoice_assistant.archive import archive_records
from invoice_assistant.models import InvoiceRecord
from invoice_assistant.report_exporter import export_invoice_report


_stdout_lock = threading.Lock()
_IMAGE_PREVIEW_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def send(payload):
    # Keep the process protocol ASCII-only so Windows code pages cannot corrupt JSON framing.
    message = json.dumps(payload, ensure_ascii=True) + "\n"
    with _stdout_lock:
        sys.stdout.write(message)
        sys.stdout.flush()


def main():
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request.get("command") == "warmup":
                import fitz
                send({"event": "warmup_complete"})
                continue
            if request.get("command") == "export":
                records = [InvoiceRecord.from_dict(item) for item in request.get("records", [])]
                output = Path(str(request.get("output_folder", ""))).expanduser()
                output.mkdir(parents=True, exist_ok=True)
                archive_records(records, output, mode=str(request.get("archive_mode", "month")), name_fields=request.get("name_fields"), separator=str(request.get("name_separator", "_")))
                report = export_invoice_report(records, output / "发票整理报表.xlsx", field_order=request.get("report_fields"))
                send({"event": "export_complete", "path": str(report), "records": [record.as_dict() for record in records]})
                continue
            if request.get("command") == "preview":
                import fitz
                source = Path(str(request.get("path", ""))).expanduser()
                if not source.is_file():
                    send({"ok": False, "error": "preview file not found"})
                    continue
                stat = source.stat()
                key_raw = f"{source.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
                key = hashlib.sha1(key_raw.encode("utf-8")).hexdigest()[:16]
                target = Path.home() / "AppData" / "Local" / "Temp" / f"invoice_toolbox_preview_{key}.jpg"
                if not target.exists():
                    if source.suffix.lower() in _IMAGE_PREVIEW_SUFFIXES:
                        from PIL import Image, ImageOps

                        image = ImageOps.exif_transpose(Image.open(source)).convert("RGB")
                        image.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
                        image.save(target, quality=88, optimize=True)
                    else:
                        document = fitz.open(source)
                        try:
                            page = document.load_page(0)
                            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
                            pixmap.save(str(target))
                        finally:
                            document.close()
                send({"event": "preview_complete", "path": str(target)})
                continue
            if request.get("command") != "scan":
                send({"ok": False, "error": "unsupported command"})
                continue
            folder = Path(str(request.get("folder", ""))).expanduser()
            if not folder.is_dir():
                send({"ok": False, "error": f"folder not found: {folder}"})
                continue

            def progress(done, total, path, record):
                send({"event": "progress", "done": done, "total": total, "name": path.name, "record": record.as_dict() if record else None})

            exclude_folder = str(request.get("exclude_folder", "")).strip()
            excluded = [Path(exclude_folder).expanduser()] if exclude_folder else []
            candidates = [path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES]
            excluded_count = 0
            if excluded:
                root = excluded[0].resolve()
                for path in candidates:
                    try:
                        path.resolve().relative_to(root)
                        excluded_count += 1
                    except ValueError:
                        pass
            send({"event": "scan_started", "total": len(candidates) - excluded_count, "excluded": excluded_count})
            records = scan_invoice_files(folder, progress=progress, exclude_roots=excluded)
            send({"event": "complete", "records": [record.as_dict() for record in records]})
        except Exception as exc:
            send({"ok": False, "error": str(exc)})


if __name__ == "__main__":
    main()
