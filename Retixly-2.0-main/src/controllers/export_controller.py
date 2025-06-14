from PyQt6.QtCore import QObject, pyqtSignal
import os
import csv
import xml.etree.ElementTree as ET
from datetime import datetime
import boto3
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from ftplib import FTP
import requests
from PIL import Image

class ExportController(QObject):
    export_progress = pyqtSignal(int, str)
    export_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, settings_controller):
        super().__init__()
        self.settings = settings_controller
        
    def get_gdrive_credentials(self):
        """Zwraca ważne poświadczenia Google Drive lub podnosi wyjątek, gdy wymagane jest logowanie OAuth2."""
        try:
            credentials_path = os.path.join(
                os.path.expanduser('~'),
                '.image_processor',
                'gdrive_credentials.json'
            )

            if os.path.exists(credentials_path):
                credentials = Credentials.from_authorized_user_file(credentials_path)
                if credentials and credentials.valid:
                    return credentials

            # Jeśli plik nie istnieje albo token wygasł
            raise Exception("Google Drive authentication required. Please configure OAuth2 credentials.")
        except Exception as e:
            raise Exception(f"Google Drive authentication failed: {str(e)}")
            
    def export_images(self, images, export_settings):
        """Eksportuje przetworzone obrazy zgodnie z ustawieniami."""
        try:
            export_type = export_settings['type']
            total_images = len(images)
            
            for i, image_data in enumerate(images, 1):
                progress = (i / total_images) * 100
                self.export_progress.emit(
                    progress,
                    self.tr(f"Exporting image {i} of {total_images}...")
                )
                
                if export_type == self.tr("Local Folder"):
                    self.export_local(image_data, export_settings)
                elif export_type == "Google Drive":
                    self.export_gdrive(image_data, export_settings)
                elif export_type == "Amazon S3":
                    self.export_s3(image_data, export_settings)
                elif export_type == "FTP":
                    self.export_ftp(image_data, export_settings)
                elif export_type == "imgBB":
                    self.export_imgbb(image_data, export_settings)
                    
            # Generowanie pliku z linkami
            if export_settings['generate_links'] != self.tr("Don't generate links file"):
                self.generate_links_file(images, export_settings)
                
            self.export_complete.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            
    def export_local(self, image_data, settings):
        """Eksport do lokalnego folderu."""
        output_path = os.path.join(
            settings['path'],
            self.generate_filename(image_data, settings)
        )
        image_data['image'].save(output_path)
        image_data['export_path'] = output_path
        
    def export_gdrive(self, image_data, settings):
        """Eksport do Google Drive."""
        try:
            credentials = self.get_gdrive_credentials()
            service = build('drive', 'v3', credentials=credentials)
            
            # Przygotowanie pliku
            file_metadata = {
                'name': self.generate_filename(image_data, settings),
                'parents': [settings['folder_id']]
            }
            
            # Tymczasowy zapis pliku
            temp_path = os.path.join(
                os.path.dirname(image_data['original_path']),
                'temp_' + os.path.basename(image_data['original_path'])
            )
            image_data['image'].save(temp_path)
            
            # Upload do Google Drive
            media = MediaFileUpload(temp_path, resumable=True)
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            # Zapisanie linku
            image_data['export_path'] = file.get('webViewLink')
            
            # Usunięcie pliku tymczasowego
            os.remove(temp_path)
            
        except Exception as e:
            raise Exception(f"Google Drive export failed: {str(e)}")
            
    def export_s3(self, image_data, settings):
        """Eksport do Amazon S3."""
        try:
            # Walidacja wymaganych parametrów
            required_params = ['key_id', 'secret', 'bucket', 'region']
            missing_params = [param for param in required_params if not settings.get(param)]
            if missing_params:
                raise Exception(f"Missing S3 parameters: {', '.join(missing_params)}")

            s3 = boto3.client(
                's3',
                aws_access_key_id=settings['key_id'],
                aws_secret_access_key=settings['secret'],
                region_name=settings['region']
            )
            
            # Test połączenia z bucketem
            s3.head_bucket(Bucket=settings['bucket'])
            
            # Przygotowanie pliku
            filename = self.generate_filename(image_data, settings)
            temp_path = os.path.join(
                os.path.dirname(image_data['original_path']),
                'temp_' + filename
            )
            image_data['image'].save(temp_path)
            
            # Upload do S3
            s3.upload_file(
                temp_path,
                settings['bucket'],
                filename
            )
            
            # Generowanie URL
            url = f"https://{settings['bucket']}.s3.amazonaws.com/{filename}"
            image_data['export_path'] = url
            
            # Usunięcie pliku tymczasowego
            os.remove(temp_path)
            
        except Exception as e:
            raise Exception(f"S3 export failed: {str(e)}")
            
    def export_ftp(self, image_data, settings):
        """Eksport przez FTP."""
        try:
            use_sftp = settings.get('use_sftp', False)

            if use_sftp:
                import paramiko
                transport = paramiko.Transport((settings['host'], settings.get('port', 22)))
                transport.connect(username=settings['user'], password=settings['password'])
                sftp = paramiko.SFTPClient.from_transport(transport)
                # Przejście do docelowego katalogu
                if settings['path']:
                    try:
                        sftp.chdir(settings['path'])
                    except IOError:
                        sftp.mkdir(settings['path'])
                        sftp.chdir(settings['path'])

                filename = self.generate_filename(image_data, settings)
                temp_path = os.path.join(
                    os.path.dirname(image_data['original_path']),
                    'temp_' + filename
                )
                image_data['image'].save(temp_path)
                sftp.put(temp_path, filename)
                url = f"sftp://{settings['host']}/{settings['path']}/{filename}"
                image_data['export_path'] = url
                sftp.close()
                transport.close()
            else:
                ftp = FTP(settings['host'])
                ftp.login(settings['user'], settings['password'])
                if settings['path']:
                    ftp.cwd(settings['path'])
                filename = self.generate_filename(image_data, settings)
                
                temp_path = os.path.join(
                    os.path.dirname(image_data['original_path']),
                    'temp_' + filename
                )
                image_data['image'].save(temp_path)
                
                # Upload pliku
                with open(temp_path, 'rb') as file:
                    ftp.storbinary(f'STOR {filename}', file)
                    
                # Generowanie URL
                url = f"ftp://{settings['host']}/{settings['path']}/{filename}"
                image_data['export_path'] = url
                
                # Zamknięcie połączenia i usunięcie pliku tymczasowego
                ftp.quit()
                os.remove(temp_path)
            
        except Exception as e:
            raise Exception(f"FTP export failed: {str(e)}")
            
    def export_imgbb(self, image_data, settings):
        """Eksport obrazu do ImgBB z obsługą formatu, jakości i ulepszonym logowaniem odpowiedzi."""
        try:
            # Ustawienia formatu i jakości
            format_type = settings.get('format', {}).get('type', 'JPEG')
            quality = settings.get('format', {}).get('quality', 85)

            # Nazwa tymczasowa
            temp_path = os.path.join(
                os.path.dirname(image_data['original_path']),
                f'temp_{os.path.splitext(os.path.basename(image_data["original_path"]))[0]}.{format_type.lower()}'
            )

            # Konwersja, jeśli JPEG i obraz ma kanał alfa lub tryb P
            if format_type.upper() == 'JPEG' and image_data['image'].mode in ('RGBA', 'P'):
                rgb_image = Image.new('RGB', image_data['image'].size, (255, 255, 255))
                if image_data['image'].mode == 'RGBA':
                    rgb_image.paste(image_data['image'], mask=image_data['image'].split()[-1])
                else:
                    rgb_image.paste(image_data['image'])
                rgb_image.save(temp_path, format=format_type, quality=quality, optimize=True)
            else:
                save_kwargs = {'format': format_type}
                if format_type.upper() == 'JPEG':
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                image_data['image'].save(temp_path, **save_kwargs)

            # Upload do ImgBB
            with open(temp_path, 'rb') as file:
                response = requests.post(
                    'https://api.imgbb.com/1/upload',
                    params={'key': settings['api_key']},
                    files={'image': file},
                    timeout=30
                )

            # Walidacja HTTP
            response.raise_for_status()
            response_data = response.json()

            if response_data.get('success') and 'data' in response_data:
                image_data['export_path'] = response_data['data']['url']
                # Dodatkowe informacje przydatne w debugowaniu lub późniejszej obsłudze
                image_data['delete_url'] = response_data['data'].get('delete_url')
                image_data['imgbb_id'] = response_data['data'].get('id')
            else:
                error_msg = response_data.get('error', {}).get('message', 'Unknown error')
                raise Exception(f"ImgBB upload failed: {error_msg}")

            # Usunięcie pliku tymczasowego
            os.remove(temp_path)

        except Exception as e:
            # Upewnij się, że tymczasowy plik nie pozostanie
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"imgBB export failed: {str(e)}")
            
    def generate_links_file(self, images, settings):
        """Generuje plik CSV lub XML z linkami do wyeksportowanych obrazów."""
        output_format = settings['generate_links']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if output_format == "Generate CSV":
            self.generate_csv(images, settings, timestamp)
        else:  # XML
            self.generate_xml(images, settings, timestamp)
            
    def generate_csv(self, images, settings, timestamp):
        """Generuje plik CSV z linkami."""
        output_path = os.path.join(
            settings['path'],
            f'image_links_{timestamp}.csv'
        )
        
        with open(output_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Original Name', 'Export URL'])
            
            for image_data in images:
                writer.writerow([
                    os.path.basename(image_data['original_path']),
                    image_data['export_path']
                ])
                
    def generate_xml(self, images, settings, timestamp):
        """Generuje plik XML z linkami."""
        root = ET.Element('images')
        root.set('generated', timestamp)
        
        for image_data in images:
            image_elem = ET.SubElement(root, 'image')
            
            name_elem = ET.SubElement(image_elem, 'original_name')
            name_elem.text = os.path.basename(image_data['original_path'])
            
            url_elem = ET.SubElement(image_elem, 'export_url')
            url_elem.text = image_data['export_path']
            
        tree = ET.ElementTree(root)
        output_path = os.path.join(
            settings['path'],
            f'image_links_{timestamp}.xml'
        )
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        
    def generate_filename(self, image_data, settings):
        """Generuje nazwę pliku według wzorca."""
        pattern = settings['filename_pattern']
        original_name = os.path.splitext(
            os.path.basename(image_data['original_path'])
        )[0]
        
        # Zastąpienie znaczników w wzorcu
        filename = pattern.replace('{original_name}', original_name)
        filename = filename.replace(
            '{timestamp}',
            datetime.now().strftime('%Y%m%d_%H%M%S')
        )
        filename = filename.replace(
            '{size}',
            f"{image_data['image'].width}x{image_data['image'].height}"
        )
        
        # Dodanie rozszerzenia
        return filename + '.' + settings['format']['type'].lower()

    def generate_csv_with_product_mapping(self, images, settings, csv_mapping):
        """Generuje plik CSV z Product ID i linkami do obrazów w chmurze."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(
            settings['path'],
            f'cloud_images_mapping_{timestamp}.csv'
        )

        with open(output_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Product_ID', 'Image_URL'])

            for image_data in images:
                original_filename = os.path.basename(image_data['original_path'])
                product_id = csv_mapping.get(original_filename, '')
                if image_data.get('export_path'):
                    writer.writerow([product_id, image_data['export_path']])
