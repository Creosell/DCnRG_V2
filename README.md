# Report Generator

A comprehensive tool for analyzing display device test results (TVs, Monitors). It parses JSON measurement logs, calculates key metrics (Brightness, Contrast, Color Gamut, DeltaE), compares them against expected standards, and generates interactive HTML reports with CIE chromaticity diagrams.

## Project Structure

* **`src/`**: Source code (calculations, parsing, reporting logic).
* **`data/`**: Input folder. Place raw JSON device reports here.
* **`config/`**: Configuration files (SVG templates, expected result YAMLs).
* **`results/`**: Output folder for HTML reports.
* **`test_reports/`**: Intermediate JSON aggregated reports.
* **`report_archive/`**: Zipped archives of processed sessions.
* **`main.py`**: Entry point of the application.
* **`release_manager.py`**: Script for building and uploading releases.

---

## Environment Setup

### 1. Create local environment

**Using standard Python venv:**

```bash
    python -m venv .venv
````

### 2\. Activation of venv

**Windows:**

```bash
    .venv\Scripts\activate
```

**macOS and Linux:**

```bash
    source .venv/bin/activate
```

### 3\. Install dependencies

```bash
    pip install -r requirements.txt
```

-----

## Usage

### Generating Reports

1.  Place the raw JSON measurement files into the `data/` folder.
2.  Ensure you have the correct configuration YAML in `config/device_configs/` matching your device name (e.g., `MyMonitorModel.yaml`). If not found, `config/expected_result.yaml` is used as a fallback.
3.  Run the main script:

<!-- end list -->

```bash
    python main.py
```

4.  Find the generated **HTML report** in the `results/` folder.
5.  Processed files and reports will be archived in `report_archive/`.

-----

## Release & Deployment

The project uses `release_manager.py` to build the executable (via PyInstaller), package it, and upload it to the Nextcloud server. This script manages its own dependencies using `uv`.

### Prerequisites

Install `uv`:

```bash
    pip install uv
```

### Command Syntax

```bash
    uv run --active release_manager.py [mode] [path] [product_id] [version] [flags]
```

**Arguments:**

  * `mode`:
      * `zip`: Archives the contents of `path` into a single `.zip` file and uploads it.
      * `files`: Uploads files individually (preserves structure).
  * `path`: Path to the build/dist directory (e.g., `dist/ReportGenerator`). **Note:** Contents are placed at the root of the release.
  * `product_id`: Unique identifier (e.g., `report_generator`).
  * `version`: Version string (e.g., `1.0.0`).

**Flags:**
  * `--active`: Runs UV using current .venv of a project.
  * `--build`: Runs PyInstaller before packaging. It looks for a `.spec` file matching the folder name of your `path`.
  * `--upload`: Uploads immediately without confirmation prompt.
  * `--include [path]`: Adds a directory to the release (preserved as a subfolder).

### Example: Build, Zip, and Upload

This command builds the `.exe` from the spec file, zips the contents of `dist/ReportGenerator`, includes the `config` folder, and uploads it as version `1.0.0`.

```bash
    uv run --active release_manager.py zip build\dist\ReportGenerator report_generator 1.0.0 --include config --build --upload
```

### Example: Upload Files Only

If you only want to upload the raw files without zipping:

```bash
    uv run --active release_manager.py files build\dist\ReportGenerator report_generator 1.0.0 --upload
```

## Optimization: UPX Compression

To significantly reduce the size of the generated `.exe` file (and consequently the final `.zip` archive), it is recommended to use **UPX** (Ultimate Packer for eXecutables).

**Setup Steps:**
1. Download the latest version of UPX from the official [GitHub releases page](https://github.com/upx/upx/releases).
2. Extract the downloaded archive.
3. Copy the `upx.exe` file directly into your virtual environment's scripts folder:
   * **Path:** `.venv\Scripts\` (Windows)

PyInstaller automatically detects UPX in this folder and will use it to compress the binary during the `--build` process.