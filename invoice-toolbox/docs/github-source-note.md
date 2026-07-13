# GitHub source note

This folder contains the maintainable source code for Invoice Toolbox.

Generated binaries are intentionally excluded:

- `winui_app/Backend/InvoiceToolbox.Worker.exe`
- `winui_app/AppPackages/`
- `build/`, `dist/`, `outputs/`
- signing certificates such as `.pfx`

Build the Python worker from `native_worker.py` / `InvoiceToolbox.Worker.spec`, then place the generated worker executable under `winui_app/Backend/` before creating a local MSIX package.
