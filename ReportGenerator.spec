# ReportGenerator.spec

# --- 1. Список всех .py файлов вашего приложения ---
# Мы вручную указываем PyInstaller, что собирать.
app_scripts = [
    'main.py',
    'src/calculate.py',
    'src/graphics_hepler.py',
    'src/helpers.py',
    'src/parse.py',
    'src/report.py'
]

# --- 2. Анализ (Analysis) ---
a = Analysis(
    app_scripts,  # <-- ИЗМЕНЕНО: Явно передаем список
    pathex=[],      # <-- ИЗМЕНЕНО: Оставляем пустым
    binaries=[],
    datas=[('config', 'config')], # <-- ПРАВИЛЬНО: 'config' остается здесь
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test', 'PyQt5', 'PySide6',
        'pydoc_data', 'distutils', 'setuptools',
        'pytest', 'pytest_mock', 'PyInstaller',
        'cx_Freeze'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# --- БЛОК РУЧНОЙ ОЧИСТКИ (Для 'config') ---
# Этот блок все еще нужен, чтобы хуки не "втянули" config в lib.
a.binaries = [x for x in a.binaries if not x[0].startswith('config')]
a.pure = [x for x in a.pure if not x[0].startswith('config')]
a.zipfiles = [x for x in a.zipfiles if not x[0].startswith('config')]
# --- КОНЕЦ БЛОКА ОЧИСТКИ ---


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
    upx_dir='.venv/Scripts/',
    upx_exclude=[
        '_uuid.pyd', 'python3.dll',
        'VCRUNTIME140.dll', 'VCRUNTIME140_1.dll'
    ],
    runtime_tmpdir=None,
    console=True,
    icon=None,
    contents_directory='lib_report_generator' # <-- ПРАВИЛЬНО
)

# --- 5. COLLECT (Финальная папка) ---
coll = COLLECT(
    exe,
    a.binaries, # <-- Очищено от 'config'
    a.zipfiles, # <-- Очищено от 'config'
    a.datas,    # <-- 'config' существует ТОЛЬКО здесь
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ReportGenerator',
)