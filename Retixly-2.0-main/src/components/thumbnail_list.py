from PyQt6.QtWidgets import (QListWidget, QListWidgetItem, QLabel, 
                           QWidget, QHBoxLayout, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon
from ..utils.image_utils import create_thumbnail
from ..utils.file_utils import get_supported_formats
import os

class ThumbnailItem(QWidget):
    remove_requested = pyqtSignal(QListWidgetItem)
    
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        
        # Miniatura
        thumbnail = create_thumbnail(self.file_path, (60, 60))
        thumbnail_label = QLabel()
        thumbnail_label.setPixmap(thumbnail)
        layout.addWidget(thumbnail_label)
        
        # Nazwa pliku
        filename = os.path.basename(self.file_path)
        name_label = QLabel(filename)
        name_label.setStyleSheet("padding-left: 5px;")
        layout.addWidget(name_label, 1)
        
        # Przycisk usuwania
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #666;
            }
            QPushButton:hover {
                color: #f00;
            }
        """)
        remove_btn.clicked.connect(self.request_removal)
        layout.addWidget(remove_btn)
        
        self.setLayout(layout)
        
    def request_removal(self):
        parent = self.parent()
        while parent and not isinstance(parent, QListWidget):
            parent = parent.parent()
        if parent:
            for i in range(parent.count()):
                if parent.itemWidget(parent.item(i)) == self:
                    self.remove_requested.emit(parent.item(i))
                    break

class ThumbnailList(QListWidget):
    files_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setUniformItemSizes(True)
        self.setSpacing(2)
        
        self.supported_formats = get_supported_formats()
        
    def add_files(self, files):
        for file_path in files:
            if self.is_supported_file(file_path):
                self.add_thumbnail(file_path)
        self.files_changed.emit()
        
    def add_folder(self, folder_path):
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                if self.is_supported_file(file_path):
                    self.add_thumbnail(file_path)
        self.files_changed.emit()
        
    def add_thumbnail(self, file_path):
        item = QListWidgetItem()
        thumbnail_widget = ThumbnailItem(file_path)
        thumbnail_widget.remove_requested.connect(self.remove_item)
        
        item.setSizeHint(thumbnail_widget.sizeHint())
        self.addItem(item)
        self.setItemWidget(item, thumbnail_widget)
        
    def remove_item(self, item):
        self.takeItem(self.row(item))
        self.files_changed.emit()
        
    def clear(self):
        super().clear()
        self.files_changed.emit()
        
    def get_files(self):
        files = []
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            files.append(widget.file_path)
        return files
        
    def is_supported_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()[1:]
        return ext in self.supported_formats
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                files.append(path)
            elif os.path.isdir(path):
                self.add_folder(path)
        self.add_files(files)
