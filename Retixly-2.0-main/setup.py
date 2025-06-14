import sys
from pathlib import Path
from cx_Freeze import setup, Executable

# Ścieżki do plików
current_dir = Path(__file__).parent

# Pliki do dołączenia
include_files = [
    ("assets", "assets"),
    ("translations", "translations"), 
    ("data", "data"),
    ("src", "src"),
]

# Pakiety do dołączenia
packages = [
    "PyQt6",
    "PIL", 
    "rembg",
    "numpy",
    "cv2",
    "onnxruntime",
    "requests",
    "cryptography",
    "boto3",
    "webbrowser",
    "json",
    "pathlib",
    "logging",
    "subprocess",
    "threading",
    "urllib",
    "ssl",
    "socket",
]

# Moduły do jawnego dołączenia
includes = [
    "PyQt6.QtCore",
    "PyQt6.QtGui", 
    "PyQt6.QtWidgets",
    "PIL.Image",
    "PIL.ImageFilter",
    "PIL.ImageEnhance",
    "rembg.bg",
    "numpy.core._multiarray_umath",
    "requests.adapters",
    "cryptography.hazmat.backends.openssl",
    "src.controllers.settings_controller",
    "src.views.main_window",
    "src.core.updater",
]

# Moduły do pominięcia  
excludes = [
    "tkinter",
    "unittest",
    "test",
    "pydoc",
    "doctest",
    "jupyter",
    "IPython",
    "matplotlib.tests",
    "numpy.tests",
]

# Opcje budowania - NAPRAWIONE
build_exe_options = {
    "packages": packages,
    "includes": includes,
    "excludes": excludes,
    "include_files": include_files,
    "optimize": 2,
    # USUNIĘTE: "include_msvcrt": True,  # Ta opcja nie istnieje
    "zip_include_packages": ["*"],
    "zip_exclude_packages": [],
}

# Konfiguracja exe
executable = Executable(
    script="main.py",
    base="Win32GUI" if sys.platform == "win32" else None,
    target_name="Retixly.exe",
    icon="assets/icons/app_icon.ico" if (current_dir / "assets/icons/app_icon.ico").exists() else None,
)

# Setup
setup(
    name="Retixly",
    version="1.0.0",
    description="AI-powered background removal tool",
    author="RetixlySoft",
    options={"build_exe": build_exe_options},
    executables=[executable],
)