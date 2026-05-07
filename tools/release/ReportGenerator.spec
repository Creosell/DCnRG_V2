# ReportGenerator.spec

import os
ROOT = os.path.normpath(os.path.join(SPECPATH, '../..'))

# --- 1. Список всех .py файлов вашего приложения ---
app_scripts = [
    os.path.join(ROOT, 'main.py'),
    os.path.join(ROOT, 'src/calculate.py'),
    os.path.join(ROOT, 'src/graphics_helper.py'),
    os.path.join(ROOT, 'src/helpers.py'),
    os.path.join(ROOT, 'src/parse.py'),
    os.path.join(ROOT, 'src/report.py')
]

# --- 2. Анализ (Analysis) ---
a = Analysis(
    app_scripts,
    pathex=[ROOT],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test', 'PyQt5', 'PySide6',
        'pydoc_data', 'distutils', 'setuptools',
        'pytest', 'pytest_mock', 'pyinstaller', 'nc_py_api',
        'requests', 'urllib3'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# --- 3. PYZ (Python-библиотеки) ---
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# --- 4. EXE (Исполняемый файл) ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ReportGenerator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_dir=SPECPATH,
    upx_exclude=[
        '_uuid.pyd', 'python3.dll',
        'VCRUNTIME140.dll', 'VCRUNTIME140_1.dll'
    ],
    runtime_tmpdir=None,
    console=True,
    icon=None,
    contents_directory='lib_report_generator'
)

# --- 5. COLLECT (Финальная папка) ---
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ReportGenerator',
)
