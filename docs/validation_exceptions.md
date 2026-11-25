# Validation Exceptions & Special Rules

This document describes all deviations from standard min/typ/max validation logic
applied to specific device types and metric categories.

---

## Standard Validation Logic (Baseline)

For reference, the default check for a general (non-TV, non-corporate) device:

1. **avg check**: `actual_avg >= expected_typ` — FAIL if below.
2. **min check**: `actual_min >= expected_min` — FAIL if below.
3. Both conditions must pass for a PASS result.

---

## 1. TV Exceptions

### 1.1 Contrast — 6.5% Tolerance on Typical

**Constant**: `CONTRAST_TOLERANCE_FOR_TV = 0.065`

For TV devices, the expected typical (`typ`) for Contrast is reduced by 6.5% before comparison:

```
effective_typ = expected_typ × (1.0 − 0.065)
```

The avg check is then: `actual_avg >= effective_typ`.

> Applies only to: `Contrast`
>
> Source: SUPPLYCC-3063 (tolerance agreed with BU, QA, QC and production; the TV quality standard
> only says "< original OC specification").

---

### 1.2 Skip Avg/Typ Check — Min-Only Validation

**Constant**: `AVG_FAIL_SKIP_KEYS_FOR_TV`

For the following metrics, the avg/typ check is **completely skipped** for TVs.
Only the **min** threshold is enforced:

| Metric              | JSON Key          |
|---------------------|-------------------|
| Brightness Uniformity | `Brightness_uniformity` |

**Pass condition**: `actual_min >= expected_min`

> `Temperature` is also listed in `AVG_FAIL_SKIP_KEYS_FOR_TV`, but it is handled earlier by its own
> min/max logic (see Section 3.1), so this entry has no effect.

> Color gamut metrics are **not** in this list: for TVs they use the standard
> check (`actual_min >= expected_min` and `actual_avg >= expected_typ`), as the
> TV quality standard requires gamut "according to specification".

---

### 1.3 Color Temperature Brightness Compensation — Not Applied

The TV quality standard (15.7) states: if the color temperature is outside 7300~11300 K,
brightness should be +10 nit for each 500 K of difference. The standard does not define
the base value for this addition, so the rule is **not implemented**; `Temperature` is checked
by min/max bounds only (see Section 3.1).

---

### 1.4 Brightness & Contrast — Measurement Point Differs

For TVs, a different measurement location is used as the reference point:

| Metric     | TV                        | Monitor/Corporate     |
|------------|---------------------------|-----------------------|
| Brightness (typ) | `WhiteColor` measurement | `Center` measurement |
| Contrast   | `WhiteColor / BlackColor` | `Center / BlackColor` |

This affects the raw `typ` value stored in the JSON report before any comparison.

---

## 2. Corporate Device Exceptions (Non-TV)

Corporate devices are **non-TV** (`IsTV = false`). Both tolerances below are
applied by reducing the effective `expected_typ` before the avg check.

### 2.1 General Metrics — 5% Tolerance on Typical

**Constant**: `CORPORATE_DEVICES_TYP_TOLERANCE = 0.05`

```
effective_typ = expected_typ × (1.0 − 0.05)
```

**Applies to**:

| YAML Key               | Display Name           |
|------------------------|------------------------|
| `Brightness`           | Brightness             |
| `Brightness_uniformity`| Brightness Uniformity  |
| `Contrast`             | Contrast               |

The `tolerance_applied` field in the comparison report records the original and adjusted typ values.

---

### 2.2 Color Gamut Metrics — 2% Tolerance on Typical

**Constant**: `CORPORATE_DEVICES_CG_TOLERANCE = 0.02`

```
effective_typ = expected_typ × (1.0 − 0.02)
```

**Applies to**:

| YAML Key         | Display Name           |
|------------------|------------------------|
| `Cg_rgb_area`    | sRGB Gamut Area (%)    |
| `Cg_ntsc_area`   | NTSC Gamut Area (%)    |
| `Cg_dcip3_area`  | DCI-P3 Gamut Area (%)  |
| `Cg_rgb`         | sRGB Gamut Coverage (%) |
| `Cg_ntsc`        | NTSC Gamut Coverage (%) |
| `Cg_dcip3`       | DCI-P3 Coverage (%)    |

---

### 2.3 Contrast — Min-Only for Specific Configs

