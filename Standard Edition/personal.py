import sys
import sqlite3
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QGroupBox,
    QInputDialog, QMessageBox, QDialog, QLineEdit, QTextEdit, QFormLayout, QDialogButtonBox, QTableWidget,
    QHeaderView, QTableWidgetItem, QListWidget, QListWidgetItem, QAbstractItemView, QSpinBox, QComboBox,
    QCalendarWidget, QDateTimeEdit, QTimeEdit, QGridLayout
)
from PySide6.QtGui import QIcon, QPalette, QColor, QDrag
from PySide6.QtCore import Qt, QDate, QDateTime, QTime, QMimeData, QSize
from reportlab.pdfgen import canvas
import webbrowser
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

APP_VERSION = "1.0.0a"

def resource_path(relative_path):
    """ Ermöglicht Zugriff auf Ressourcen im PyInstaller-Bundle und im Entwicklermodus """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

ICON_PATH = resource_path("icon.ico")

# Datenbankinitialisierung
def init_db():
    # Hauptdatenbank
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    
    # Einrichtungen
    c.execute('''CREATE TABLE IF NOT EXISTS einrichtungen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        adresse TEXT,
        telefon TEXT,
        status TEXT DEFAULT 'Frei',
        status_reason TEXT DEFAULT '',
        ansprechpartner1 TEXT,
        ansprechpartner1_tel TEXT,
        ansprechpartner1_email TEXT,
        ansprechpartner2 TEXT,
        ansprechpartner2_tel TEXT,
        ansprechpartner2_email TEXT
    )''')

    # Wohnbereiche
    c.execute('''CREATE TABLE IF NOT EXISTS wohnbereiche (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        einrichtung_id INTEGER,
        name TEXT,
        telefon TEXT,
        fax TEXT,
        FOREIGN KEY(einrichtung_id) REFERENCES einrichtungen(id)
    )''')

    # Disponenten
    c.execute('''CREATE TABLE IF NOT EXISTS disponenten (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vorname TEXT,
        nachname TEXT,
        buero TEXT,
        handy TEXT,
        email TEXT
    )''')

    # Dienste
    c.execute('''CREATE TABLE IF NOT EXISTS dienste (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        einrichtung_id INTEGER,
        beginn DATETIME,
        ende DATETIME,
        pause INTEGER,
        beschreibung TEXT,
        FOREIGN KEY(einrichtung_id) REFERENCES einrichtungen(id)
    )''')

    # Benutzer
    c.execute('''CREATE TABLE IF NOT EXISTS benutzer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        benutzername TEXT UNIQUE,
        passwort TEXT,
        vorname TEXT,
        nachname TEXT,
        rolle TEXT
    )''')

    # Admin-Benutzer anlegen
    c.execute("SELECT * FROM benutzer WHERE benutzername='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO benutzer VALUES (NULL,?,?,?,?,?)", 
                 ('admin', 'admin', 'Administrator', '', 'admin'))

    conn.commit()
    conn.close()

    # Lizenzdatenbank
    conn = sqlite3.connect("lizenz.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS lizenzen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        benutzer_id INTEGER UNIQUE,
        lizenzkey TEXT UNIQUE,
        FOREIGN KEY(benutzer_id) REFERENCES benutzer(id)
    )''')
    conn.commit()
    conn.close()

    # Dienstvorlagen
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dienstvorlagen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        beginn TEXT NOT NULL,
        ende TEXT NOT NULL,
        pause INTEGER DEFAULT 0,
        einrichtung_id INTEGER,
        FOREIGN KEY(einrichtung_id) REFERENCES einrichtungen(id)
    )''')
    conn.commit()
    conn.close()

    # Spalte 'einrichtung_id' zu 'dienstvorlagen' hinzufügen, falls nicht vorhanden
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE dienstvorlagen ADD COLUMN einrichtung_id INTEGER")
        conn.commit()
        print("Spalte 'einrichtung_id' wurde hinzugefügt.")
    except Exception as e:
        print("Fehler oder Spalte existiert schon:", e)
    conn.close()

