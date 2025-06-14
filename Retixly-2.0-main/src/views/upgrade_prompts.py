import webbrowser
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                            QLabel, QDialog, QFrame, QMessageBox, QScrollArea)
from PyQt6.QtWidgets import QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QPalette

from ..controllers.license_controller import get_license_controller
from ..models.subscription import SubscriptionPlan


class QuickUpgradeBar(QWidget):
    upgrade_requested = pyqtSignal()
    dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.license_controller = get_license_controller()
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #667eea, stop:1 #764ba2);
                border-bottom: 1px solid #5a67d8;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        icon_label = QLabel("⭐")
        icon_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                background: transparent;
            }
        """)
        layout.addWidget(icon_label)
        
        message_label = QLabel("Unlock Pro Features")
        message_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: 500;
                background: transparent;
            }
        """)
        layout.addWidget(message_label)
        
        layout.addStretch()
        
        upgrade_btn = QPushButton("Upgrade Now")
        upgrade_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 15px;
                padding: 8px 20px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        upgrade_btn.clicked.connect(self.upgrade_requested.emit)
        layout.addWidget(upgrade_btn)
        
        dismiss_btn = QPushButton("×")
        dismiss_btn.setFixedSize(30, 30)
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.7);
                border: none;
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
                color: white;
            }
        """)
        dismiss_btn.clicked.connect(self.dismiss)
        layout.addWidget(dismiss_btn)
        
        self.setLayout(layout)
        
    def dismiss(self):
        self.hide()
        self.dismissed.emit()


class UpgradeDialog(QDialog):
    plan_selected = pyqtSignal(SubscriptionPlan)

    def __init__(self, feature_name=None, parent=None):
        super().__init__(parent)
        self.feature_name = feature_name
        self.license_controller = get_license_controller()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Upgrade to Pro")
        self.setFixedSize(520, 680)  # Zwiększone rozmiary
        self.setModal(True)
        
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header = self.create_header()
        layout.addWidget(header)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: #f8f9fa;
            }
            QScrollBar:vertical {
                background: #f0f0f0;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(25)
        content_layout.setContentsMargins(25, 25, 25, 25)
        
        plans_section = self.create_plans_section()
        content_layout.addWidget(plans_section)
        
        # Dodanie funkcji Pro
        features_section = self.create_features_section()
        content_layout.addWidget(features_section)
        
        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        footer = self.create_footer()
        layout.addWidget(footer)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background: #f8f9fa;
            }
        """)
        
    def create_header(self):
        header = QFrame()
        header.setFixedHeight(150)
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #4a90e2, stop:1 #357abd);
                border-bottom: 1px solid #2d6da3;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("🚀 Unlock Pro Features")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: bold;
                background: transparent;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Get unlimited access to all professional features")
        subtitle.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 16px;
                background: transparent;
            }
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        header.setLayout(layout)
        return header
        
    def create_plans_section(self):
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background: white;
                border: none;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Choose your plan:")
        title.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 15px;
                background: transparent;
            }
        """)
        layout.addWidget(title)

        # Tworzenie planów bezpośrednio w layout
        yearly_plan = self.create_plan_card(
            "Pro Yearly",
            "$99.99",
            "per year",
            "Best value – Save $20 annually!",
            SubscriptionPlan.PRO_YEARLY,
            True
        )
        layout.addWidget(yearly_plan)

        monthly_plan = self.create_plan_card(
            "Pro Monthly",
            "$9.99",
            "per month",
            "Perfect for trying Pro features",
            SubscriptionPlan.PRO_MONTHLY,
            False
        )
        layout.addWidget(monthly_plan)

        section.setLayout(layout)
        return section
        
    def create_plan_card(self, name, price, period, description, plan, recommended=False):
        card = QFrame()
        card.setMinimumHeight(140)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Różne style dla recommended i zwykłej karty, bez border
        if recommended:
            card.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #e3f2fd, stop:1 #f8fbff);
                    border-radius: 12px;
                    margin: 5px;
                }
            """)
        else:
            card.setStyleSheet("""
                QFrame {
                    background: white;
                    border-radius: 12px;
                    margin: 5px;
                }
            """)

        # Main vertical layout for the card (to allow prominent label on top)
        card_main_layout = QVBoxLayout(card)
        card_main_layout.setContentsMargins(0, 0, 0, 0)
        card_main_layout.setSpacing(0)

        # Prominent top-left label for yearly plan
        if recommended:
            prominent_label = QLabel("📅 YEARLY PLAN")
            prominent_label.setStyleSheet("""
                QLabel {
                    background: none;
                    color: #2266cc;
                    font-size: 17px;
                    font-weight: bold;
                    letter-spacing: 2px;
                    text-transform: uppercase;
                    margin-left: 16px;
                    margin-top: 10px;
                }
            """)
            prominent_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            card_main_layout.addWidget(prominent_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Main horizontal layout for plan details and button
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(20)

        # Lewa strona - informacje o planie
        left_layout = QVBoxLayout()
        left_layout.setSpacing(8)

        # Badge dla recommended (keep if needed, or remove if redundant)
        if recommended:
            badge = QLabel("⭐ RECOMMENDED")
            badge.setStyleSheet("""
                QLabel {
                    background: #4a90e2;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: bold;
                    max-width: 120px;
                }
            """)
            badge.setAlignment(Qt.AlignmentFlag.AlignLeft)
            left_layout.addWidget(badge)

        # Nazwa planu
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 20px;
                font-weight: bold;
                background: transparent;
            }
        """)
        left_layout.addWidget(name_label)

        # Kontener na cenę i okres
        price_container = QHBoxLayout()
        price_container.setSpacing(8)

        price_label = QLabel(price)
        price_label.setStyleSheet("""
            QLabel {
                color: #4a90e2;
                font-size: 24px;
                font-weight: bold;
                background: transparent;
            }
        """)
        price_container.addWidget(price_label)

        period_label = QLabel(period)
        period_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 14px;
                background: transparent;
            }
        """)
        period_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
        price_container.addWidget(period_label)
        price_container.addStretch()

        left_layout.addLayout(price_container)

        # Opis
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            QLabel {
                color: #34495e;
                font-size: 13px;
                background: transparent;
                margin-top: 5px;
            }
        """)
        desc_label.setWordWrap(True)
        left_layout.addWidget(desc_label)

        left_layout.addStretch()
        main_layout.addLayout(left_layout)

        # Prawa strona - przycisk
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        select_btn = QPushButton("Select Plan")
        select_btn.setFixedSize(120, 40)

        if recommended:
            select_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4a90e2, stop:1 #357abd);
                    color: white;
                    border: none;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #357abd, stop:1 #2d6da3);
                }
                QPushButton:pressed {
                    background: #2d6da3;
                }
            """)
        else:
            select_btn.setStyleSheet("""
                QPushButton {
                    background: white;
                    color: #4a90e2;
                    border: 2px solid #4a90e2;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #f8fbff;
                    border-color: #357abd;
                }
                QPushButton:pressed {
                    background: #e3f2fd;
                }
            """)

        select_btn.clicked.connect(lambda: self.select_plan(plan))
        right_layout.addWidget(select_btn)

        main_layout.addLayout(right_layout)
        card_main_layout.addLayout(main_layout)
        return card

    def create_features_section(self):
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("✨ What you get with Pro:")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(title)
        
        features = [
            "🚀 Unlimited batch processing",
            "📊 CSV & XML import/export",
            "⚡ Advanced export options",
            "🎯 Priority support",
            "🔄 Automatic updates"
        ]
        
        for feature in features:
            feature_label = QLabel(feature)
            feature_label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    color: #34495e;
                    padding: 5px 0;
                    background: transparent;
                }
            """)
            layout.addWidget(feature_label)
        
        section.setLayout(layout)
        return section
        
    def create_footer(self):
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet("""
            QFrame {
                background: #f5f5f5;
                border-top: 1px solid #e0e0e0;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(30, 15, 30, 15)
        
        guarantee_label = QLabel("🏆 30-day money-back guarantee")
        guarantee_label.setStyleSheet("""
            QLabel {
                color: #28a745;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        layout.addWidget(guarantee_label)
        
        layout.addStretch()
        
        cancel_btn = QPushButton("Continue Shopping")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #666666;
                border: none;
                font-size: 14px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                color: #333333;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        footer.setLayout(layout)
        return footer
        
    def select_plan(self, plan):
        try:
            print(f"🔍 DEBUG: Selecting plan: {plan}")
            
            from ..controllers.subscription_controller import get_subscription_controller
            controller = get_subscription_controller()
            
            checkout_url = controller.create_checkout_url(plan)
            
            if checkout_url:
                print(f"✅ Checkout URL created: {checkout_url}")
                
                reply = QMessageBox.question(
                    self,
                    "Open Checkout",
                    f"Open checkout page for {plan.value.replace('_', ' ').title()}?\n\n"
                    f"This will open your browser to complete the payment.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    webbrowser.open(checkout_url)
                    
                    QMessageBox.information(
                        self,
                        "Checkout Opened",
                        "The checkout page has been opened in your browser.\n\n"
                        "Complete the payment to activate your Pro subscription.\n"
                        "You can close this dialog now."
                    )
                    
                    self.accept()
                
            else:
                print("❌ No checkout URL returned")
                QMessageBox.critical(
                    self,
                    "Error",
                    "Could not generate checkout link.\n\n"
                    "Please check your internet connection and try again."
                )
                
        except Exception as e:
            print(f"❌ Error in select_plan: {e}")
            import traceback
            traceback.print_exc()
            
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while creating checkout:\n{str(e)}\n\n"
                "Please try again or contact support."
            )


def should_show_upgrade_bar():
    try:
        license_controller = get_license_controller()
        return license_controller.is_free_user
    except:
        return False


def show_upgrade_prompt(feature_name=None, parent=None):
    try:
        dialog = UpgradeDialog(feature_name, parent)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
    except Exception as e:
        print(f"❌ Error showing upgrade prompt: {e}")
        import traceback
        traceback.print_exc()
        
        QMessageBox.information(
            parent,
            "Upgrade Required",
            f"This feature ({feature_name or 'Pro Feature'}) requires Retixly Pro.\n\n"
            "Please upgrade to unlock all professional features!"
        )
        return False


def show_feature_locked_message(feature_name, parent=None):
    QMessageBox.information(
        parent,
        "Pro Feature",
        f"{feature_name} is available in Retixly Pro.\n\n"
        "Upgrade to unlock batch processing, CSV/XML import, "
        "and advanced export options!"
    )
