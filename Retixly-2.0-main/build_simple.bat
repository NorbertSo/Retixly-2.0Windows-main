# -*- mode: python ; coding: utf-8 -*-
# build_simple.spec - Lightweight build bez dużych pakietów AI

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('bootstrap_ui.py', '.'),  # Bootstrap UI
        ('assets', 'assets'),      # Ikony i style
        ('translations', 'translations'),  # Tłumaczenia
        ('src', 'src'),            # Kod aplikacji
        ('version_info.txt', '.'), # Version info
    ],
    hiddenimports=[
        'bootstrap_ui',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore', 
        'PyQt6.QtGui',
        'PIL',
        'PIL.Image',
        'requests',
        'cryptography',
        'pathlib',
        'importlib',
        'subprocess',
        'threading',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # WYKLUCZAMY duże pakiety AI - będą pobrane przez bootstrap
        'torch',
        'torchvision', 
        'torchaudio',
        'rembg',
        'numpy',
        'cv2',
        'opencv-python',
        'onnxruntime',
        'boto3',
        'botocore',
        'google-auth',
        'google-api-python-client',
        'pillow-heif',
        
        # Standardowe wykluczenia
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'jupyter',
        'IPython',
        'notebook',
        'setuptools',
        'pip',
        'wheel',
        'distutils',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Retixly',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    versrsrc='version_info.txt',  # Version info
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Retixly',
)