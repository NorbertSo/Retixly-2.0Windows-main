"""
Auto-Update System for Retixly
Sprawdza aktualizacje z GitHub i umożliwia automatyczne aktualizacje
"""

import requests
import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
import logging
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import QThread, pyqtSignal, QTimer

logger = logging.getLogger(__name__)

class UpdateChecker(QThread):
    """Thread do sprawdzania aktualizacji w tle"""
    update_available = pyqtSignal(dict)
    no_update = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, current_version="1.0.0"):
        super().__init__()
        self.current_version = current_version
        # ZMIEŃ NA SWÓJ LINK DO GITHUB
        self.update_url = "https://raw.githubusercontent.com/NorbertSo/retixly-releases/main/version.json"
    
    def run(self):
        """Sprawdza dostępność aktualizacji"""
        try:
            logger.info(f"Sprawdzanie aktualizacji z: {self.update_url}")
            response = requests.get(self.update_url, timeout=10)
            response.raise_for_status()
            
            update_info = response.json()
            logger.info(f"Aktualna wersja: {self.current_version}, Dostępna: {update_info.get('version', 'unknown')}")
            
            if self.is_newer_version(update_info["version"], self.current_version):
                logger.info("Dostępna nowa wersja!")
                self.update_available.emit(update_info)
            else:
                logger.info("Brak nowych aktualizacji")
                self.no_update.emit()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Błąd sieci podczas sprawdzania aktualizacji: {e}")
            self.error_occurred.emit(f"Błąd połączenia: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Błąd parsowania JSON: {e}")
            self.error_occurred.emit(f"Błąd danych aktualizacji: {str(e)}")
        except Exception as e:
            logger.error(f"Nieznany błąd sprawdzania aktualizacji: {e}")
            self.error_occurred.emit(str(e))
    
    def is_newer_version(self, remote_version, local_version):
        """
        Porównuje wersje w formacie X.Y.Z
        Zwraca True jeśli remote_version jest nowszy niż local_version
        """
        try:
            remote_parts = [int(x) for x in remote_version.split('.')]
            local_parts = [int(x) for x in local_version.split('.')]
            
            # Wyrównaj długość list
            max_len = max(len(remote_parts), len(local_parts))
            remote_parts.extend([0] * (max_len - len(remote_parts)))
            local_parts.extend([0] * (max_len - len(local_parts)))
            
            return remote_parts > local_parts
        except (ValueError, AttributeError) as e:
            logger.error(f"Błąd porównywania wersji: {e}")
            return False

