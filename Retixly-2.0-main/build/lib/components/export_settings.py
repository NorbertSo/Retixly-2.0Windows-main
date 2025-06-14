from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                               QLabel, QLineEdit, QPushButton, QFileDialog,
                               QStackedWidget, QGroupBox, QMessageBox)
from PyQt6.QtCore import Qt
import os

class ExportSettings(QWidget):
    def __init__(self, settings_controller, parent=None):
        super().__init__(parent)
        self.settings = settings_controller
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Wybór typu eksportu
        export_type_layout = QHBoxLayout()
        export_type_layout.addWidget(QLabel(self.tr("Export to:")))
        
        self.export_type = QComboBox()
        self.export_type.addItems([
            self.tr("Local Folder"),
            "Google Drive",
            "Amazon S3",
            "FTP",
            "imgBB"
        ])
        self.export_type.currentIndexChanged.connect(self.show_export_settings)
        export_type_layout.addWidget(self.export_type)
        
        layout.addLayout(export_type_layout)
        
        # Stos widgetów z ustawieniami dla różnych typów eksportu
        self.settings_stack = QStackedWidget()
        self.settings_stack.addWidget(self.create_local_settings())
        self.settings_stack.addWidget(self.create_gdrive_settings())
        self.settings_stack.addWidget(self.create_s3_settings())
        self.settings_stack.addWidget(self.create_ftp_settings())
        self.settings_stack.addWidget(self.create_imgbb_settings())
        
        layout.addWidget(self.settings_stack)
        
        # Opcje eksportu
        options_group = QGroupBox(self.tr("Export Options"))
        options_layout = QVBoxLayout()
        
        # Format nazwy pliku
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(QLabel(self.tr("Filename pattern:")))
        self.filename_pattern = QLineEdit("{original_name}_{size}")
        filename_layout.addWidget(self.filename_pattern)
        options_layout.addLayout(filename_layout)
        
        # Format pliku CSV/XML
        self.generate_links = QComboBox()
        self.generate_links.addItems([
            self.tr("Don't generate links file"),
            "Generate CSV",
            "Generate XML"
        ])
        options_layout.addWidget(self.generate_links)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        self.setLayout(layout)
        
    def create_local_settings(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        self.local_path = QLineEdit()
        self.local_path.setPlaceholderText(self.tr("Select export folder..."))
        
        browse_btn = QPushButton(self.tr("Browse"))
        browse_btn.clicked.connect(self.browse_folder)
        
        path_layout.addWidget(self.local_path)
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        widget.setLayout(layout)
        return widget
        
    def create_gdrive_settings(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Folder ID
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Folder ID:"))
        self.gdrive_folder = QLineEdit()
        folder_layout.addWidget(self.gdrive_folder)
        
        # Przycisk autoryzacji
        auth_btn = QPushButton(self.tr("Authorize Google Drive"))
        auth_btn.clicked.connect(self.authorize_gdrive)
        
        layout.addLayout(folder_layout)
        layout.addWidget(auth_btn)
        widget.setLayout(layout)
        return widget
        
    def create_s3_settings(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Credentials
        layout.addWidget(QLabel("Access Key ID:"))
        self.s3_key_id = QLineEdit()
        layout.addWidget(self.s3_key_id)
        
        layout.addWidget(QLabel("Secret Access Key:"))
        self.s3_secret = QLineEdit()
        self.s3_secret.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.s3_secret)
        
        layout.addWidget(QLabel("Bucket:"))
        self.s3_bucket = QLineEdit()
        layout.addWidget(self.s3_bucket)
        
        # Test połączenia
        test_btn = QPushButton(self.tr("Test Connection"))
        test_btn.clicked.connect(self.test_s3_connection)
        layout.addWidget(test_btn)
        
        widget.setLayout(layout)
        return widget
        
    def create_ftp_settings(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Dane FTP
        layout.addWidget(QLabel("Host:"))
        self.ftp_host = QLineEdit()
        layout.addWidget(self.ftp_host)
        
        layout.addWidget(QLabel("Username:"))
        self.ftp_user = QLineEdit()
        layout.addWidget(self.ftp_user)
        
        layout.addWidget(QLabel("Password:"))
        self.ftp_pass = QLineEdit()
        self.ftp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.ftp_pass)
        
        layout.addWidget(QLabel("Path:"))
        self.ftp_path = QLineEdit()
        layout.addWidget(self.ftp_path)
        
        # Test połączenia
        test_btn = QPushButton(self.tr("Test Connection"))
        test_btn.clicked.connect(self.test_ftp_connection)
        layout.addWidget(test_btn)
        
        widget.setLayout(layout)
        return widget
        
    def create_imgbb_settings(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("API Key:"))
        self.imgbb_key = QLineEdit()
        layout.addWidget(self.imgbb_key)
        
        # Test klucza API
        test_btn = QPushButton(self.tr("Test API Key"))
        test_btn.clicked.connect(self.test_imgbb_key)
        layout.addWidget(test_btn)
        
        widget.setLayout(layout)
        return widget
        
    def show_export_settings(self, index):
        self.settings_stack.setCurrentIndex(index)
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Export Folder")
        )
        if folder:
            self.local_path.setText(folder)
            
    def authorize_gdrive(self):
        """Loads OAuth credentials JSON file and stores it in the user's
        configuration directory used by :class:`ExportController`."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select Google Drive credentials"),
            os.path.expanduser("~"),
            "JSON Files (*.json)"
        )

        if not file_path:
            return

        target_dir = os.path.join(os.path.expanduser("~"), ".image_processor")
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, "gdrive_credentials.json")

        try:
            import shutil

            shutil.copy(file_path, target_path)
            QMessageBox.information(
                self,
                self.tr("Google Drive"),
                self.tr("Credentials saved successfully.")
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                self.tr("Google Drive"),
                self.tr("Failed to save credentials: {error}").format(error=str(exc))
            )
        
    def test_s3_connection(self):
        """Tries to connect to Amazon S3 using provided credentials."""
        try:
            import boto3

            s3 = boto3.client(
                "s3",
                aws_access_key_id=self.s3_key_id.text(),
                aws_secret_access_key=self.s3_secret.text(),
            )
            s3.head_bucket(Bucket=self.s3_bucket.text())
            QMessageBox.information(
                self,
                "Amazon S3",
                self.tr("Connection successful.")
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Amazon S3",
                self.tr("Connection failed: {error}").format(error=str(exc))
            )
        
    def test_ftp_connection(self):
        """Checks connection to an FTP server using provided credentials."""
        try:
            from ftplib import FTP

            ftp = FTP(self.ftp_host.text())
            ftp.login(self.ftp_user.text(), self.ftp_pass.text())
            if self.ftp_path.text():
                ftp.cwd(self.ftp_path.text())
            ftp.quit()
            QMessageBox.information(
                self,
                "FTP",
                self.tr("Connection successful.")
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "FTP",
                self.tr("Connection failed: {error}").format(error=str(exc))
            )
        
    def test_imgbb_key(self):
        """Validates the imgBB API key by trying to upload a tiny image."""
        try:
            import io
            from PIL import Image
            import requests

            img = Image.new("RGB", (1, 1), color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)

            response = requests.post(
                "https://api.imgbb.com/1/upload",
                params={"key": self.imgbb_key.text()},
                files={"image": buf.getvalue()},
                timeout=15,
            )
            data = response.json()
            if response.status_code == 200 and data.get("success"):
                QMessageBox.information(
                    self,
                    "imgBB",
                    self.tr("API key is valid.")
                )
            else:
                error_msg = data.get("error", {}).get("message", "Unknown error")
                raise Exception(error_msg)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "imgBB",
                self.tr("API key test failed: {error}").format(error=str(exc))
            )
        
    def get_settings(self):
        export_type = self.export_type.currentText()
        settings = {
            'type': export_type,
            'filename_pattern': self.filename_pattern.text(),
            'generate_links': self.generate_links.currentText()
        }
        
        # Dodanie specyficznych ustawień dla wybranego typu eksportu
        if export_type == self.tr("Local Folder"):
            settings['path'] = self.local_path.text()
        elif export_type == "Google Drive":
            settings['folder_id'] = self.gdrive_folder.text()
        elif export_type == "Amazon S3":
            settings.update({
                'key_id': self.s3_key_id.text(),
                'secret': self.s3_secret.text(),
                'bucket': self.s3_bucket.text()
            })
        elif export_type == "FTP":
            settings.update({
                'host': self.ftp_host.text(),
                'user': self.ftp_user.text(),
                'password': self.ftp_pass.text(),
                'path': self.ftp_path.text()
            })
        elif export_type == "imgBB":
            settings['api_key'] = self.imgbb_key.text()
            
        return settings
