import os
import shutil
from pathlib import Path
import mimetypes

def get_supported_formats():
    """Zwraca listę obsługiwanych formatów obrazów."""
    return [
        'jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff', 'tif', 
        'webp', 'heic', 'heif', 'svg', 'ico'
    ]

def is_image_file(file_path):
    """Sprawdza czy plik to obraz."""
    if not os.path.isfile(file_path):
        return False
    
    # Sprawdź rozszerzenie
    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    if ext in get_supported_formats():
        return True
    
    # Sprawdź MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type.startswith('image/'):
        return True
    
    return False

def get_files_from_directory(directory, recursive=True):
    """Pobiera wszystkie pliki obrazów z katalogu."""
    image_files = []
    directory = Path(directory)
    
    if not directory.exists():
        return image_files
    
    if recursive:
        for file_path in directory.rglob('*'):
            if file_path.is_file() and is_image_file(str(file_path)):
                image_files.append(str(file_path))
    else:
        for file_path in directory.iterdir():
            if file_path.is_file() and is_image_file(str(file_path)):
                image_files.append(str(file_path))
    
    return sorted(image_files)

def create_output_directory(base_path, create_if_not_exists=True):
    """Tworzy katalog wyjściowy."""
    output_path = Path(base_path)
    
    if create_if_not_exists and not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
    
    return str(output_path)

def generate_output_filename(input_path, suffix="", new_extension=None):
    """Generuje nazwę pliku wyjściowego."""
    input_path = Path(input_path)
    
    # Podstawowa nazwa bez rozszerzenia
    base_name = input_path.stem
    
    # Dodaj suffix jeśli podano
    if suffix:
        base_name += f"_{suffix}"
    
    # Użyj nowego rozszerzenia lub zachowaj oryginalne
    if new_extension:
        extension = new_extension
    else:
        extension = input_path.suffix
    
    # Upewnij się, że rozszerzenie zaczyna się od kropki
    if extension and not extension.startswith('.'):
        extension = f".{extension}"
    
    return f"{base_name}{extension}"

def safe_filename(filename):
    """Tworzy bezpieczną nazwę pliku."""
    # Usuń niebezpieczne znaki
    unsafe_chars = '<>:"/\\|?*'
    safe_name = filename
    
    for char in unsafe_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Usuń wielokrotne podkreślenia
    while '__' in safe_name:
        safe_name = safe_name.replace('__', '_')
    
    # Usuń podkreślenia z początku i końca
    safe_name = safe_name.strip('_')
    
    return safe_name

def copy_file_with_metadata(source, destination):
    """Kopiuje plik zachowując metadane."""
    try:
        shutil.copy2(source, destination)
        return True
    except Exception as e:
        print(f"Błąd kopiowania pliku {source} do {destination}: {e}")
        return False

def get_file_size_mb(file_path):
    """Zwraca rozmiar pliku w MB."""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0

def cleanup_temp_files(temp_directory):
    """Czyści pliki tymczasowe."""
    temp_path = Path(temp_directory)
    
    if not temp_path.exists():
        return
    
    for file_path in temp_path.iterdir():
        try:
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Nie można usunąć {file_path}: {e}")

def validate_output_path(output_path):
    """Waliduje ścieżkę wyjściową."""
    output_path = Path(output_path)
    
    # Sprawdź czy rodzic istnieje
    if not output_path.parent.exists():
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Nie można utworzyć katalogu: {e}"
    
    # Sprawdź czy można pisać
    try:
        test_file = output_path.parent / ".test_write"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        return False, f"Brak uprawnień do zapisu: {e}"
    
    return True, ""

def batch_rename_files(file_list, pattern="{name}_{index}"):
    """Wsadowa zmiana nazw plików."""
    renamed_files = []
    
    for index, file_path in enumerate(file_list, 1):
        file_path = Path(file_path)
        
        # Generuj nową nazwę
        new_name = pattern.format(
            name=file_path.stem,
            index=str(index).zfill(3),
            original=file_path.stem
        )
        
        new_path = file_path.parent / f"{new_name}{file_path.suffix}"
        
        # Unikaj konfliktów nazw
        counter = 1
        while new_path.exists():
            temp_name = f"{new_name}_{counter}"
            new_path = file_path.parent / f"{temp_name}{file_path.suffix}"
            counter += 1
        
        renamed_files.append((str(file_path), str(new_path)))
    
    return renamed_files

def get_directory_size(directory):
    """Oblicza rozmiar katalogu."""
    total_size = 0
    directory = Path(directory)
    
    if not directory.exists():
        return 0
    
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            try:
                total_size += file_path.stat().st_size
            except Exception:
                continue
    
    return total_size / (1024 * 1024)  # Zwróć w MB

def create_backup(file_path, backup_suffix="_backup"):
    """Tworzy kopię zapasową pliku."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        return None
    
    backup_name = f"{file_path.stem}{backup_suffix}{file_path.suffix}"
    backup_path = file_path.parent / backup_name
    
    # Znajdź unikalną nazwę
    counter = 1
    while backup_path.exists():
        backup_name = f"{file_path.stem}{backup_suffix}_{counter}{file_path.suffix}"
        backup_path = file_path.parent / backup_name
        counter += 1
    
    try:
        shutil.copy2(file_path, backup_path)
        return str(backup_path)
    except Exception as e:
        print(f"Błąd tworzenia kopii zapasowej: {e}")
        return None