class DatabaseManager:
    def __init__(self, db_path="app.db"):
        self.db_path = db_path

    def get_facility(self, facility_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM einrichtungen WHERE id=?", (facility_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_living_area(self, area_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM wohnbereiche WHERE id=?", (area_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_living_area(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO wohnbereiche (einrichtung_id, name, telefon, fax)
            VALUES (?, ?, ?, ?)
        """, (data['facility_id'], data['name'], data['phone'], data['fax']))
        conn.commit()
        conn.close()

    def update_living_area(self, area_id, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE wohnbereiche SET name=?, telefon=?, fax=?
            WHERE id=?
        """, (data['name'], data['phone'], data['fax'], area_id))
        conn.commit()
        conn.close()

    def delete_living_area(self, area_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM wohnbereiche WHERE id=?", (area_id,))
        conn.commit()
        conn.close()

    def get_dispatcher(self, dispatcher_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM disponenten WHERE id=?", (dispatcher_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_dispatcher(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO disponenten (vorname, nachname, buero, handy, email)
            VALUES (?, ?, ?, ?, ?)
        """, (data['firstname'], data['lastname'], data['office'], data['mobile'], data['email']))
        conn.commit()
        conn.close()

    def update_dispatcher(self, dispatcher_id, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE disponenten SET vorname=?, nachname=?, buero=?, handy=?, email=?
            WHERE id=?
        """, (data['firstname'], data['lastname'], data['office'], data['mobile'], data['email'], dispatcher_id))
        conn.commit()
        conn.close()

    def delete_dispatcher(self, dispatcher_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM disponenten WHERE id=?", (dispatcher_id,))
        conn.commit()
        conn.close()

    def get_all_dispatchers(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM disponenten")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_living_areas(self, facility_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM wohnbereiche WHERE einrichtung_id=?", (facility_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_services(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT dienste.*, einrichtungen.name as facility_name
            FROM dienste
            LEFT JOIN einrichtungen ON dienste.einrichtung_id = einrichtungen.id
        """)
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_services_for_date(self, date):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        date_str = date.toString("yyyy-MM-dd")
        c.execute("""
            SELECT dienste.*, einrichtungen.name as facility_name
            FROM dienste
            LEFT JOIN einrichtungen ON dienste.einrichtung_id = einrichtungen.id
            WHERE date(beginn) = ?
        """, (date_str,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_monthly_services(self, facility_id, year, month):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT dienste.*, einrichtungen.name as facility_name
            FROM dienste
            LEFT JOIN einrichtungen ON dienste.einrichtung_id = einrichtungen.id
            WHERE dienste.einrichtung_id = ? AND strftime('%Y', beginn) = ? AND strftime('%m', beginn) = ?
        """, (facility_id, str(year), f"{month:02d}"))
        rows = c.fetchall()
        conn.close()
        import datetime
        result = []
        for row in rows:
            row = dict(row)
            row['date'] = datetime.datetime.strptime(row['beginn'], "%Y-%m-%d %H:%M:%S")
            row['begin'] = datetime.datetime.strptime(row['beginn'], "%Y-%m-%d %H:%M:%S")
            row['end'] = datetime.datetime.strptime(row['ende'], "%Y-%m-%d %H:%M:%S")
            result.append(row)
        return result

    def get_all_facilities(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM einrichtungen")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_service(self, service_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM dienste WHERE id=?", (service_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def add_service(self, service_data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO dienste (einrichtung_id, beginn, ende, pause, beschreibung)
            VALUES (?, ?, ?, ?, ?)
        """, (service_data['einrichtung_id'], 
              service_data['beginn'],
              service_data['ende'],
              service_data['pause'],
              service_data['beschreibung']))
        conn.commit()
        conn.close()

    def update_service(self, service_id, service_data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE dienste 
            SET einrichtung_id=?, beginn=?, ende=?, pause=?, beschreibung=?
            WHERE id=?
        """, (service_data['einrichtung_id'],
              service_data['beginn'],
              service_data['ende'],
              service_data['pause'],
              service_data['beschreibung'],
              service_id))
        conn.commit()
        conn.close()

    def delete_service(self, service_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM dienste WHERE id=?", (service_id,))
        conn.commit()
        conn.close()

    def add_facility(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO einrichtungen (name, adresse, telefon, status, status_reason, ansprechpartner1, ansprechpartner1_tel, ansprechpartner1_email, ansprechpartner2, ansprechpartner2_tel, ansprechpartner2_email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data['name'], data['adresse'], data['telefon'], data['status'], data['status_reason'], data['ansprechpartner1'], data['ansprechpartner1_tel'], data['ansprechpartner1_email'], data['ansprechpartner2'], data['ansprechpartner2_tel'], data['ansprechpartner2_email']))
        conn.commit()
        conn.close()

    def update_facility(self, facility_id, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            UPDATE einrichtungen SET name=?, adresse=?, telefon=?, status=?, status_reason=?, ansprechpartner1=?, ansprechpartner1_tel=?, ansprechpartner1_email=?, ansprechpartner2=?, ansprechpartner2_tel=?, ansprechpartner2_email=?
            WHERE id=?
        """, (data['name'], data['adresse'], data['telefon'], data['status'], data['status_reason'], data['ansprechpartner1'], data['ansprechpartner1_tel'], data['ansprechpartner1_email'], data['ansprechpartner2'], data['ansprechpartner2_tel'], data['ansprechpartner2_email'], facility_id))
        conn.commit()
        conn.close()

    def delete_facility(self, facility_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM einrichtungen WHERE id=?", (facility_id,))
        conn.commit()
        conn.close()

    def get_all_shift_templates(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM dienstvorlagen")
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def add_shift_template(self, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO dienstvorlagen (name, beginn, ende, pause, einrichtung_id) VALUES (?, ?, ?, ?, ?)",
                  (data['name'], data['beginn'], data['ende'], data['pause'], data['einrichtung_id']))
        conn.commit()
        conn.close()

    def update_shift_template(self, tpl_id, data):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE dienstvorlagen SET name=?, beginn=?, ende=?, pause=?, einrichtung_id=? WHERE id=?",
                  (data['name'], data['beginn'], data['ende'], data['pause'], data['einrichtung_id'], tpl_id))
        conn.commit()
        conn.close()

    def delete_shift_template(self, tpl_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM dienstvorlagen WHERE id=?", (tpl_id,))
        conn.commit()
        conn.close()

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        self.username = QLineEdit()
        self.username.setPlaceholderText("Benutzername")
        layout.addWidget(self.username)
        
        self.password = QLineEdit()
        self.password.setPlaceholderText("Passwort")
        self.password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password)
        
        self.login_button = QPushButton("Anmelden")
        self.login_button.clicked.connect(self.check_login)
        layout.addWidget(self.login_button)
        
        self.setLayout(layout)
        
    def check_login(self):
        conn = sqlite3.connect("app.db")
        c = conn.cursor()
        c.execute("SELECT * FROM benutzer WHERE benutzername=? AND passwort=?",
                 (self.username.text(), self.password.text()))
        user = c.fetchone()
        conn.close()
        
        if user:
            self.user_data = user
            self.accept()
        else:
            QMessageBox.warning(self, "Fehler", "Falscher Benutzername oder Passwort!")

class Dashboard(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.db = DatabaseManager()
        self.setWindowIcon(QIcon(ICON_PATH))
        self.init_ui()
        self.update_dashboard_info()

    def init_ui(self):
        self.setWindowTitle("Dienstplaner")
        self.setMinimumSize(900, 600)

        # Hauptlayout: Sidebar links, Inhalt rechts
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # Sidebar
        sidebar = QVBoxLayout()
        sidebar.setSpacing(10)
        sidebar.setAlignment(Qt.AlignTop)

        btn_dashboard = QPushButton("Dashboard")
        btn_dashboard.clicked.connect(self.update_dashboard_info)
        sidebar.addWidget(btn_dashboard)

        btn_new_service = QPushButton("Neuer Dienst")
        btn_new_service.clicked.connect(self.new_service)
        sidebar.addWidget(btn_new_service)

        btn_export = QPushButton("Dienste exportieren")
        btn_export.clicked.connect(self.export_services)
        sidebar.addWidget(btn_export)

        sidebar.addSpacing(20)
        sidebar.addWidget(QLabel("Verwaltung:"))

        btn_facility = QPushButton("Einrichtungen")
        btn_facility.clicked.connect(self.manage_facilities)
        sidebar.addWidget(btn_facility)

        btn_living_areas = QPushButton("Wohnbereiche")
        btn_living_areas.clicked.connect(self.manage_living_areas)
        sidebar.addWidget(btn_living_areas)

        btn_dispatcher = QPushButton("Disponenten")
        btn_dispatcher.clicked.connect(self.manage_dispatchers)
        sidebar.addWidget(btn_dispatcher)

        btn_services = QPushButton("Dienste")
        btn_services.clicked.connect(self.manage_services)
        sidebar.addWidget(btn_services)

        btn_shift_templates = QPushButton("Dienstvorlagen")
        btn_shift_templates.clicked.connect(self.manage_shift_templates)
        sidebar.addWidget(btn_shift_templates)

        sidebar.addSpacing(20)
        btn_user_settings = QPushButton("Benutzereinstellungen")
        btn_user_settings.clicked.connect(self.show_user_settings)
        sidebar.addWidget(btn_user_settings)

        sidebar.addStretch()
        btn_exit = QPushButton("Beenden")
        btn_exit.clicked.connect(self.close)
        sidebar.addWidget(btn_exit)

        # Sidebar-Widget
        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar)
        sidebar_widget.setFixedWidth(220)
        sidebar_widget.setStyleSheet("""
            QWidget {
                background: #18191c;
                border-radius: 16px;
                margin: 12px 0 12px 12px;
                box-shadow: 0 4px 24px #0008;
            }
        """)

        # Buttons mit Icons und Text
        def make_sidebar_button(text, icon_path, active=False):
            btn = QPushButton(f"  {text}")
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(22, 22))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumHeight(44)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {'#23272e' if active else 'transparent'};
                    color: {'#fff' if active else '#b0b3b8'};
                    border: 2px solid #444;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 18px;
                    font-size: 16px;
                    margin-bottom: 4px;
                }}
                QPushButton:hover {{
                    background: #23272e;
                    color: #fff;
                    border: 2px solid #888;
                }}
            """)
            return btn

        # Beispiel für die ersten Buttons (Icons müssen als PNG/SVG vorliegen)
        sidebar = QVBoxLayout()
        sidebar.setSpacing(6)
        sidebar.setAlignment(Qt.AlignTop)
        sidebar.addWidget(QLabel("<b style='color:#fff; font-size:18px; margin:12px;'>☰  Menu</b>"))

        btn_home = make_sidebar_button("Home", "icons/home.png", active=True)
        btn_messages = make_sidebar_button("Messages", "icons/messages.png")
        btn_integrations = make_sidebar_button("Integrations", "icons/integrations.png")
        btn_finance = make_sidebar_button("Finance", "icons/finance.png")
        btn_threads = make_sidebar_button("Threads", "icons/threads.png")
        btn_contacts = make_sidebar_button("Contacts", "icons/contacts.png")
        btn_explore = make_sidebar_button("Explore", "icons/explore.png")
        btn_settings = make_sidebar_button("Settings", "icons/settings.png")
        btn_help = make_sidebar_button("Help", "icons/help.png")

        for btn in [btn_home, btn_messages, btn_integrations, btn_finance, btn_threads, btn_contacts, btn_explore, btn_settings, btn_help]:
            sidebar.addWidget(btn)

        sidebar.addStretch()

        # Untere Buttons (z.B. Logout, Emoji)
        bottom_bar = QHBoxLayout()
        bottom_bar.addWidget(make_sidebar_button("", "icons/logout.png"))
        bottom_bar.addWidget(make_sidebar_button("", "icons/discord.png"))
        bottom_bar.addWidget(make_sidebar_button("", "icons/reddit.png"))
        sidebar.addLayout(bottom_bar)

        # Hauptinhalt (wie bisher)
        content_layout = QVBoxLayout()
        
        # Willkommensnachricht
        welcome = QLabel(f"Willkommen, {self.user_data[3]}!")  # Verwende den Vornamen
        welcome.setStyleSheet("font-size: 24px; margin: 20px;")
        content_layout.addWidget(welcome)
        
        # Widgets-Container
        widgets_container = QHBoxLayout()
        
        # Aktueller Dienst
        self.current_service = QGroupBox("Aktueller Dienst")
        current_service_layout = QVBoxLayout()
        self.current_service_label = QLabel("Kein aktiver Dienst")
        current_service_layout.addWidget(self.current_service_label)
        self.current_service.setLayout(current_service_layout)
        widgets_container.addWidget(self.current_service)
        
        # Aktuelle Einrichtung
        self.current_facility = QGroupBox("Aktuelle Einrichtung")
        current_facility_layout = QVBoxLayout()
        self.current_facility_label = QLabel("Keine Einrichtung ausgewählt")
        current_facility_layout.addWidget(self.current_facility_label)
        self.current_facility.setLayout(current_facility_layout)
        widgets_container.addWidget(self.current_facility)
        
        # Disponenten
        self.dispatcher_info = QGroupBox("Disponent")
        dispatcher_layout = QVBoxLayout()
        self.dispatcher_label = QLabel("Kein Disponent ausgewählt")
        dispatcher_layout.addWidget(self.dispatcher_label)
        self.dispatcher_info.setLayout(dispatcher_layout)
        widgets_container.addWidget(self.dispatcher_info)
        
        widgets_container.setSpacing(16)
        widgets_container.setStretch(0, 1)
        widgets_container.setStretch(1, 1)
        widgets_container.setStretch(2, 1)
        
        content_layout.addLayout(widgets_container)

        # Monatskalender-Ansicht direkt im Dashboard anzeigen
        self.month_calendar = DutyCalendarWidget(self)
        self.month_calendar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_layout.addWidget(self.month_calendar)

        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setAlignment(Qt.AlignRight)
        version_label.setStyleSheet("color: gray; padding: 5px;")
        content_layout.addWidget(version_label)

        # Layouts zusammenfügen
        main_layout.addWidget(sidebar_widget)
        main_layout.addLayout(content_layout)

    def update_dashboard_info(self):
        # Aktueller Dienst (nächster Dienst ab heute)
        import datetime
        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect("app.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT dienste.*, einrichtungen.name as facility_name, einrichtungen.adresse as facility_address
            FROM dienste
            LEFT JOIN einrichtungen ON dienste.einrichtung_id = einrichtungen.id
            WHERE beginn >= ?
            ORDER BY beginn ASC LIMIT 1
        """, (today,))
        dienst = c.fetchone()
        if dienst:
            beginn = dienst["beginn"][11:16]
            ende = dienst["ende"][11:16]
            beschreibung = dienst["beschreibung"]
            self.current_service_label.setText(f"{beschreibung} ({beginn} - {ende})")
            einrichtungsname = dienst["facility_name"] or "Keine Einrichtung"
            adresse = dienst["facility_address"] or ""
            self.current_facility_label.setText(f"{einrichtungsname}\n{adresse}")
        else:
            self.current_service_label.setText("Kein aktiver Dienst")
            self.current_facility_label.setText("Keine Einrichtung ausgewählt")

        # Disponent (ersten aus DB anzeigen)
        c.execute("SELECT * FROM disponenten LIMIT 1")
        disp = c.fetchone()
        if disp:
            self.dispatcher_label.setText(f"{disp['vorname']} {disp['nachname']} ({disp['handy']})")
        else:
            self.dispatcher_label.setText("Kein Disponent ausgewählt")
        conn.close()

    def new_service(self):
        dialog = ServicePlanningDialog(self)
        dialog.exec_()
        
    def export_services(self):
        # Nach Einrichtungsnamen fragen statt ID
        facilities = self.db.get_all_facilities()
        if not facilities:
            QMessageBox.warning(self, "Export", "Keine Einrichtungen vorhanden.")
            return
        items = [f"{f['name']} (ID: {f['id']})" for f in facilities]
        item, ok = QInputDialog.getItem(self, "Export", "Einrichtung auswählen:", items, 0, False)
        if ok and item:
            facility_id = int(item.split("ID:")[1].replace(")", "").strip())
            year, month, ok = self.get_year_month()
            if ok:
                exporter = ServiceExporter()
                filename = exporter.export_monthly_services(facility_id, year, month)
                QMessageBox.information(self, "Export erfolgreich",
                                     f"Dienste wurden exportiert nach:\n{filename}")

    def get_year_month(self):
        current_date = QDate.currentDate()
        year, ok = QInputDialog.getInt(self, "Jahr", "Jahr:", 
                                     current_date.year(), 2000, 2100)
        if ok:
            month, ok = QInputDialog.getInt(self, "Monat", "Monat:", 
                                          current_date.month(), 1, 12)
            return year, month, ok
        return None, None, False

    def manage_facilities(self):
        dialog = FacilityDialog(self)
        dialog.exec_()

    def manage_living_areas(self):
        # Dropdown mit allen Einrichtungen (Häusern) nach Name
        facilities = self.db.get_all_facilities()
        if not facilities:
            QMessageBox.warning(self, "Hinweis", "Es sind keine Einrichtungen vorhanden.")
            return
        items = [f"{f['name']} (ID: {f['id']})" for f in facilities]
        item, ok = QInputDialog.getItem(self, "Wohnbereich", "Einrichtung auswählen:", items, 0, False)
        if ok and item:
            # Extrahiere die ID aus dem ausgewählten Text
            facility_id = int(item.split("ID:")[1].replace(")", "").strip())
            dialog = LivingAreaDialog(facility_id, self)
            dialog.exec_()

    def manage_dispatchers(self):
        dialog = DispatcherDialog(self)
        dialog.exec_()

    def manage_services(self):
        dialog = ServicePlanningDialog(self)
        dialog.exec_()

    def manage_shift_templates(self):
        dialog = ShiftTemplateDialog(self)
        dialog.exec_()

    def show_user_settings(self):
        dialog = UserSettingsDialog(self.user_data[0], self)
        dialog.exec_()

class DutyCalendarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.current_year = QDate.currentDate().year()
        self.current_month = QDate.currentDate().month()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)

        # Monatsnavigation
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedWidth(32)
        self.prev_btn.clicked.connect(self.prev_month)
        self.header = QLabel()
        self.header.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        self.header.setAlignment(Qt.AlignCenter)
        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedWidth(32)
        self.next_btn.clicked.connect(self.next_month)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.header, 1)
        nav_layout.addWidget(self.next_btn)
        self.layout.addLayout(nav_layout)

        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        self.layout.addLayout(self.grid, 1)  # <--- wichtig: stretch für mitwachsen

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.draw_calendar()

    def prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.draw_calendar()

    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.draw_calendar()

    def draw_calendar(self):
        self.header.setText(QDate(self.current_year, self.current_month, 1).toString("MMMM yyyy"))
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        for col, day in enumerate(weekdays):
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; color: #aaa;")
            self.grid.addWidget(lbl, 0, col)
        first_day = QDate(self.current_year, self.current_month, 1)
        start_col = (first_day.dayOfWeek() + 6) % 7
        days_in_month = first_day.daysInMonth()
        row = 1
        col = start_col
        for day in range(1, days_in_month + 1):
            cell = QWidget()
            vbox = QVBoxLayout(cell)
            vbox.setContentsMargins(2, 2, 2, 2)
            day_lbl = QLabel(str(day))
            day_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            day_lbl.setStyleSheet("color: white; font-size: 12px;")
            vbox.addWidget(day_lbl)
            services = self.db.get_services_for_date(QDate(self.current_year, self.current_month, day))
            for service in services:
                beschreibung = service.get('beschreibung', '').strip()
                beginn = str(service['beginn'])
                label, color = get_shift_label_and_color(beginn, beschreibung)
                dienst_lbl = QLabel(label)
                dienst_lbl.setAlignment(Qt.AlignCenter)
                dienst_lbl.setStyleSheet(
                    f"background: {color}; color: white; border-radius: 6px; padding: 2px 6px; margin-top: 2px;"
                )
                vbox.addWidget(dienst_lbl)
            self.grid.addWidget(cell, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

        # Gesamtstunden berechnen und anzeigen
        services = []
        for day in range(1, days_in_month + 1):
            services += self.db.get_services_for_date(QDate(self.current_year, self.current_month, day))

        total_minutes = 0
        for service in services:
            try:
                beginn = datetime.strptime(service['beginn'], "%Y-%m-%d %H:%M:%S")
                ende = datetime.strptime(service['ende'], "%Y-%m-%d %H:%M:%S")
                pause = int(service.get('pause', 0))
                diff = (ende - beginn).total_seconds() / 60 - pause
                total_minutes += max(diff, 0)
            except Exception:
                pass

        total_hours = total_minutes // 60
        total_rest = int(total_minutes % 60)

        # Label am unteren Rand anzeigen
        if hasattr(self, "hours_label"):
            self.hours_label.setText(f"Gesamtstunden: {int(total_hours)} Std {total_rest} Min / 152 Std")
        else:
            self.hours_label = QLabel(f"Gesamtstunden: {int(total_hours)} Std {total_rest} Min / 152 Std")
            self.hours_label.setStyleSheet("font-size: 14px; color: #fff; margin-top: 10px;")
            self.layout.addWidget(self.hours_label)

class FacilityDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.setWindowTitle("Einrichtungen verwalten")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumSize(900, 500)
        self.setup_ui()
        self.load_facilities()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("Neu")
        self.edit_btn = QPushButton("Bearbeiten")
        self.delete_btn = QPushButton("Löschen")
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Adresse", "Telefon", "Status", "Begründung",
            "Ansprechpartner 1", "Tel. AP1", "Ansprechpartner 2", "Tel. AP2"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.add_btn.clicked.connect(self.add_facility)
        self.edit_btn.clicked.connect(self.edit_facility)
        self.delete_btn.clicked.connect(self.delete_facility)

    def load_facilities(self):
        facilities = self.db.get_all_facilities()
        self.table.setRowCount(len(facilities))
        for row, facility in enumerate(facilities):
            self.table.setItem(row, 0, QTableWidgetItem(str(facility['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(facility['name']))
            self.table.setItem(row, 2, QTableWidgetItem(facility.get('adresse', '')))
            self.table.setItem(row, 3, QTableWidgetItem(facility.get('telefon', '')))
            status = facility.get('status', 'Frei')
            reason = facility.get('status_reason', '')
            status_item = QTableWidgetItem(status)
            if status == "Frei":
                status_item.setBackground(QColor(0, 200, 0))
            else:
                status_item.setBackground(QColor(200, 0, 0))
            self.table.setItem(row, 4, status_item)
            self.table.setItem(row, 5, QTableWidgetItem(reason))
            self.table.setItem(row, 6, QTableWidgetItem(facility.get('ansprechpartner1', '')))
            self.table.setItem(row, 7, QTableWidgetItem(facility.get('ansprechpartner1_tel', '')))
            self.table.setItem(row, 8, QTableWidgetItem(facility.get('ansprechpartner2', '')))
            self.table.setItem(row, 9, QTableWidgetItem(facility.get('ansprechpartner2_tel', '')))

    def add_facility(self):
        dialog = FacilityEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_facility_data()
            self.db.add_facility(data)
            self.load_facilities()

    def edit_facility(self):
        row = self.table.currentRow()
        if row >= 0:
            facility_id = int(self.table.item(row, 0).text())
            dialog = FacilityEditDialog(self, facility_id)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_facility_data()
                self.db.update_facility(facility_id, data)
                self.load_facilities()
        else:
            QMessageBox.warning(self, "Hinweis", "Bitte wählen Sie eine Einrichtung aus.")

    def delete_facility(self):
        row = self.table.currentRow()
        if row >= 0:
            facility_id = int(self.table.item(row, 0).text())
            reply = QMessageBox.question(self, "Löschen",
                                         "Einrichtung wirklich löschen?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.db.delete_facility(facility_id)
                self.load_facilities()
        else:
            QMessageBox.warning(self, "Hinweis", "Bitte wählen Sie eine Einrichtung aus.")

class FacilityEditDialog(QDialog):
    def __init__(self, parent=None, facility_id=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.facility_id = facility_id
        self.setWindowTitle("Einrichtung bearbeiten" if facility_id else "Neue Einrichtung")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setup_ui()
        if facility_id:
            self.load_facility()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.name = QLineEdit()
        self.address = QTextEdit()
        self.phone = QLineEdit()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Frei", "Gesperrt"])
        self.status_combo.currentTextChanged.connect(self.status_changed)
        self.status_reason = QLineEdit()
        self.status_reason.setPlaceholderText("Begründung bei 'Gesperrt' erforderlich")
        self.status_reason.setEnabled(False)

        # Ansprechpartner Felder
        self.ansprechpartner1 = QLineEdit()
        self.ansprechpartner1_tel = QLineEdit()
        self.ansprechpartner1_email = QLineEdit()
        self.ansprechpartner2 = QLineEdit()
        self.ansprechpartner2_tel = QLineEdit()
        self.ansprechpartner2_email = QLineEdit()

        layout.addRow("Name:", self.name)
        layout.addRow("Adresse:", self.address)
        layout.addRow("Telefon:", self.phone)
        layout.addRow("Status:", self.status_combo)
        layout.addRow("Begründung:", self.status_reason)
        layout.addRow("Ansprechpartner 1:", self.ansprechpartner1)
        layout.addRow("Telefon Ansprechpartner 1:", self.ansprechpartner1_tel)
        layout.addRow("E-Mail Ansprechpartner 1:", self.ansprechpartner1_email)
        layout.addRow("Ansprechpartner 2:", self.ansprechpartner2)
        layout.addRow("Telefon Ansprechpartner 2:", self.ansprechpartner2_tel)
        layout.addRow("E-Mail Ansprechpartner 2:", self.ansprechpartner2_email)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def status_changed(self, text):
        if text == "Gesperrt":
            self.status_reason.setEnabled(True)
            if not self.status_reason.text():
                reason, ok = QInputDialog.getText(self, "Begründung", "Bitte Begründung für Sperrung angeben:")
                if ok and reason:
                    self.status_reason.setText(reason)
        else:
            self.status_reason.setEnabled(False)
            self.status_reason.clear()

    def load_facility(self):
        facility = self.db.get_facility(self.facility_id)
        if facility:
            self.name.setText(facility['name'])
            self.address.setText(facility.get('adresse', ''))
            self.phone.setText(facility.get('telefon', ''))
            status = facility.get('status', 'Frei')
            index = self.status_combo.findText(status)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)
            self.status_reason.setText(facility.get('status_reason', ''))
            self.ansprechpartner1.setText(facility.get('ansprechpartner1', ''))
            self.ansprechpartner1_tel.setText(facility.get('ansprechpartner1_tel', ''))
            self.ansprechpartner1_email.setText(facility.get('ansprechpartner1_email', ''))
            self.ansprechpartner2.setText(facility.get('ansprechpartner2', ''))
            self.ansprechpartner2_tel.setText(facility.get('ansprechpartner2_tel', ''))
            self.ansprechpartner2_email.setText(facility.get('ansprechpartner2_email', ''))

    def accept(self):
        if self.status_combo.currentText() == "Gesperrt" and not self.status_reason.text():
            QMessageBox.warning(self, "Begründung fehlt", "Bitte geben Sie eine Begründung für die Sperrung an.")
            return
        super().accept()

    def get_facility_data(self):
        return {
            'name': self.name.text(),
            'adresse': self.address.toPlainText(),
            'telefon': self.phone.text(),
            'status': self.status_combo.currentText(),
            'status_reason': self.status_reason.text(),
            'ansprechpartner1': self.ansprechpartner1.text(),
            'ansprechpartner1_tel': self.ansprechpartner1_tel.text(),
            'ansprechpartner1_email': self.ansprechpartner1_email.text(),
            'ansprechpartner2': self.ansprechpartner2.text(),
            'ansprechpartner2_tel': self.ansprechpartner2_tel.text(),
            'ansprechpartner2_email': self.ansprechpartner2_email.text()
        }

class LivingAreaDialog(QDialog):
    def __init__(self, facility_id, parent=None, area_id=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.facility_id = facility_id
        self.area_id = area_id
        self.setWindowTitle("Wohnbereiche verwalten")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumSize(700, 400)
        self.setup_ui()
        self.load_areas()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("Neu")
        self.edit_btn = QPushButton("Bearbeiten")
        self.delete_btn = QPushButton("Löschen")
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Telefon-Durchwahl", "Fax"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.add_btn.clicked.connect(self.add_area)
        self.edit_btn.clicked.connect(self.edit_area)
        self.delete_btn.clicked.connect(self.delete_area)

    def load_areas(self):
        areas = self.db.get_all_living_areas(self.facility_id)
        self.table.setRowCount(len(areas))
        for row, area in enumerate(areas):
            self.table.setItem(row, 0, QTableWidgetItem(str(area['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(area.get('name', '')))
            self.table.setItem(row, 2, QTableWidgetItem(area.get('telefon', '')))
            self.table.setItem(row, 3, QTableWidgetItem(area.get('fax', '')))

    def add_area(self):
        dialog = LivingAreaEditDialog(self.facility_id, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_area_data()
            self.db.add_living_area(data)
            self.load_areas()

    def edit_area(self):
        row = self.table.currentRow()
        if row >= 0:
            area_id = int(self.table.item(row, 0).text())
            dialog = LivingAreaEditDialog(self.facility_id, self, area_id)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_area_data()
                self.db.update_living_area(area_id, data)
                self.load_areas()
        else:
            QMessageBox.warning(self, "Hinweis", "Bitte wählen Sie einen Wohnbereich aus.")

    def delete_area(self):
        row = self.table.currentRow()
        if row >= 0:
            area_id = int(self.table.item(row, 0).text())
            reply = QMessageBox.question(self, "Löschen",
                                         "Wohnbereich wirklich löschen?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.db.delete_living_area(area_id)
                self.load_areas()
        else:
            QMessageBox.warning(self, "Hinweis", "Bitte wählen Sie einen Wohnbereich aus.")

class LivingAreaEditDialog(QDialog):
    def __init__(self, facility_id, parent=None, area_id=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.facility_id = facility_id
        self.area_id = area_id
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setup_ui()
        if self.area_id:
            self.load_area()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.name = QLineEdit()
        self.phone = QLineEdit()
        self.fax = QLineEdit()
        layout.addRow("Name:", self.name)
        layout.addRow("Telefon-Durchwahl:", self.phone)  # <--- geändert
        layout.addRow("Fax:", self.fax)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def load_area(self):
        area = self.db.get_living_area(self.area_id)
        if area:
            self.name.setText(area['name'])
            self.phone.setText(area.get('telefon', ''))
            self.fax.setText(area.get('fax', ''))

    def get_area_data(self):
        return {
            'facility_id': self.facility_id,
            'name': self.name.text(),
            'phone': self.phone.text(),
            'fax': self.fax.text()
        }

class DispatcherDialog(QDialog):
    def __init__(self, parent=None, dispatcher_id=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.dispatcher_id = dispatcher_id
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setup_ui()
        self.load_dispatchers()

    def setup_ui(self):
        self.setWindowTitle("Disponenten verwalten")
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("Neu")
        self.edit_btn = QPushButton("Bearbeiten")
        self.delete_btn = QPushButton("Löschen")
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Vorname", "Nachname", "Büro", "Mobil", "Email"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.add_btn.clicked.connect(self.add_dispatcher)
        self.edit_btn.clicked.connect(self.edit_dispatcher)
        self.delete_btn.clicked.connect(self.delete_dispatcher)

    def load_dispatchers(self):
        dispatchers = self.db.get_all_dispatchers()
        self.table.setRowCount(len(dispatchers))
        for row, dispatcher in enumerate(dispatchers):
            self.table.setItem(row, 0, QTableWidgetItem(str(dispatcher['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(dispatcher.get('vorname', '')))
            self.table.setItem(row, 2, QTableWidgetItem(dispatcher.get('nachname', '')))
            self.table.setItem(row, 3, QTableWidgetItem(dispatcher.get('buero', '')))
            self.table.setItem(row, 4, QTableWidgetItem(dispatcher.get('handy', '')))
            self.table.setItem(row, 5, QTableWidgetItem(dispatcher.get('email', '')))

    def add_dispatcher(self):
        dialog = DispatcherEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_dispatcher_data()
            self.db.add_dispatcher(data)
            self.load_dispatchers()

    def edit_dispatcher(self):
        row = self.table.currentRow()
        if row >= 0:
            dispatcher_id = int(self.table.item(row, 0).text())
            dialog = DispatcherEditDialog(self, dispatcher_id)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_dispatcher_data()
                self.db.update_dispatcher(dispatcher_id, data)
                self.load_dispatchers()
        else:
            QMessageBox.warning(self, "Hinweis", "Bitte wählen Sie einen Disponenten aus.")

    def delete_dispatcher(self):
        row = self.table.currentRow()
        if row >= 0:
            dispatcher_id = int(self.table.item(row, 0).text())
            reply = QMessageBox.question(self, "Löschen",
                                         "Disponenten wirklich löschen?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.db.delete_dispatcher(dispatcher_id)
                self.load_dispatchers()
        else:
            QMessageBox.warning(self, "Hinweis", "Bitte wählen Sie einen Disponenten aus.")

class DispatcherEditDialog(QDialog):
    def __init__(self, parent=None, dispatcher_id=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.dispatcher_id = dispatcher_id
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setup_ui()
        if self.dispatcher_id:
            self.load_dispatcher()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.firstname = QLineEdit()
        self.lastname = QLineEdit()
        self.office = QLineEdit()
        self.mobile = QLineEdit()
        self.email = QLineEdit()
        layout.addRow("Vorname:", self.firstname)
        layout.addRow("Nachname:", self.lastname)
        layout.addRow("Büro:", self.office)
        layout.addRow("Mobil:", self.mobile)
        layout.addRow("Email:", self.email)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def load_dispatcher(self):
        dispatcher = self.db.get_dispatcher(self.dispatcher_id)
        if dispatcher:
            self.firstname.setText(dispatcher.get('vorname', ''))
            self.lastname.setText(dispatcher.get('nachname', ''))
            self.office.setText(dispatcher.get('buero', ''))
            self.mobile.setText(dispatcher.get('handy', ''))
            self.email.setText(dispatcher.get('email', ''))

    def get_dispatcher_data(self):
        return {
            'firstname': self.firstname.text(),
            'lastname': self.lastname.text(),
            'office': self.office.text(),
            'mobile': self.mobile.text(),
            'email': self.email.text()
        }

class CalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        import json
        parent_dialog = self.parentWidget()
        date = self.selectedDate()
        if event.mimeData().hasText():
            try:
                tpl = json.loads(event.mimeData().text())
                # Dienst für das Datum anlegen
                beginn = date.toString("yyyy-MM-dd") + " " + tpl['beginn'] + ":00"
                ende = date.toString("yyyy-MM-dd") + " " + tpl['ende'] + ":00"
                # Beschreibung bleibt wie in der Vorlage
                service_data = {
                    'beschreibung': tpl['name'],
                    'beginn': beginn,
                    'ende': ende,
                    'pause': tpl.get('pause', 0),
                    'einrichtung_id': tpl.get('einrichtung_id')
                }
                parent_dialog.db.add_service(service_data)
                parent_dialog.load_services()
                event.acceptProposedAction()
                return
            except Exception:
                pass
        super().dropEvent(event)

def get_shift_label_and_color(beginn, beschreibung):
    # Hole nur die Stunde aus dem Beginn
    try:
        stunde = int(beginn[11:13])
    except Exception:
        stunde = -1

    if stunde == 6:
        return ("Frühschicht 06:00", "#fbff00")
    elif stunde == 13:
        return ("Spätschicht 13:00", "#ff9100")
    elif stunde == 20:
        return ("Nachtschicht 20:00", "#002fff")
    elif beschreibung:
        return (beschreibung, "#3CB371")
    else:
        return ("Dienst " + beginn[11:16], "#3CB371")

class ServicePlanningDialog(QDialog):
    def __init__(self, parent=None, service_id=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.service_id = service_id
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Dienstplanung")
        self.setMinimumSize(1000, 700)

        main_layout = QVBoxLayout()

        # Toolbar mit Aktionen
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("Neu")
        self.edit_btn = QPushButton("Bearbeiten")
        self.delete_btn = QPushButton("Löschen")

        self.add_btn.clicked.connect(self.add_service)
        self.edit_btn.clicked.connect(self.edit_service)
        self.delete_btn.clicked.connect(self.delete_service)

        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()

        main_layout.addLayout(toolbar)

        # Hauptbereich
        content = QHBoxLayout()

        # Linke Seite - Kalender und Liste
        left_side = QVBoxLayout()

        # Kalender
        self.calendar = CalendarWidget(self)
        self.calendar.clicked.connect(self.date_selected)
        left_side.addWidget(self.calendar)

        self.services_list = ServiceTableWidget(self)
        self.services_list.setColumnCount(6)
        self.services_list.setHorizontalHeaderLabels([
            "ID", "Einrichtung", "Dienstname", "Beginn", "Pause", "Ende"
        ])
        left_side.addWidget(self.services_list)

        # Dienstvorlagen
        self.shift_template_list = ShiftTemplateListWidget(self)
        self.load_shift_templates()
        self.shift_template_list.setMaximumHeight(120)
        left_side.addWidget(QLabel("Dienstvorlagen:"))
        left_side.addWidget(self.shift_template_list)

        content.addLayout(left_side)
        main_layout.addLayout(content)
        self.setLayout(main_layout)

        # Initial Dienste laden
        self.load_services()

    def date_selected(self, date):
        services = self.db.get_services_for_date(date)
        self.services_list.setRowCount(len(services))
        for row, service in enumerate(services):
            self.services_list.setItem(row, 0, QTableWidgetItem(str(service['id'])))
            self.services_list.setItem(row, 1, QTableWidgetItem(service.get('facility_name', '')))
            beschreibung = service.get('beschreibung', '').strip()
            beginn = str(service['beginn'])
            label, color = get_shift_label_and_color(beginn, beschreibung)
            item = QTableWidgetItem(label)
            item.setBackground(QColor(color))
            item.setForeground(QColor("white"))
            self.services_list.setItem(row, 2, item)
            self.services_list.setItem(row, 3, QTableWidgetItem(beginn))
            self.services_list.setItem(row, 4, QTableWidgetItem(str(service['pause'])))
            self.services_list.setItem(row, 5, QTableWidgetItem(str(service['ende'])))
        self.services_list.resizeColumnsToContents()

    def load_services(self):
        services = self.db.get_all_services()
        self.services_list.setRowCount(len(services))
        for row, service in enumerate(services):
            self.services_list.setItem(row, 0, QTableWidgetItem(str(service['id'])))
            self.services_list.setItem(row, 1, QTableWidgetItem(service.get('facility_name', '')))
            beschreibung = service.get('beschreibung', '').strip()
            beginn = str(service['beginn'])
            label, color = get_shift_label_and_color(beginn, beschreibung)
            item = QTableWidgetItem(label)
            item.setBackground(QColor(color))
            item.setForeground(QColor("white"))
            self.services_list.setItem(row, 2, item)
            self.services_list.setItem(row, 3, QTableWidgetItem(beginn))
            self.services_list.setItem(row, 4, QTableWidgetItem(str(service['pause'])))
            self.services_list.setItem(row, 5, QTableWidgetItem(str(service['ende'])))
        self.services_list.resizeColumnsToContents()

    def load_shift_templates(self):
        self.shift_template_list.clear()
        templates = self.db.get_all_shift_templates()
        for tpl in templates:
            einrichtungsname = ""
            if tpl.get('einrichtung_id'):
                facility = self.db.get_facility(tpl['einrichtung_id'])
                if facility:
                    einrichtungsname = f" [{facility['name']}]"
            item = QListWidgetItem(f"{tpl['name']} ({tpl['beginn']} - {tpl['ende']}){einrichtungsname}")
            item.setData(Qt.UserRole, tpl)
            self.shift_template_list.addItem(item)

    def add_service(self):
        dialog = ServiceEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            service_data = dialog.get_service_data()
            self.db.add_service(service_data)
            self.load_services()

    def edit_service(self):
        current_row = self.services_list.currentRow()
        if current_row >= 0:
            service_id = int(self.services_list.item(current_row, 0).text())
            dialog = ServiceEditDialog(self, service_id)
            if dialog.exec_() == QDialog.Accepted:
                service_data = dialog.get_service_data()
                self.db.update_service(service_id, service_data)
                self.load_services()
        else:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Dienst aus.")

    def delete_service(self):
        current_row = self.services_list.currentRow()
        if current_row >= 0:
            service_id = int(self.services_list.item(current_row, 0).text())
            reply = QMessageBox.question(self, "Dienst löschen",
                                         "Möchten Sie diesen Dienst wirklich löschen?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.db.delete_service(service_id)
                self.load_services()
        else:
            QMessageBox.warning(self, "Fehler", "Bitte wählen Sie einen Dienst aus.")

class ServiceEditDialog(QDialog):
    def __init__(self, parent=None, service_id=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.service_id = service_id
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Dienst bearbeiten" if self.service_id else "Neuer Dienst")
        layout = QFormLayout()

        # Dienstname (Beschreibung) ganz oben
        self.description = QLineEdit()
        self.description.setPlaceholderText("Dienstname / Beschreibung")
        layout.addRow("Dienstname:", self.description)

        # Datum und Zeit
        self.begin_datetime = QDateTimeEdit()
        self.begin_datetime.setCalendarPopup(True)
        self.begin_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.begin_datetime.setDateTime(QDateTime.currentDateTime())

        self.end_datetime = QDateTimeEdit()
        self.end_datetime.setCalendarPopup(True)
        self.end_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_datetime.setDateTime(QDateTime.currentDateTime().addSecs(8*3600))

        self.pause_spin = QSpinBox()
        self.pause_spin.setRange(0, 120)
        self.pause_spin.setSuffix(" Minuten")
        self.pause_spin.setValue(30)

        # Felder in neuer Reihenfolge
        layout.addRow("Beginn:", self.begin_datetime)
        layout.addRow("Ende:", self.end_datetime)
        layout.addRow("Pause:", self.pause_spin)

        # Einrichtung ganz unten
        self.facility_combo = QComboBox()
        self.facility_combo.addItem("Keine Zuordnung", None)
        self.load_facilities()
        layout.addRow("Einrichtung:", self.facility_combo)

        # Dienstvorlage
        self.template_combo = QComboBox()
        self.template_combo.addItem("Manuell", None)
        self.load_templates()
        self.template_combo.currentIndexChanged.connect(self.apply_template)
        layout.addRow("Dienstvorlage:", self.template_combo)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

        if self.service_id:
            self.load_service()

    def load_facilities(self):
        facilities = self.db.get_all_facilities()
        for facility in facilities:
            self.facility_combo.addItem(facility['name'], facility['id'])

    def load_templates(self):
        self.templates = self.db.get_all_shift_templates()
        for tpl in self.templates:
            self.template_combo.addItem(tpl['name'], tpl['id'])

    def apply_template(self):
        idx = self.template_combo.currentIndex()
        if idx > 0:
            tpl = self.templates[idx-1]
            # Setze Beginn, Ende, Pause
            today = QDate.currentDate()
            self.begin_datetime.setDateTime(QDateTime.fromString(today.toString("yyyy-MM-dd") + " " + tpl['beginn'], "yyyy-MM-dd HH:mm"))
            self.end_datetime.setDateTime(QDateTime.fromString(today.toString("yyyy-MM-dd") + " " + tpl['ende'], "yyyy-MM-dd HH:mm"))
            self.pause_spin.setValue(tpl.get('pause', 0))

    def load_service(self):
        service = self.db.get_service(self.service_id)
        if service:
            self.description.setText(service.get('beschreibung', ''))
            index = self.facility_combo.findData(service['einrichtung_id'])
            if index >= 0:
                self.facility_combo.setCurrentIndex(index)
            try:
                self.begin_datetime.setDateTime(QDateTime.fromString(service['beginn'], "yyyy-MM-dd HH:mm:ss"))
                self.end_datetime.setDateTime(QDateTime.fromString(service['ende'], "yyyy-MM-dd HH:mm:ss"))
            except Exception:
                pass
            self.pause_spin.setValue(service['pause'])

    def get_service_data(self):
        return {
            'beschreibung': self.description.text(),
            'beginn': self.begin_datetime.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            'ende': self.end_datetime.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            'pause': self.pause_spin.value(),
            'einrichtung_id': self.facility_combo.currentData()
        }

class ServiceExporter:
    def __init__(self):
        self.db = DatabaseManager()
    
    def export_monthly_services(self, facility_id, year, month):
        facility = self.db.get_facility(facility_id)
        services = self.db.get_monthly_services(facility_id, year, month)
        filename = f"Dienste_{facility['name']}_{year}_{month}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        # Deutsche Monatsnamen
        monate = [
            "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember"
        ]
        monat_de = monate[month - 1]

        # Kopfzeile
        header_style = ParagraphStyle('header', fontSize=24, leading=28, spaceAfter=10, leftIndent=0)
        subheader_style = ParagraphStyle('subheader', fontSize=10, alignment=2, spaceAfter=2)
        elements.append(Paragraph(f"{monat_de} {year}", header_style))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            f"<b>Gebuchte Dienste</b><br/><font size=9>{facility['name']}</font><br/>{datetime.now().strftime('%d.%m.%Y')}",
            subheader_style
        ))
        elements.append(Spacer(1, 18))

        # Tabellendaten vorbereiten
        data = [["Tag", "Uhrzeit", "Titel", "Ort"]]
        weekday_colors = {
            0: colors.HexColor("#0070c0"),  # Mo
            1: colors.HexColor("#0070c0"),  # Di
            2: colors.HexColor("#0070c0"),  # Mi
            3: colors.HexColor("#0070c0"),  # Do
            4: colors.HexColor("#0070c0"),  # Fr
            5: colors.HexColor("#00b050"),  # Sa
            6: colors.HexColor("#00b050"),  # So
        }
        wochentage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        total_minutes = 0

        # Adresse für den Ort-Absatz vorbereiten
        adresse = facility.get('adresse', '')
        plz_ort = ""
        # Versuche PLZ und Ort zu extrahieren (z.B. "Musterstraße 1, 12345 Musterstadt")
        import re
        plz_ort_match = re.search(r'(\d{5})\s+([^\d,]+)', adresse)
        if plz_ort_match:
            plz_ort = f"{plz_ort_match.group(1)} {plz_ort_match.group(2).strip()}"
        else:
            plz_ort = ""
        # Adresse splitten
        adresse_zeilen = adresse.split(",")
        strasse = adresse_zeilen[0].strip() if adresse_zeilen else ""
        ort_zeile = adresse_zeilen[1].strip() if len(adresse_zeilen) > 1 else plz_ort

        ort_absatz = f"{facility['name']}<br/>{strasse}<br/>{ort_zeile}"

        # Alle Tage des Monats durchgehen
        import calendar
        from datetime import datetime as dt
        days_in_month = calendar.monthrange(year, month)[1]
        # Dienste nach Tag gruppieren
        dienste_by_day = {}
        for service in services:
            tag = service['date'].day
            if tag not in dienste_by_day:
                dienste_by_day[tag] = []
            dienste_by_day[tag].append(service)

        for day in range(1, days_in_month + 1):
            datum = dt(year, month, day)
            weekday = datum.weekday()
            tag_label = f"{day} <font color='{weekday_colors[weekday].hexval()}'><b>{wochentage[weekday]}</b></font>"
            if day in dienste_by_day:
                for service in dienste_by_day[day]:
                    uhrzeit = f"{service['begin'].strftime('%H:%M')} - {service['end'].strftime('%H:%M')}"
                    titel = service.get('beschreibung', '')
                    data.append([
                        Paragraph(tag_label, styles['Normal']),
                        uhrzeit,
                        titel,
                        Paragraph(ort_absatz, styles['Normal'])
                    ])
                    beginn = service['begin']
                    ende = service['end']
                    pause = int(service.get('pause', 0))
                    diff = (ende - beginn).total_seconds() / 60 - pause
                    total_minutes += max(diff, 0)
            else:
                # Leerer Tag: keine Adresse/Ort anzeigen
                data.append([
                    Paragraph(tag_label, styles['Normal']),
                    "",
                    "",
                    ""
                ])

        # Tabelle
        table = Table(data, colWidths=[22*mm, 35*mm, 60*mm, 55*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),
            ('LINEBELOW', (0, 1), (-1, -1), 0.25, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)

        # Gesamtstunden berechnen und anzeigen
        total_hours = int(total_minutes // 60)
        total_rest = int(total_minutes % 60)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(
            f"<b>Gesamtstunden:</b> {total_hours} Std {total_rest} Min / 152 Std",
            styles['Normal']
        ))

        doc.build(elements)
        return filename

class DutyCalendarDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.current_year = QDate.currentDate().year()
        self.current_month = QDate.currentDate().month()
        self.setMinimumSize(900, 600)
        self.setWindowTitle("Dienstplan Monatsübersicht")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.layout = QVBoxLayout(self)
        self.header = QLabel()
        self.header.setStyleSheet("font-size: 20px; font-weight: bold; color: white;")
        self.layout.addWidget(self.header)
        self.grid = QGridLayout()
        self.layout.addLayout(self.grid)
        self.draw_calendar()

    def draw_calendar(self):
        self.header.setText(QDate(self.current_year, self.current_month, 1).toString("MMMM yyyy"))
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        for col, day in enumerate(weekdays):
            lbl = QLabel(day)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; color: #aaa;")
            self.grid.addWidget(lbl, 0, col)
        first_day = QDate(self.current_year, self.current_month, 1)
        start_col = (first_day.dayOfWeek() + 6) % 7
        days_in_month = first_day.daysInMonth()
        row = 1
        col = start_col
        for day in range(1, days_in_month + 1):
            cell = QWidget()
            vbox = QVBoxLayout(cell)
            vbox.setContentsMargins(2, 2, 2, 2)
            day_lbl = QLabel(str(day))
            day_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            day_lbl.setStyleSheet("color: white; font-size: 12px;")
            vbox.addWidget(day_lbl)
            services = self.db.get_services_for_date(QDate(self.current_year, self.current_month, day))
            for service in services:
                beschreibung = service.get('beschreibung', '').strip()
                beginn = str(service['beginn'])
                label, color = get_shift_label_and_color(beginn, beschreibung)
                dienst_lbl = QLabel(label)
                dienst_lbl.setAlignment(Qt.AlignCenter)
                dienst_lbl.setStyleSheet(
                    f"background: {color}; color: white; border-radius: 6px; padding: 2px 6px; margin-top: 2px;"
                )
                vbox.addWidget(dienst_lbl)
            self.grid.addWidget(cell, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

        # Gesamtstunden berechnen und anzeigen
        services = []
        for day in range(1, days_in_month + 1):
            services += self.db.get_services_for_date(QDate(self.current_year, self.current_month, day))

        total_minutes = 0
        for service in services:
            try:
                beginn = datetime.strptime(service['beginn'], "%Y-%m-%d %H:%M:%S")
                ende = datetime.strptime(service['ende'], "%Y-%m-%d %H:%M:%S")
                pause = int(service.get('pause', 0))
                diff = (ende - beginn).total_seconds() / 60 - pause
                total_minutes += max(diff, 0)
            except Exception:
                pass

        total_hours = total_minutes // 60
        total_rest = int(total_minutes % 60)

        # Label am unteren Rand anzeigen
        if hasattr(self, "hours_label"):
            self.hours_label.setText(f"Gesamtstunden: {int(total_hours)} Std {total_rest} Min / 152 Std")
        else:
            self.hours_label = QLabel(f"Gesamtstunden: {int(total_hours)} Std {total_rest} Min / 152 Std")
            self.hours_label.setStyleSheet("font-size: 14px; color: #fff; margin-top: 10px;")
            self.layout.addWidget(self.hours_label)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            if self.current_month == 1:
                self.current_month = 12
                self.current_year -= 1
            else:
                self.current_month -= 1
            self.draw_calendar()
        elif event.key() == Qt.Key_Right:
            if self.current_month == 12:
                self.current_month = 1
                self.current_year += 1
            else:
                self.current_month += 1
            self.draw_calendar()
        else:
            super().keyPressEvent(event)

class ServiceTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def startDrag(self, supportedActions):
        current_row = self.currentRow()
        if current_row >= 0:
            service_id = self.item(current_row, 0).text()
            mimeData = QMimeData()
            mimeData.setText(service_id)
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec_(Qt.MoveAction)

class ShiftTemplateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.setWindowTitle("Dienstvorlagen verwalten")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumSize(500, 300)
        self.setup_ui()
        self.load_templates()

   

    def setup_ui(self):
        layout = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("Neu")
        self.edit_btn = QPushButton("Bearbeiten")
        self.delete_btn = QPushButton("Löschen")
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Beginn", "Ende", "Einrichtung"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        self.add_btn.clicked.connect(self.add_template)
        self.edit_btn.clicked.connect(self.edit_template)
        self.delete_btn.clicked.connect(self.delete_template)

    def load_templates(self):
        templates = self.db.get_all_shift_templates()
        self.table.setRowCount(len(templates))
        for row, tpl in enumerate(templates):
            self.table.setItem(row, 0, QTableWidgetItem(str(tpl['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(tpl['name']))
            self.table.setItem(row, 2, QTableWidgetItem(tpl['beginn']))
            self.table.setItem(row, 3, QTableWidgetItem(tpl['ende']))
            facility_name = ""
            if tpl.get('einrichtung_id'):
                facility = self.db.get_facility(tpl['einrichtung_id'])
                if facility:
                    facility_name = facility['name']
            self.table.setItem(row, 4, QTableWidgetItem(facility_name))

    def add_template(self):
        dialog = ShiftTemplateEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_template_data()
            self.db.add_shift_template(data)
            self.load_templates()

    def edit_template(self):
        row = self.table.currentRow()
        if row >= 0:
            tpl_id = int(self.table.item(row, 0).text())
            dialog = ShiftTemplateEditDialog(self, tpl_id)
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_template_data()
                self.db.update_shift_template(tpl_id, data)
                self.load_templates()

    def delete_template(self):
        row = self.table.currentRow()
        if row >= 0:
            tpl_id = int(self.table.item(row, 0).text())
            self.db.delete_shift_template(tpl_id)
            self.load_templates()

class ShiftTemplateEditDialog(QDialog):
    def __init__(self, parent=None, tpl_id=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.tpl_id = tpl_id
        self.setWindowTitle("Dienstvorlage bearbeiten" if tpl_id else "Neue Dienstvorlage")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setup_ui()
        if tpl_id:
            self.load_template()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.name = QLineEdit()
        self.begin = QTimeEdit()
        self.begin.setDisplayFormat("HH:mm")
        self.end = QTimeEdit()
        self.end.setDisplayFormat("HH:mm")
        self.pause = QSpinBox()
        self.pause.setRange(0, 120)
        self.pause.setSuffix(" Minuten")
        # Einrichtungsauswahl
        self.facility_combo = QComboBox()
        self.facility_combo.addItem("Keine Zuordnung", None)
        self.load_facilities()
        layout.addRow("Name:", self.name)
        layout.addRow("Beginn:", self.begin)
        layout.addRow("Ende:", self.end)
        layout.addRow("Pause:", self.pause)
        layout.addRow("Einrichtung:", self.facility_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.setLayout(layout)

    def load_facilities(self):
        facilities = self.db.get_all_facilities()
        for facility in facilities:
            self.facility_combo.addItem(facility['name'], facility['id'])

    def load_template(self):
        tpl = self.db.get_all_shift_templates()
        tpl = next((t for t in tpl if t['id'] == self.tpl_id), None)
        if tpl:
            self.name.setText(tpl['name'])
            self.begin.setTime(QTime.fromString(tpl['beginn'], "HH:mm"))
            self.end.setTime(QTime.fromString(tpl['ende'], "HH:mm"))
            self.pause.setValue(tpl.get('pause', 0))
            # Einrichtung setzen
            idx = self.facility_combo.findData(tpl.get('einrichtung_id'))
            if idx >= 0:
                self.facility_combo.setCurrentIndex(idx)

    def get_template_data(self):
        return {
            'name': self.name.text(),
            'beginn': self.begin.time().toString("HH:mm"),
            'ende': self.end.time().toString("HH:mm"),
            'pause': self.pause.value(),
            'einrichtung_id': self.facility_combo.currentData()
        }

class ShiftTemplateListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            tpl = item.data(Qt.UserRole)
            mimeData = QMimeData()
            # Wir kodieren die Vorlage als Text, z.B. als JSON
            import json
            mimeData.setText(json.dumps(tpl))
            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.exec_(Qt.MoveAction)

class UserSettingsDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.db_path = "app.db"
        self.user_id = user_id
        self.setWindowTitle("Benutzereinstellungen")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setup_ui()
        self.load_user()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.firstname = QLineEdit()
        self.lastname = QLineEdit()
        layout.addRow("Vorname:", self.firstname)
        layout.addRow("Nachname:", self.lastname)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.setLayout(layout)

    def load_user(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT vorname, nachname FROM benutzer WHERE id=?", (self.user_id,))
        row = c.fetchone()
        conn.close()
        if row:
            self.firstname.setText(row[0] or "")
            self.lastname.setText(row[1] or "")

    def save(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE benutzer SET vorname=?, nachname=? WHERE id=?",
                  (self.firstname.text(), self.lastname.text(), self.user_id))
        conn.commit()
        conn.close()
        self.accept()

def main():
    # Datenbank initialisieren
    init_db()
    
    app = QApplication(sys.argv)
    
    # Windows 10/11 Dark Title Bar
    if sys.platform == "win32":
        import ctypes
        from ctypes.wintypes import DWORD
        try:
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            for hwnd in range(1, 10):  # Check first few window handles
                try:
                    set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(2)), ctypes.sizeof(ctypes.c_int))
                except:
                    pass
        except:
            pass
    
    app.setStyle("Fusion")
    
    # Dark Mode
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)

    app.setStyleSheet("""
        QWidget {
            background: #23272e;
            color: #e0e0e0;
            border-radius: 12px;
            border: 1.5px solid #353535;
        }
        QMainWindow, QDialog {
            background: #23272e;
            border-radius: 16px;
            border: 1.5px solid #353535;
        }
        QGroupBox {
            background: #23272e;
            border: 1.5px solid #353535;
            border-radius: 12px;
            margin-top: 16px;
            font-weight: bold;
            color: #fff;
        }
        QGroupBox:title {
            subcontrol-origin: margin;
            left: 10px;
            top: 2px;
            padding: 0 4px;
            color: #b0b3b8;
            background: transparent;
        }
        QLabel {
            color: #e0e0e0;
        }
        QTableWidget, QTableView {
            background: #18191c;
            color: #fff;
            border-radius: 8px;
            border: 1.5px solid #353535;
            gridline-color: #353535;
            selection-background-color: #23272e;
            selection-color: #fff;
        }
        QHeaderView::section {
            background: #23272e;
            color: #b0b3b8;
            border: 1px solid #353535;
            border-radius: 6px;
            padding: 4px;
        }
        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDateTimeEdit, QTimeEdit {
            background: #18191c;
            color: #fff;
            border-radius: 8px;
            border: 1.5px solid #353535;
            padding: 4px 8px;
            selection-background-color: #23272e;
            selection-color: #fff;
        }
        QPushButton {
            background: #23272e;
            color: #b0b3b8;
            border: 2px solid #444;
            border-radius: 8px;
            padding: 8px 18px;
            font-size: 15px;
            margin-bottom: 4px;
        }
        QPushButton:hover {
            background: #353535;
            color: #fff;
            border: 2px solid #888;
        }
        QCalendarWidget QWidget {
            background: #23272e;
            color: #fff;
            border-radius: 8px;
        }
        QScrollBar:vertical, QScrollBar:horizontal {
            background: #18191c;
            border-radius: 6px;
            width: 12px;
            margin: 2px;
        }
        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
            background: #353535;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::add-line, QScrollBar::sub-line {
            background: none;
            border: none;
        }
    """)

    # Benutzerabfrage bei Erststart
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute("SELECT * FROM benutzer")
    user = c.fetchone()
    if not user:
        while True:
            dialog = QDialog()
            dialog.setWindowTitle("Benutzer anlegen")
            dialog.setWindowIcon(QIcon(ICON_PATH))
            layout = QFormLayout(dialog)
            firstname = QLineEdit()
            lastname = QLineEdit()
            layout.addRow("Vorname:", firstname)
            layout.addRow("Nachname:", lastname)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, dialog)
            layout.addRow(buttons)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            dialog.setLayout(layout)
            if dialog.exec_() == QDialog.Accepted and firstname.text().strip() and lastname.text().strip():
                c.execute("INSERT INTO benutzer (benutzername, passwort, vorname, nachname, rolle) VALUES (?, ?, ?, ?, ?)",
                          (firstname.text().lower(), "", firstname.text(), lastname.text(), "user"))
                conn.commit()
                c.execute("SELECT * FROM benutzer WHERE benutzername=?", (firstname.text().lower(),))
                user = c.fetchone()
                break
            else:
                sys.exit(0)
    conn.close()

    # Dashboard öffnen
    dashboard = Dashboard(user)
    dashboard.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()