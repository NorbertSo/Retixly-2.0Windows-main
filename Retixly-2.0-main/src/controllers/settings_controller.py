from PyQt6.QtCore import QSettings, QObject, pyqtSignal
import json
import os

class SettingsController(QObject):
    settings_changed = pyqtSignal(str, object)  # sekcja, nowa_wartość
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings('RetixlySoft', 'Retixly')
        self.load_defaults()
        
    def load_defaults(self):
        """Ładuje domyślne ustawienia, jeśli nie istnieją."""
        defaults = {
            'general': {
                'language': 'en',
                'theme': 'light',
                'auto_save': True,
                'check_updates': True
            },
            'processing': {
                'default_background': '#FFFFFF',
                'jpeg_quality': 85,
                'optimize_output': True,
                'preserve_metadata': False
            },
            'watermark': {
                'enabled': False,
                'path': '',
                'position': 'bottom-right',
                'opacity': 0.5,
                'scale': 0.2
            },
            'retouch': {
                'brightness': 1.0,
                'contrast': 1.0,
                'saturation': 1.0,
                'sharpness': 1.0
            },
            'export': {
                'default_format': 'PNG',
                'filename_pattern': '{original_name}_{size}',
                'default_path': os.path.expanduser('~/Pictures/Retixly')
            },
            'marketplace': {
                'default': 'Amazon',
                'auto_resize': True,
                'naming_convention': True
            },
            'cloud': {
                'gdrive_credentials': '',
                's3_credentials': '',
                'ftp_settings': '',
                'imgbb_key': ''
            }
        }
        
        # Sprawdzenie i ustawienie domyślnych wartości
        for section, values in defaults.items():
            if not self.settings.contains(f'{section}/initialized'):
                for key, value in values.items():
                    self.set_value(section, key, value)
                self.settings.setValue(f'{section}/initialized', True)
                
    def get_value(self, section, key, default=None):
        """Pobiera wartość ustawienia."""
        value = self.settings.value(f'{section}/{key}', default)
        
        # Konwersja typu dla wartości boolean i numerycznych
        if isinstance(default, bool):
            return str(value).lower() == 'true'
        elif isinstance(default, (int, float)):
            try:
                return type(default)(value)
            except (ValueError, TypeError):
                return default
        elif isinstance(default, dict):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return default
                
        return value
        
    def set_value(self, section, key, value):
        """Ustawia wartość ustawienia."""
        # Konwersja słowników do JSON
        if isinstance(value, dict):
            value = json.dumps(value)
            
        self.settings.setValue(f'{section}/{key}', value)
        self.settings_changed.emit(f'{section}/{key}', value)
        
    def get_section(self, section):
        """Pobiera wszystkie ustawienia z danej sekcji."""
        self.settings.beginGroup(section)
        values = {}
        for key in self.settings.childKeys():
            if key != 'initialized':
                values[key] = self.get_value(section, key)
        self.settings.endGroup()
        return values
        
    def reset_section(self, section):
        """Resetuje sekcję do wartości domyślnych."""
        self.settings.beginGroup(section)
        self.settings.remove('')
        self.settings.endGroup()
        self.load_defaults()
        
    def export_settings(self, file_path):
        """Eksportuje wszystkie ustawienia do pliku."""
        settings_dict = {}
        for section in self.settings.childGroups():
            settings_dict[section] = self.get_section(section)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, indent=4)
            
    def import_settings(self, file_path):
        """Importuje ustawienia z pliku."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                settings_dict = json.load(f)
                
            for section, values in settings_dict.items():
                for key, value in values.items():
                    self.set_value(section, key, value)
                    
            return True
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
            
    # Gettery i settery dla często używanych ustawień
    
    def get_language(self):
        """Pobiera aktualny język."""
        return self.get_value('general', 'language', 'en')
        
    def set_language(self, language):
        """Ustawia język aplikacji."""
        self.set_value('general', 'language', language)
        
    def get_theme(self):
        """Pobiera aktualny motyw."""
        return self.get_value('general', 'theme', 'light')
        
    def set_theme(self, theme):
        """Ustawia motyw aplikacji."""
        self.set_value('general', 'theme', theme)
        
    def get_watermark_settings(self):
        """Pobiera ustawienia znaku wodnego."""
        return self.get_section('watermark')
        
    def get_retouch_settings(self):
        """Pobiera ustawienia retuszu."""
        return self.get_section('retouch')
        
    def get_export_settings(self):
        """Pobiera ustawienia eksportu."""
        return self.get_section('export')
        
    def get_marketplace_settings(self):
        """Pobiera ustawienia marketplace."""
        return self.get_section('marketplace')
