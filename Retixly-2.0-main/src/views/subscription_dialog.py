from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFrame, QWidget, QMessageBox, QGroupBox,
                            QFormLayout, QProgressBar, QTextEdit, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont, QPixmap, QPalette
import webbrowser
import logging

from ..controllers.license_controller import get_license_controller
from ..controllers.subscription_controller import get_subscription_controller
from ..models.subscription import SubscriptionPlan, SubscriptionStatus

logger = logging.getLogger(__name__)

class SubscriptionInfoWidget(QFrame):
    """Widget wyświetlający informacje o aktualnej subskrypcji."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.license_controller = get_license_controller()
        self.init_ui()
        self.update_info()
        
    def init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e9ecef;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Header z planem
        header_layout = QHBoxLayout()
        
        self.plan_icon = QLabel("⭐")
        self.plan_icon.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(self.plan_icon)
        
        self.plan_name = QLabel("Retixly Free")
        self.plan_name.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 700;
                color: #212529;
            }
        """)
        header_layout.addWidget(self.plan_name)
        
        header_layout.addStretch()
        
        self.status_badge = QLabel("ACTIVE")
        self.status_badge.setStyleSheet("""
            QLabel {
                background: #28a745;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        header_layout.addWidget(self.status_badge)
        
        layout.addLayout(header_layout)
        
        # Informacje o subskrypcji
        self.info_layout = QFormLayout()
        self.info_layout.setSpacing(10)
        
        # Labels będą dodane dynamicznie
        self.expires_label = QLabel()
        self.next_billing_label = QLabel()
        self.price_label = QLabel()
        
        layout.addLayout(self.info_layout)
        
        # Progress bar dla czasu pozostałego (tylko dla Pro)
        self.time_progress = QProgressBar()
        self.time_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 5px;
            }
        """)
        self.time_progress.hide()
        layout.addWidget(self.time_progress)
        
        self.setLayout(layout)
        
    def update_info(self):
        """Aktualizuje informacje o subskrypcji."""
        try:
            # Wyczyść poprzednie informacje
            self.clear_info_layout()
            
            subscription_info = self.license_controller.get_subscription_info()
            plan = subscription_info['plan']
            status = subscription_info['status']
            
            # Aktualizuj header
            if plan == 'FREE':
                self.plan_icon.setText("🆓")
                self.plan_name.setText("Retixly Free")
                self.plan_name.setStyleSheet("""
                    QLabel {
                        font-size: 20px;
                        font-weight: 700;
                        color: #6c757d;
                    }
                """)
            else:
                self.plan_icon.setText("⭐")
                plan_display = "Retixly Pro (Monthly)" if plan == 'PRO_MONTHLY' else "Retixly Pro (Yearly)"
                self.plan_name.setText(plan_display)
                self.plan_name.setStyleSheet("""
                    QLabel {
                        font-size: 20px;
                        font-weight: 700;
                        color: #212529;
                    }
                """)
            
            # Aktualizuj status badge
            self.update_status_badge(status, subscription_info.get('in_grace_period', False))
            
            # Dodaj informacje specyficzne dla planu
            if plan != 'FREE':
                self.add_pro_info(subscription_info)
            else:
                self.add_free_info()
                
        except Exception as e:
            logger.error(f"Błąd aktualizacji info o subskrypcji: {e}")
            
    def clear_info_layout(self):
        """Czyści layout z informacjami."""
        while self.info_layout.count():
            child = self.info_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def update_status_badge(self, status: str, in_grace_period: bool):
        """Aktualizuje badge statusu."""
        if in_grace_period:
            self.status_badge.setText("GRACE PERIOD")
            self.status_badge.setStyleSheet("""
                QLabel {
                    background: #ffc107;
                    color: #212529;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        elif status == 'ACTIVE':
            self.status_badge.setText("ACTIVE")
            self.status_badge.setStyleSheet("""
                QLabel {
                    background: #28a745;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        elif status == 'CANCELLED':
            self.status_badge.setText("CANCELLED")
            self.status_badge.setStyleSheet("""
                QLabel {
                    background: #dc3545;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
        else:
            self.status_badge.setText(status)
            self.status_badge.setStyleSheet("""
                QLabel {
                    background: #6c757d;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 600;
                }
            """)
            
    def add_pro_info(self, subscription_info: dict):
        """Dodaje informacje dla użytkowników Pro."""
        # Data wygaśnięcia
        if subscription_info.get('expires_at'):
            expires_date = subscription_info['expires_at'][:10]  # YYYY-MM-DD
            expires_label = QLabel(expires_date)
            expires_label.setStyleSheet("font-weight: 500; color: #495057;")
            self.info_layout.addRow("Expires:", expires_label)
            
        # Dni do wygaśnięcia
        days_until_expiry = subscription_info.get('days_until_expiry')
        if days_until_expiry is not None:
            if days_until_expiry > 0:
                days_label = QLabel(f"{days_until_expiry} days")
                days_label.setStyleSheet("font-weight: 500; color: #495057;")
            else:
                days_label = QLabel("Expired")
                days_label.setStyleSheet("font-weight: 500; color: #dc3545;")
            self.info_layout.addRow("Time remaining:", days_label)
            
            # Progress bar dla czasu pozostałego
            if days_until_expiry > 0:
                total_days = 30 if subscription_info['plan'] == 'PRO_MONTHLY' else 365
                progress = max(0, (days_until_expiry / total_days) * 100)
                self.time_progress.setValue(int(progress))
                self.time_progress.show()
            else:
                self.time_progress.hide()
        
        # Grace period info
        if subscription_info.get('in_grace_period'):
            grace_days = subscription_info.get('grace_days_left', 0)
            grace_label = QLabel(f"{grace_days} days left")
            grace_label.setStyleSheet("font-weight: 500; color: #ffc107;")
            self.info_layout.addRow("Grace period:", grace_label)
            
    def add_free_info(self):
        """Dodaje informacje dla użytkowników Free."""
        features_label = QLabel("• Single photo processing\n• Basic export options")
        features_label.setStyleSheet("color: #6c757d; font-size: 13px;")
        self.info_layout.addRow("Features:", features_label)
        
        upgrade_note = QLabel("Upgrade to Pro for batch processing and advanced features!")
        upgrade_note.setStyleSheet("color: #007bff; font-style: italic; font-size: 12px;")
        self.info_layout.addRow("", upgrade_note)

class SubscriptionActionsWidget(QFrame):
    """Widget z akcjami zarządzania subskrypcją."""
    
    upgrade_requested = pyqtSignal(SubscriptionPlan)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.license_controller = get_license_controller()
        self.subscription_controller = get_subscription_controller()
        self.init_ui()
        self.update_actions()
        
    def init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        self.layout = QVBoxLayout()
        self.layout.setSpacing(12)
        self.setLayout(self.layout)
        
    def update_actions(self):
        """Aktualizuje dostępne akcje."""
        # Wyczyść poprzednie przyciski
        self.clear_layout()
        
        subscription_info = self.license_controller.get_subscription_info()
        plan = subscription_info['plan']
        status = subscription_info['status']
        
        if plan == 'FREE':
            self.add_upgrade_actions()
        else:
            self.add_pro_actions(status)
            
    def clear_layout(self):
        """Czyści layout."""
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
    def add_upgrade_actions(self):
        """Dodaje akcje upgrade dla użytkowników FREE."""
        title = QLabel("Upgrade to Pro")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #212529;
                margin-bottom: 10px;
            }
        """)
        self.layout.addWidget(title)
        
        # Monthly option
        monthly_frame = self.create_plan_option(
            "Pro Monthly",
            "$9.99/month",
            "Perfect for trying out Pro features",
            SubscriptionPlan.PRO_MONTHLY
        )
        self.layout.addWidget(monthly_frame)
        
        # Yearly option (recommended)
        yearly_frame = self.create_plan_option(
            "Pro Yearly",
            "$99.99/year",
            "Best value - Save $20 per year!",
            SubscriptionPlan.PRO_YEARLY,
            recommended=True
        )
        self.layout.addWidget(yearly_frame)
        
    def add_pro_actions(self, status: str):
        """Dodaje akcje dla użytkowników Pro."""
        title = QLabel("Manage Subscription")
        title.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #212529;
                margin-bottom: 10px;
            }
        """)
        self.layout.addWidget(title)
        
        # Customer Portal
        portal_btn = QPushButton("Manage Billing & Payment")
        portal_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        portal_btn.clicked.connect(self.open_customer_portal)
        self.layout.addWidget(portal_btn)
        
        # Cancel/Resume based on status
        if status == 'ACTIVE':
            cancel_btn = QPushButton("Cancel Subscription")
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #dc3545;
                    border: 2px solid #dc3545;
                    border-radius: 8px;
                    padding: 12px;
                    font-weight: 500;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #dc3545;
                    color: white;
                }
            """)
            cancel_btn.clicked.connect(self.cancel_subscription)
            self.layout.addWidget(cancel_btn)
            
        elif status == 'CANCELLED':
            resume_btn = QPushButton("Resume Subscription")
            resume_btn.setStyleSheet("""
                QPushButton {
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 12px;
                    font-weight: 500;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: #218838;
                }
            """)
            resume_btn.clicked.connect(self.resume_subscription)
            self.layout.addWidget(resume_btn)
        
    def create_plan_option(self, name: str, price: str, description: str, 
                          plan: SubscriptionPlan, recommended: bool = False):
        """Tworzy opcję planu."""
        frame = QFrame()
        style = """
            QFrame {
                background: white;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 15px;
            }
        """
        if recommended:
            style = """
                QFrame {
                    background: white;
                    border: 2px solid #007bff;
                    border-radius: 8px;
                    padding: 15px;
                }
            """
        frame.setStyleSheet(style)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #212529;")
        header_layout.addWidget(name_label)
        
        if recommended:
            rec_badge = QLabel("RECOMMENDED")
            rec_badge.setStyleSheet("""
                QLabel {
                    background: #007bff;
                    color: white;
                    padding: 2px 8px;
                    border-radius: 10px;
                    font-size: 10px;
                    font-weight: 600;
                }
            """)
            header_layout.addWidget(rec_badge)
            
        header_layout.addStretch()
        
        price_label = QLabel(price)
        price_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #007bff;")
        header_layout.addWidget(price_label)
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 12px; color: #6c757d;")
        layout.addWidget(desc_label)
        
        # Button
        select_btn = QPushButton("Select Plan")
        select_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #0056b3;
            }
        """)
        select_btn.clicked.connect(lambda: self.upgrade_clicked(plan))
        layout.addWidget(select_btn)
        
        frame.setLayout(layout)
        return frame
        
    def upgrade_clicked(self, plan: SubscriptionPlan):
        """Obsługuje kliknięcie upgrade."""
        self.upgrade_requested.emit(plan)
        
    def open_customer_portal(self):
        """Otwiera customer portal."""
        try:
            portal_url = self.subscription_controller.update_payment_method()
            if portal_url:
                webbrowser.open(portal_url)
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Could not open customer portal. Please try again later."
                )
        except Exception as e:
            logger.error(f"Błąd otwierania customer portal: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            
    def cancel_subscription(self):
        """Anuluje subskrypcję."""
        reply = QMessageBox.question(
            self,
            "Cancel Subscription",
            "Are you sure you want to cancel your subscription?\n\n"
            "You will continue to have access to Pro features until the end of your billing period.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.subscription_controller.cancel_subscription()
                if success:
                    QMessageBox.information(
                        self,
                        "Subscription Cancelled",
                        "Your subscription has been cancelled. You will continue to have access "
                        "to Pro features until the end of your billing period."
                    )
                    self.update_actions()
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        "Could not cancel subscription. Please try again later."
                    )
            except Exception as e:
                logger.error(f"Błąd anulowania subskrypcji: {e}")
                QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
                
    def resume_subscription(self):
        """Wznawia subskrypcję."""
        try:
            success = self.subscription_controller.resume_subscription()
            if success:
                QMessageBox.information(
                    self,
                    "Subscription Resumed",
                    "Your subscription has been resumed successfully!"
                )
                self.update_actions()
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    "Could not resume subscription. Please try again later."
                )
        except Exception as e:
            logger.error(f"Błąd wznawiania subskrypcji: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")

class SubscriptionDialog(QDialog):
    """Główny dialog zarządzania subskrypcją."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.license_controller = get_license_controller()
        self.subscription_controller = get_subscription_controller()
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        self.setWindowTitle("Subscription Management")
        self.setFixedSize(600, 700)
        self.setModal(True)
        
        # Główny layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Scroll area dla głównej zawartości
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(20)
        
        # Informacje o subskrypcji
        self.info_widget = SubscriptionInfoWidget()
        scroll_layout.addWidget(self.info_widget)
        
        # Akcje
        self.actions_widget = SubscriptionActionsWidget()
        scroll_layout.addWidget(self.actions_widget)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Footer z przyciskami
        footer = self.create_footer()
        layout.addWidget(footer)
        
        self.setLayout(layout)
        
        # Style dla całego dialogu
        self.setStyleSheet("""
            QDialog {
                background: #f8f9fa;
            }
        """)
        
    def create_header(self):
        """Tworzy header dialogu."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        
        layout = QHBoxLayout()
        
        # Ikona i tytuł
        content_layout = QVBoxLayout()
        
        title = QLabel("Subscription Management")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: 700;
                background: transparent;
            }
        """)
        content_layout.addWidget(title)
        
        subtitle = QLabel("Manage your Retixly Pro subscription")
        subtitle.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                background: transparent;
            }
        """)
        content_layout.addWidget(subtitle)
        
        layout.addLayout(content_layout)
        layout.addStretch()
        
        # Przycisk odświeżania
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(40, 40)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 20px;
                color: white;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.3);
            }
        """)
        refresh_btn.clicked.connect(self.refresh_subscription_info)
        layout.addWidget(refresh_btn)
        
        header.setLayout(layout)
        return header
        
    def create_footer(self):
        """Tworzy footer z przyciskami."""
        footer = QFrame()
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        
        # Help button
        help_btn = QPushButton("Need Help?")
        help_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6c757d;
                border: none;
                font-size: 12px;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #007bff;
            }
        """)
        help_btn.clicked.connect(self.show_help)
        layout.addWidget(help_btn)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        footer.setLayout(layout)
        return footer
        
    def connect_signals(self):
        """Podłącza sygnały."""
        self.actions_widget.upgrade_requested.connect(self.handle_upgrade_request)
        
        # Sygnały z kontrolera licencji
        self.license_controller.license_status_changed.connect(self.refresh_info)
        self.license_controller.subscription_updated.connect(self.refresh_info)
        
    def handle_upgrade_request(self, plan: SubscriptionPlan):
        """Obsługuje żądanie upgrade."""
        try:
            checkout_url = self.subscription_controller.create_checkout_url(plan)
            if checkout_url:
                webbrowser.open(checkout_url)
                QMessageBox.information(
                    self,
                    "Checkout Opened",
                    "The checkout page has been opened in your browser. "
                    "Complete the payment to activate your Pro subscription."
                )
                self.accept()  # Zamknij dialog
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Could not generate checkout link. Please try again later."
                )
        except Exception as e:
            logger.error(f"Błąd podczas upgrade: {e}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            
    def refresh_subscription_info(self):
        """Odświeża informacje o subskrypcji."""
        try:
            # Wymusz weryfikację online
            self.license_controller.force_online_verification()
            self.refresh_info()
            
            QMessageBox.information(
                self,
                "Refreshed",
                "Subscription information has been updated."
            )
        except Exception as e:
            logger.error(f"Błąd odświeżania: {e}")
            QMessageBox.warning(
                self,
                "Error",
                "Could not refresh subscription information. Please try again later."
            )
            
    def refresh_info(self):
        """Odświeża widgety z informacjami."""
        self.info_widget.update_info()
        self.actions_widget.update_actions()
        
    def show_help(self):
        """Pokazuje pomoc."""
        QMessageBox.information(
            self,
            "Help",
            "For subscription support, please contact us at:\n\n"
            "Email: support@retixly.com\n"
            "Website: https://retixly.com/support\n\n"
            "We typically respond within 24 hours."
        )