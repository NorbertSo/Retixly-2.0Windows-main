from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent

class ImageView(QWidget):
    image_dropped = pyqtSignal(str)
    
    def __init__(self, placeholder_text="", parent=None):
        super().__init__(parent)
        self.init_ui(placeholder_text)
        
    def init_ui(self, placeholder_text):
        self.setAcceptDrops(True)
        layout = QVBoxLayout()
        
        # Label na obraz
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(300, 300)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #999;
                border-radius: 5px;
                background-color: #f0f0f0;
            }
        """)
        
        # Ustawienie tekstu placeholder
        self.image_label.setText(placeholder_text)
        
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if self.is_valid_image(file_path):
                self.load_image(file_path)
                self.image_dropped.emit(file_path)
                break
                
    def load_image(self, image_path):
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        
    def clear_image(self):
        self.image_label.clear()
        
    @staticmethod
    def is_valid_image(file_path):
        valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        return any(file_path.lower().endswith(ext) for ext in valid_extensions)