class AutoUpdater:
    """System automatycznych aktualizacji"""
    
    def __init__(self, parent_window, current_version="1.0.0"):
        self.parent = parent_window
        self.current_version = current_version
        self.checker = UpdateChecker(current_version)
        self.silent_check = True
        
        # Połącz sygnały
        self.checker.update_available.connect(self.show_update_dialog)
        self.checker.no_update.connect(self.no_update_available)
        self.checker.error_occurred.connect(self.handle_error)
        
        # Timer do sprawdzania aktualizacji co godzinę
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.check_for_updates(silent=True))
        self.timer.start(3600000)  # 1 godzina = 3600000 ms
        
        logger.info("Auto-updater zainicjalizowany")
    
    def check_for_updates(self, silent=True):
        """
        Sprawdź aktualizacje
        silent=True - nie pokazuj komunikatów jeśli brak aktualizacji
        """
        self.silent_check = silent
        if not self.checker.isRunning():
            logger.info(f"Rozpoczynam sprawdzanie aktualizacji (silent={silent})")
            self.checker.start()
        else:
            logger.info("Sprawdzanie aktualizacji już w toku")
    
    def show_update_dialog(self, update_info):
        """Pokaż dialog o dostępnej aktualizacji"""
        try:
            version = update_info.get('version', 'Nieznana')
            changelog = update_info.get('changelog', 'Brak informacji o zmianach')
            required = update_info.get('required', False)
            
            msg = QMessageBox(self.parent)
            msg.setWindowTitle("Dostępna aktualizacja Retixly")
            msg.setIcon(QMessageBox.Icon.Information)
            
            if required:
                msg.setText(f"⚠️ WYMAGANA aktualizacja do wersji {version}")
                msg.setInformativeText(f"Ta aktualizacja jest obowiązkowa.\n\nZmiany:\n{changelog}")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.setDefaultButton(QMessageBox.StandardButton.Ok)
            else:
                msg.setText(f"🎉 Dostępna nowa wersja: {version}")
                msg.setInformativeText(f"Czy chcesz zaktualizować teraz?\n\nZmiany:\n{changelog}")
                msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Later)
                msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            
            result = msg.exec()
            
            if result == QMessageBox.StandardButton.Yes or result == QMessageBox.StandardButton.Ok:
                self.download_and_install_update(update_info)
                
        except Exception as e:
            logger.error(f"Błąd wyświetlania dialogu aktualizacji: {e}")
    
    def download_and_install_update(self, update_info):
        """Pobierz i zainstaluj aktualizację"""
        try:
            download_url = update_info.get("download_url")
            if not download_url:
                raise ValueError("Brak URL do pobrania aktualizacji")
            
            # Otwieranie w przeglądarce (dla tej wersji)
            logger.info(f"Otwieranie URL pobierania: {download_url}")
            webbrowser.open(download_url)
            
            # Pokaż instrukcje użytkownikowi
            msg = QMessageBox(self.parent)
            msg.setWindowTitle("Pobieranie aktualizacji")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("🌐 Pobieranie aktualizacji rozpoczęte")
            msg.setInformativeText(
                "Strona pobierania została otwarta w przeglądarce.\n\n"
                "Kroki:\n"
                "1. Pobierz nowy instalator\n"
                "2. Uruchom pobrany plik\n"
                "3. Zamknij obecną aplikację\n"
                "4. Zainstaluj nową wersję"
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            
        except Exception as e:
            logger.error(f"Błąd podczas pobierania aktualizacji: {e}")
            self.show_error_message("Błąd aktualizacji", f"Nie udało się rozpocząć aktualizacji:\n{str(e)}")
    
    def no_update_available(self):
        """Obsługa braku dostępnych aktualizacji"""
        if not self.silent_check:
            msg = QMessageBox(self.parent)
            msg.setWindowTitle("Brak aktualizacji")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("✅ Masz najnowszą wersję Retixly!")
            msg.setInformativeText(f"Aktualna wersja: {self.current_version}")
            msg.exec()
        
        logger.info("Brak dostępnych aktualizacji")
    
    def handle_error(self, error_message):
        """Obsługa błędów sprawdzania aktualizacji"""
        logger.error(f"Błąd aktualizacji: {error_message}")
        
        if not self.silent_check:
            self.show_error_message("Błąd sprawdzania aktualizacji", error_message)
    
    def show_error_message(self, title, message):
        """Pokaż komunikat o błędzie"""
        try:
            msg = QMessageBox(self.parent)
            msg.setWindowTitle(title)
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText("⚠️ Wystąpił problem")
            msg.setInformativeText(message)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
        except Exception as e:
            logger.error(f"Błąd wyświetlania komunikatu błędu: {e}")
    
    def cleanup(self):
        """Czyści zasoby przed zamknięciem"""
        try:
            if self.timer.isActive():
                self.timer.stop()
            
            if self.checker.isRunning():
                self.checker.quit()
                self.checker.wait(3000)  # Czekaj maksymalnie 3 sekundy
            
            logger.info("Auto-updater oczyszczony")
        except Exception as e:
            logger.error(f"Błąd czyszczenia auto-updater: {e}")

# Funkcja pomocnicza dla łatwej integracji
def create_auto_updater(parent_window, version="1.0.0"):
    """
    Tworzy i zwraca instancję AutoUpdater
    """
    return AutoUpdater(parent_window, version)