**Constants**: `AVG_FAIL_SKIP_KEYS_FOR_CORPORATE`, `CONTRAST_TYP_SKIP_CONFIGS`

For device configs matching `CONTRAST_TYP_SKIP_CONFIGS` (`SDNB-16iA`, `SDNB-M16iA`; matched by
`startswith`, so factory suffixes like `SDNB-16iA_CH19` also match) the avg/typ check of `Contrast`
is skipped; only `actual_min >= expected_min` is enforced. Other non-TV devices keep the 5% typ tolerance.

---

## 3. Universal Special Cases (All Device Types)

### 3.1 Temperature — Min/Max Bounds Only, No Avg/Typ Check

Temperature is validated exclusively against **min** and **max** bounds.
The `typ` and `avg` values are not used for pass/fail decisions.

**Rules**:
- FAIL if `actual_max > expected_max` (too high)
- FAIL if `actual_min < expected_min` (too low)
- PASS if both bounds are satisfied

---

### 3.2 Delta E — Inverted Logic (Lower Is Better)

Delta E is in `LOWER_IS_BETTER_KEYS`. The comparison logic is reversed:

| Standard logic (higher is better) | Delta E logic (lower is better) |
|------------------------------------|----------------------------------|
| FAIL if `avg < typ`                | FAIL if `avg > typ`             |
| FAIL if `max > max_bound`          | FAIL if `max > max_bound`       |

**Rules**:
- FAIL if `actual_max > expected_max`
- FAIL if `actual_avg > expected_typ`
- PASS if both are within bounds

---

### 3.3 Coordinate Metrics — Min/Max Bounds Only

Metrics listed in `COORDINATE_TEST_KEYS` use a dedicated bounds-only check.
No `typ` or `avg` comparison is performed.

**Affected keys**: `Red_x`, `Red_y`, `Green_x`, `Green_y`, `Blue_x`, `Blue_y`,
`White_x`, `White_y`

**Rules**:
- FAIL if `actual_min < expected_min`
- FAIL if `actual_max > expected_max`
- No tolerance applied
- N/A if any value is missing or non-numeric

---

## 4. Cell Status Highlighting Exceptions

The HTML report uses color-coded cells. Rules differ by metric category:

| Category             | Red (fail)                  | Yellow (warning)        | White (normal) |
|----------------------|-----------------------------|-------------------------|----------------|
| General metrics      | `value < min` or `> max`    | `value < typ`           | `value >= typ` |
| Coordinate metrics   | `value < min` or `> max`    | — (not applicable)      | otherwise      |
| Delta E (inverted)   | `value > max`               | `value > typ`           | otherwise      |

---

## 5. Dynamic Metric Visibility

Color gamut metrics are **hidden** from the report if no expected values
(`min`, `typ`, `max`) are defined in the device YAML config.

**Affected keys**: all `Cg_<color space>_area`, `Cg_<color space>`, `Cg_<color space>_uv_area`,
`Cg_<color space>_uv` keys (`CG_METRIC_KEYS`, one set per registered color space, e.g. `Cg_rgb_area`, `Cg_ntsc`, `Cg_dcip3`)

If all three expected values are `None` or absent for a gamut metric,
it is excluded from both the summary table and the CIE diagram legend.

---

## 6. Summary Table

| Rule                          | Applies to     | Metrics                                       | Detail                                      |
|-------------------------------|----------------|-----------------------------------------------|---------------------------------------------|
| Contrast 6.5% tolerance       | TV only        | Contrast                                      | `effective_typ = typ × 0.935`              |
| Skip avg/typ, check min only  | TV only        | Uniformity                                    | Only `actual_min >= expected_min`          |
| Measurement point differs     | TV only        | Brightness, Contrast                          | `WhiteColor` instead of `Center`           |
| 5% typ tolerance              | Corporate only | Brightness, Uniformity, Contrast              | `effective_typ = typ × 0.95`              |
| 2% typ tolerance              | Corporate only | All gamut metrics                             | `effective_typ = typ × 0.98`              |
| Min/max bounds only           | All devices    | Temperature, all coordinates                  | No avg/typ comparison                      |
| Inverted logic                | All devices    | Delta E                                       | Lower is better: FAIL if `avg > typ`       |
| Dynamic visibility            | All devices    | All gamut metrics                             | Hidden if no expected values in YAML       |
