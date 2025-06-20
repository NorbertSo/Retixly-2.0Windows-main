# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('translations', 'translations'),
        ('data', 'data'),
        ('src', 'src'),
    ],
    hiddenimports=[
        # PyQt6 - KOMPLETNE
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui', 
        'PyQt6.QtWidgets',
        'PyQt6.QtNetwork',
        'PyQt6.sip',
        
        # PIL/Pillow - KOMPLETNE
        'PIL',
        'PIL.Image',
        'PIL.ImageFilter',
        'PIL.ImageEnhance',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL.ImageOps',
        'PIL._imaging',
        
        # REMBG - WSZYSTKIE POTRZEBNE MODUŁY
        'rembg',
        'rembg.bg',
        'rembg.models',
        'rembg.sessions',
        'rembg.models.u2net',
        'rembg.models.silueta',
        'rembg.sessions.u2net',
        'rembg.sessions.silueta',
        
        # ONNX Runtime - KOMPLETNE
        'onnxruntime',
        'onnxruntime.capi',
        'onnxruntime.capi.onnxruntime_pybind11_state',
        'onnxruntime.capi._pybind_state',
        'onnxruntime.backend',
        'onnxruntime.backend.backend',
        
        # NumPy - WSZYSTKIE KLUCZOWE MODUŁY
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        'numpy.core._multiarray_tests',
        'numpy.core.multiarray',
        'numpy.core.umath',
        'numpy.linalg',
        'numpy.linalg._umath_linalg',
        'numpy.linalg.lapack_lite',
        'numpy.linalg._umath_linalg',
        'numpy.fft',
        'numpy.fft.pocketfft_internal',
        'numpy.random',
        'numpy.random._pickle',
        'numpy.random._common',
        'numpy.random.bit_generator',
        'numpy.random._bounded_integers',
        'numpy.random.mtrand',
        'numpy.random._mt19937',
        'numpy.random._pcg64',
        'numpy.random._philox',
        'numpy.random._sfc64',
        
        # OpenCV - KLUCZOWE MODUŁY
        'cv2',
        'cv2.cv2',
        
        # Cryptography - KOMPLETNE
        'cryptography',
        'cryptography.fernet',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.serialization',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.backends.openssl.backend',
        
        # Requests - KOMPLETNE
        'requests',
        'requests.adapters',
        'requests.auth',
        'requests.cookies',
        'requests.models',
        'requests.sessions',
        'requests.packages',
        'requests.packages.urllib3',
        'urllib3',
        'urllib3.util',
        'urllib3.util.retry',
        'urllib3.contrib',
        'urllib3.contrib.pyopenssl',
        
        # Boto3 - KLUCZOWE MODUŁY
        'boto3',
        'boto3.session',
        'boto3.resources',
        'boto3.resources.base',
        'botocore',
        'botocore.client',
        'botocore.session',
        'botocore.awsrequest',
        'botocore.endpoint',
        'botocore.auth',
        'botocore.credentials',
        'botocore.config',
        'botocore.exceptions',
        
        # Wewnętrzne moduły aplikacji - WSZYSTKIE
        'src',
        'src.controllers',
        'src.controllers.settings_controller',
        'src.controllers.license_controller', 
        'src.controllers.image_processor',
        'src.views',
        'src.views.main_window',
        'src.core',
        'src.core.updater',
        'src.core.engine_manager',
        'src.core.image_engine',
        'src.core.carvekit_engine',
        'src.core.windows_engine',
        
        # Standardowe Python - KOMPLETNE
        'webbrowser',
        'json',
        'pathlib',
        'logging',
        'logging.handlers',
        'os',
        'sys',
        'subprocess',
        'threading',
        'time',
        'datetime',
        'hashlib',
        'base64',
        'urllib',
        'urllib.request',
        'urllib.parse',
        'urllib.error',
        'zipfile',
        'tempfile',
        'shutil',
        'glob',
        'functools',
        'importlib',
        'importlib.util',
        'importlib.machinery',
        'ssl',
        'socket',
        'http',
        'http.client',
        'email',
        'email.mime',
        'email.mime.text',
        'email.mime.multipart',
        'collections',
        'collections.abc',
        'enum',
        'typing',
        'typing_extensions',
        'concurrent',
        'concurrent.futures',
        'multiprocessing',
        'queue',
        'platform',
        'warnings',
        'traceback',
        'copy',
        'pickle',
        'io',
        'gc',
        're',
        'math',
        'random',
        'string',
        'uuid',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Usuń TYLKO rzeczywiście niepotrzebne
        'tkinter',
        'turtle',
        'pydoc',
        'doctest', 
        'unittest',
        'test',
        'jupyter',
        'IPython',
        'notebook',
        'matplotlib.tests',
        'numpy.tests',
        'scipy.tests',
        'pandas.tests',
        'setuptools',
        'pip',
        'wheel',
        'distutils',
        
        # Usuń tylko jeśli nie używasz
        # 'pillow_heif',  # Usuń tylko jeśli nie potrzebujesz HEIC
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    icon='assets/icons/app_icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Retixly'
)