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
* **`sct_app.toml`**, **`requirements.in`**, **`requirements.lock`**: Release descriptor and dependencies (released from the SCT Updater repository).

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

This applies to all `Cg_rgb*`, `Cg_ntsc*`, `Cg_dcip3*`, `Cg_rec2020*` variants (both CIE 1931 xy and CIE 1976 u'v') and `Delta_e`.

### Color coordinate tolerance

Instead of specifying `min`/`max` for each color coordinate manually, use `Coordinates_tolerance`:

```yaml
Coordinates_tolerance: 0.030  # applied to all coordinate metrics
Red_x:
  typ: 0.638  # min/max computed automatically as 0.638 ± 0.030
```

-----

## Precision of the verdict

A value is judged against its specification **as it is shown in the report**: it is rounded half up (as Excel does) to the precision of its metric, and that number is compared with `min`, `typ` and `max`. The number on the screen is the number the device is accepted by. The measured values themselves are never rounded before this step (the measurement files carry the digits of the analyzer, the calculations of contrast and color difference are not rounded); `REPORT_PRECISION` in `src/report.py` is the only table.

| Metric | Decimals | What the rounding allows |
|---|---|---|
| Brightness, contrast, color temperature | 0 | ±0.5 of the unit (about 0.15% of a brightness of 350 cd/m²) |
| Brightness uniformity, gamut area and coverage, ΔE | 1 | ±0.05 |
| Coordinates (x, y of red, green, blue, white, center) | 3 | ±0.0005 |
| Black luminance (no specification, shown only) | 4 | ±0.00005 cd/m² |

A new metric needs an entry in `REPORT_PRECISION`; a test fails when a metric of the example specification has none.

## Release through the Screen Check Suite tool

The module is described by `sct_app.toml`, `requirements.in` and `requirements.lock` in this repository. Releases are made from the SCT Updater repository:

```bash
uv run tools/release/app_release.py app <path to this repo> 1.6.0 --upload
```

The tool uploads the code and only the wheels that are missing on the server; the Updater installs them into `apps/report_generator` and the shared files into `config/`. Full process and rules: `docs/module-release.md` in the SCT Updater repository.

To test the module the way clients get it, release it to the `dev` list (`app` with `--upload`) and update a test Updater running with `NC_CHANNEL=dev`.
