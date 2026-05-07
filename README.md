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
* **`tools/release/release_manager.py`**: Script for building and uploading releases.

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

### Exit Codes

The application returns different exit codes to indicate success or failure:

- **0 (SUCCESS)**: At least one device report was successfully generated
- **1 (GENERAL_ERROR)**: Unexpected error occurred during processing
- **2 (NO_DATA_FOUND)**: No JSON files found in `data/` folder, or all report generation attempts failed
- **3 (CONFIG_ERROR)**: Failed to create required directories

**Example usage in scripts:**
```bash
python main.py
if [ $? -eq 0 ]; then
    echo "Reports generated successfully"
else
    echo "Report generation failed with code $?"
fi
```

-----

## Device Configuration

Each device model is configured via a YAML file in `config/device_configs/`. The file name must match the `DeviceConfiguration` field in the measurement JSON (e.g., `SDX-43U4169.yaml`). If no matching file is found, `config/configuration_example.yaml` is used as a fallback.

### Metric fields

Each metric supports three threshold fields:

```yaml
Brightness:
  min: 260   # Lower bound — values below this are highlighted red (critical)
  typ: 280   # Target — values below this but above min are highlighted yellow (warning)
  max: None  # Upper bound — set to None if no upper limit is required
```

### Dynamic visibility

**Color Gamut** (`Cg_*`) and **Delta E** columns are hidden in the **Main Test Results** comparison table when all of `min`/`typ`/`max` are `None`. This prevents empty columns from appearing for metrics that are not part of the device specification.

> **Note:** Device Reports always display the full measured data regardless of this setting.

| Goal | How to configure |
|------|-----------------|
| Show a metric in Main Test Results | Set at least one of `min`/`typ`/`max` to a number |
| Hide a metric in Main Test Results | Leave all of `min`/`typ`/`max` as `None` |

This applies to all `Cg_rgb*`, `Cg_ntsc*`, `Cg_dcip3*` variants (both CIE 1931 xy and CIE 1976 u'v') and `Delta_e`.

### Color coordinate tolerance

Instead of specifying `min`/`max` for each color coordinate manually, use `Coordinates_tolerance`:

```yaml
Coordinates_tolerance: 0.030  # applied to all coordinate metrics
Red_x:
  typ: 0.638  # min/max computed automatically as 0.638 ± 0.030
```

-----

## Release & Deployment

The project uses `tools/release/release_manager.py` to build the executable (via PyInstaller), package it, and upload it to the Nextcloud server. This script manages its own dependencies using `uv`.

### Prerequisites

Install `uv`:

```bash
    pip install uv
```

### Command Syntax

```bash
    uv run --active tools/release/release_manager.py [mode] [path] [product_id] [version] [flags]
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
    uv run --active tools/release/release_manager.py zip build\dist\ReportGenerator report_generator 1.0.0 --include config --build --upload
```

### Example: Upload Files Only

If you only want to upload the raw files without zipping:

```bash
    uv run --active tools/release/release_manager.py files build\dist\ReportGenerator report_generator 1.0.0 --upload
```

## Optimization: UPX Compression

To significantly reduce the size of the generated `.exe` file (and consequently the final `.zip` archive), it is recommended to use **UPX** (Ultimate Packer for eXecutables).

**Setup Steps:**
1. Download the latest version of UPX from the official [GitHub releases page](https://github.com/upx/upx/releases).
2. Extract the downloaded archive.
3. Copy the `upx.exe` file directly into your virtual environment's scripts folder:
   * **Path:** `.venv\Scripts\` (Windows)

PyInstaller automatically detects UPX in this folder and will use it to compress the binary during the `--build` process.