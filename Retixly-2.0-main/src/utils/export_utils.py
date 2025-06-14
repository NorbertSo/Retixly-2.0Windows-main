import os
import csv
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import json
import io
from PIL import Image

# Importy opcjonalne - będą używane tylko jeśli dostępne
try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from ftplib import FTP
    HAS_FTP = True
except ImportError:
    HAS_FTP = False

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    from google.oauth2.service_account import Credentials
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False

def export_image(image, original_path, export_settings):
    """Eksportuje obraz zgodnie z ustawieniami."""
    try:
        export_type = export_settings.get('save_location', 'Lokalnie')
        
        if export_type == 'Lokalnie':
            return export_to_local(image, original_path, export_settings)
        elif export_type == 'Google Drive':
            return export_to_gdrive(image, original_path, export_settings)
        elif export_type == 'Amazon S3':
            return export_to_s3(image, original_path, export_settings)
        elif export_type == 'FTP':
            return export_to_ftp(image, original_path, export_settings)
        elif export_type == 'imgBB':
            return export_to_imgbb(image, original_path, export_settings)
        else:
            raise ValueError(f"Nieobsługiwany typ eksportu: {export_type}")
            
    except Exception as e:
        print(f"Błąd eksportu obrazu: {e}")
        return None

def export_to_local(image, original_path, settings):
    """Eksportuje obraz lokalnie."""
    output_dir = settings.get('output_directory', 'output')
    filename = generate_filename(original_path, settings)
    output_path = Path(output_dir) / filename
    
    # Upewnij się, że katalog istnieje
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Konwertuj format jeśli potrzeba
    save_format = settings.get('format', {}).get('type', 'PNG')
    quality = settings.get('format', {}).get('quality', 85)
    
    if save_format.upper() == 'JPEG' and image.mode in ('RGBA', 'LA'):
        # Konwertuj na białe tło dla JPEG
        background = Image.new('RGB', image.size, 'white')
        if image.mode == 'RGBA':
            background.paste(image, mask=image.split()[-1])
        else:
            background.paste(image)
        image = background
    
    # Zapisz obraz
    save_kwargs = {'format': save_format}
    if save_format.upper() in ['JPEG', 'WEBP']:
        save_kwargs['quality'] = quality
    if save_format.upper() == 'PNG':
        save_kwargs['optimize'] = True
    
    image.save(output_path, **save_kwargs)
    return str(output_path)

def export_to_gdrive(image, original_path, settings):
    """Eksportuje obraz do Google Drive."""
    if not HAS_GOOGLE_API:
        raise ImportError("Google API libraries not available. Install: pip install google-api-python-client google-auth")
        
    try:
        # Przygotuj credentials (w prawdziwej aplikacji byłyby z ustawień)
        credentials = settings.get('credentials', {})
        
        service = build('drive', 'v3', credentials=credentials)
        
        # Przygotuj plik do uploadu
        filename = generate_filename(original_path, settings)
        
        # Konwertuj obraz do bytes
        img_bytes = io.BytesIO()
        save_format = settings.get('format', {}).get('type', 'PNG')
        image.save(img_bytes, format=save_format)
        img_bytes.seek(0)
        
        # Upload do Google Drive
        file_metadata = {
            'name': filename,
            'parents': [settings.get('folder_id', '')]
        }
        
        media = MediaIoBaseUpload(
            img_bytes, 
            mimetype=f'image/{save_format.lower()}'
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id,webViewLink'
        ).execute()
        
        return file.get('webViewLink')
        
    except Exception as e:
        print(f"Błąd eksportu do Google Drive: {e}")
        return None

def export_to_s3(image, original_path, settings):
    """Eksportuje obraz do Amazon S3."""
    if not HAS_BOTO3:
        raise ImportError("Boto3 library not available. Install: pip install boto3")
        
    try:
        credentials = settings.get('credentials', {})
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=credentials.get('access_key'),
            aws_secret_access_key=credentials.get('secret_key')
        )
        
        # Przygotuj plik
        filename = generate_filename(original_path, settings)
        bucket_name = credentials.get('bucket')
        
        # Konwertuj obraz do bytes
        img_bytes = io.BytesIO()
        save_format = settings.get('format', {}).get('type', 'PNG')
        image.save(img_bytes, format=save_format)
        img_bytes.seek(0)
        
        # Upload do S3
        s3_client.upload_fileobj(
            img_bytes,
            bucket_name,
            filename,
            ExtraArgs={'ContentType': f'image/{save_format.lower()}'}
        )
        
        # Zwróć URL
        url = f"https://{bucket_name}.s3.amazonaws.com/{filename}"
        return url
        
    except Exception as e:
        print(f"Błąd eksportu do S3: {e}")
        return None

def export_to_ftp(image, original_path, settings):
    """Eksportuje obraz przez FTP."""
    if not HAS_FTP:
        raise ImportError("FTP library not available")
        
    try:
        credentials = settings.get('credentials', {})
        
        # Połącz z FTP
        ftp = FTP(credentials.get('host'))
        ftp.login(credentials.get('user'), credentials.get('password'))
        
        # Przejdź do katalogu
        if credentials.get('path'):
            ftp.cwd(credentials.get('path'))
        
        # Przygotuj plik
        filename = generate_filename(original_path, settings)
        
        # Konwertuj obraz do bytes
        img_bytes = io.BytesIO()
        save_format = settings.get('format', {}).get('type', 'PNG')
        image.save(img_bytes, format=save_format)
        img_bytes.seek(0)
        
        # Upload przez FTP
        ftp.storbinary(f'STOR {filename}', img_bytes)
        ftp.quit()
        
        # Zwróć URL (w prawdziwej aplikacji byłby z ustawień)
        base_url = f"ftp://{credentials.get('host')}"
        if credentials.get('path'):
            base_url += f"/{credentials.get('path')}"
        
        return f"{base_url}/{filename}"
        
    except Exception as e:
        print(f"Błąd eksportu przez FTP: {e}")
        return None
def export_to_imgbb(image, original_path, settings):
    """Eksportuje obraz do imgBB."""
    if not HAS_REQUESTS:
        raise ImportError("Requests library not available. Install: pip install requests")
        
    try:
        credentials = settings.get('credentials', {})
        api_key = credentials.get('api_key')
        
        if not api_key:
            raise ValueError("Brak klucza API dla imgBB")
        
        # Przygotuj obraz
        img_bytes = io.BytesIO()
        save_format = settings.get('format', {}).get('type', 'PNG')
        image.save(img_bytes, format=save_format)
        img_bytes.seek(0)
        
        # Upload do imgBB
        response = requests.post(
            'https://api.imgbb.com/1/upload',
            params={'key': api_key},
            files={'image': img_bytes.getvalue()}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data['data']['url']
            else:
                raise Exception("imgBB API zwróciło błąd")
        else:
            raise Exception(f"HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Błąd eksportu do imgBB: {e}")
        return None

def validate_export_settings(settings):
    """Waliduje ustawienia eksportu."""
    errors = []
    
    export_type = settings.get('save_location', 'Lokalnie')
    
    if export_type == 'Lokalnie':
        output_dir = settings.get('output_directory')
        if not output_dir:
            errors.append("Nie określono katalogu wyjściowego")
        elif not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                errors.append(f"Nie można utworzyć katalogu: {e}")
                
    elif export_type == 'Google Drive':
        credentials = settings.get('credentials', {})
        if not credentials.get('folder_id'):
            errors.append("Brak ID folderu Google Drive")
            
    elif export_type == 'Amazon S3':
        credentials = settings.get('credentials', {})
        required_fields = ['access_key', 'secret_key', 'bucket']
        for field in required_fields:
            if not credentials.get(field):
                errors.append(f"Brak wymaganego pola S3: {field}")
                
    elif export_type == 'FTP':
        credentials = settings.get('credentials', {})
        required_fields = ['host', 'user', 'password']
        for field in required_fields:
            if not credentials.get(field):
                errors.append(f"Brak wymaganego pola FTP: {field}")
                
    elif export_type == 'imgBB':
        credentials = settings.get('credentials', {})
        if not credentials.get('api_key'):
            errors.append("Brak klucza API imgBB")
    
    return errors

def generate_filename(original_path, settings):
    """Generuje nazwę pliku zgodnie z wzorcem - rozszerzona wersja."""
    try:
        original_path = Path(original_path)
        pattern = settings.get('filename_pattern', '{original_name}')

        # Rozszerzone zmienne
        variables = {
            'original_name': original_path.stem,
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
            'date': datetime.now().strftime('%Y%m%d'),
            'time': datetime.now().strftime('%H%M%S'),
            'identifier': settings.get('identifier', ''),  # Nowa zmienna dla CSV/XML
            'size': settings.get('size', 'unknown')
        }

        # Zastępowanie zmiennych w wzorcu
        filename = pattern
        for var, value in variables.items():
            placeholder = f'{{{var}}}'
            if placeholder in filename:
                filename = filename.replace(placeholder, str(value))

        # Obsługa rozszerzenia pliku
        save_format = settings.get('format', {}).get('type', 'PNG')
        extension = save_format.lower()
        if extension == 'jpeg':
            extension = 'jpg'

        return f"{filename}.{extension}"

    except Exception as e:
        # Logujemy, jeśli logger dostępny, w przeciwnym razie print
        try:
            logger.error(f"Błąd generowania nazwy pliku: {e}")
        except Exception:
            print(f"Błąd generowania nazwy pliku: {e}")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"processed_{timestamp}.png"

def get_file_size(file_path):
    """Zwraca rozmiar pliku w bajtach."""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0

def create_export_summary(exported_files, settings):
    """Tworzy podsumowanie eksportu."""
    summary = {
        'total_files': len(exported_files),
        'successful_exports': len([f for f in exported_files if f.get('export_url')]),
        'failed_exports': len([f for f in exported_files if not f.get('export_url')]),
        'export_type': settings.get('save_location', 'Lokalnie'),
        'timestamp': datetime.now().isoformat(),
        'total_size_mb': 0
    }
    
    # Oblicz całkowity rozmiar
    for file_data in exported_files:
        if 'original_path' in file_data:
            size = get_file_size(file_data['original_path'])
            summary['total_size_mb'] += size / (1024 * 1024)
    
    summary['total_size_mb'] = round(summary['total_size_mb'], 2)
    
    return summary

def generate_links_file(exported_files, settings):
    """Generuje plik z linkami do wyeksportowanych obrazów."""
    if not exported_files:
        return None
    
    output_dir = settings.get('output_directory', 'output')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Określ format pliku
    file_format = settings.get('links_format', 'csv').lower()
    
    if file_format == 'csv':
        return generate_csv_links(exported_files, output_dir, timestamp)
    elif file_format == 'xml':
        return generate_xml_links(exported_files, output_dir, timestamp)
    elif file_format == 'json':
        return generate_json_links(exported_files, output_dir, timestamp)
    else:
        return generate_txt_links(exported_files, output_dir, timestamp)

def generate_csv_links(exported_files, output_dir, timestamp):
    """Generuje plik CSV z linkami."""
    output_path = Path(output_dir) / f'exported_links_{timestamp}.csv'
    
    with open(output_path, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Original File', 'Export URL', 'Export Time'])
        
        for file_data in exported_files:
            writer.writerow([
                file_data.get('original_path', ''),
                file_data.get('export_url', ''),
                file_data.get('export_time', datetime.now().isoformat())
            ])
    
    return str(output_path)

def generate_xml_links(exported_files, output_dir, timestamp):
    """Generuje plik XML z linkami."""
    output_path = Path(output_dir) / f'exported_links_{timestamp}.xml'
    
    root = ET.Element('exported_images')
    root.set('generated', timestamp)
    root.set('count', str(len(exported_files)))
    
    for file_data in exported_files:
        image_elem = ET.SubElement(root, 'image')
        
        original_elem = ET.SubElement(image_elem, 'original_path')
        original_elem.text = file_data.get('original_path', '')
        
        url_elem = ET.SubElement(image_elem, 'export_url')
        url_elem.text = file_data.get('export_url', '')
        
        time_elem = ET.SubElement(image_elem, 'export_time')
        time_elem.text = file_data.get('export_time', datetime.now().isoformat())
    
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    
    return str(output_path)

def generate_json_links(exported_files, output_dir, timestamp):
    """Generuje plik JSON z linkami."""
    output_path = Path(output_dir) / f'exported_links_{timestamp}.json'
    
    data = {
        'generated': timestamp,
        'count': len(exported_files),
        'images': exported_files
    }
    
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    
    return str(output_path)

def generate_txt_links(exported_files, output_dir, timestamp):
    """Generuje prosty plik tekstowy z linkami."""
    output_path = Path(output_dir) / f'exported_links_{timestamp}.txt'
    
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(f"Exported Images Links - Generated: {timestamp}\n")
        file.write("=" * 50 + "\n\n")
        
        for i, file_data in enumerate(exported_files, 1):
            file.write(f"{i}. {file_data.get('original_path', 'Unknown')}\n")
            file.write(f"   URL: {file_data.get('export_url', 'N/A')}\n")
            file.write(f"   Time: {file_data.get('export_time', 'N/A')}\n\n")
    
    return str(output_path)

if __name__ == "__main__":
    # Przykład użycia
    from PIL import Image
    
    # Przykładowe ustawienia
    settings = {
        'save_location': 'Lokalnie',
        'output_directory': 'output',
        'format': {'type': 'PNG', 'quality': 85},
        'filename_pattern': '{original_name}_{timestamp}'
    }
    
    # Przykładowy eksport
    try:
        # Otwórz przykładowy obraz
        with Image.open("example.png") as img:
            # Eksportuj
            result = export_image(img, "example.png", settings)
            if result:
                print(f"Wyeksportowano do: {result}")
            else:
                print("Błąd eksportu")
    except Exception as e:
        print(f"Błąd: {e}")
