import sys
import sqlite3
from datetime import datetime
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPalette
from reportlab.pdfgen import canvas
from PyQt5.QtCore import *
import webbrowser
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

APP_VERSION = "1.0.0a"

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

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
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
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Dienstplaner")
        self.setMinimumSize(800, 600)
        
        # Zentrales Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Willkommensnachricht
        welcome = QLabel(f"Willkommen, {self.user_data[3]}!")  # Verwende den Vornamen
        welcome.setStyleSheet("font-size: 24px; margin: 20px;")
        layout.addWidget(welcome)
        
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
        
        # Disponent Info
        self.dispatcher_info = QGroupBox("Disponent")
        dispatcher_layout = QVBoxLayout()
        self.dispatcher_label = QLabel("Kein Disponent ausgewählt")
        dispatcher_layout.addWidget(self.dispatcher_label)
        self.dispatcher_info.setLayout(dispatcher_layout)
        widgets_container.addWidget(self.dispatcher_info)
        
        layout.addLayout(widgets_container)

        # Monatskalender-Ansicht direkt im Dashboard anzeigen
        self.month_calendar = DutyCalendarWidget(self)
        layout.addWidget(self.month_calendar)

        # Menüleiste
        menubar = self.menuBar()
        
        # Datei-Menü
        file_menu = menubar.addMenu("Datei")
        
        new_service_action = QAction("Neuer Dienst", self)
        new_service_action.triggered.connect(self.new_service)
        file_menu.addAction(new_service_action)
        
        export_action = QAction("Dienste exportieren", self)
        export_action.triggered.connect(self.export_services)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Beenden", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Verwaltungs-Menü
        admin_menu = menubar.addMenu("Verwaltung")
        
        facility_action = QAction("Einrichtungen", self)
        facility_action.triggered.connect(self.manage_facilities)
        admin_menu.addAction(facility_action)
        
        living_areas_action = QAction("Wohnbereiche", self)
        living_areas_action.triggered.connect(self.manage_living_areas)
        admin_menu.addAction(living_areas_action)
        
        dispatcher_action = QAction("Disponenten", self)
        dispatcher_action.triggered.connect(self.manage_dispatchers)
        admin_menu.addAction(dispatcher_action)
        
        service_action = QAction("Dienste", self)
        service_action.triggered.connect(self.manage_services)
        admin_menu.addAction(service_action)
        
        # Monatsansicht-Menü
        calendar_action = QAction("Dienstplan Monatsansicht", self)
        calendar_action.triggered.connect(self.show_duty_calendar)
        menubar.addAction(calendar_action)
        
        # Version
        version_label = QLabel(f"Version {APP_VERSION}")
        version_label.setAlignment(QtCore.Qt.AlignRight)
        version_label.setStyleSheet("color: gray; padding: 5px;")
        layout.addWidget(version_label)

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

    def show_duty_calendar(self):
        dlg = DutyCalendarDialog(self)
        dlg.exec_()

class DutyCalendarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.current_year = QDate.currentDate().year()
        self.current_month = QDate.currentDate().month()
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
                color = "#3CB371"
                text = "Dienst"
                beginn = service['beginn']
                if "22:" in beginn or "23:" in beginn or "00:" in beginn:
                    color = "#e74c3c"
                    text = "Nacht"
                elif "06:" in beginn or "07:" in beginn or "08:" in beginn:
                    color = "#8e44ad"
                    text = "Früh"
                elif "14:" in beginn or "15:" in beginn:
                    color = "#27ae60"
                    text = "Spät"
                dienst_lbl = QLabel(f"{text} {beginn[11:16]}")
                dienst_lbl.setAlignment(Qt.AlignCenter)
                dienst_lbl.setStyleSheet(f"background: {color}; color: white; border-radius: 6px; padding: 2px 6px; margin-top: 2px;")
                vbox.addWidget(dienst_lbl)
            self.grid.addWidget(cell, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

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

class FacilityDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.setWindowTitle("Einrichtungen verwalten")
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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Adresse", "Telefon", "Status", "Begründung"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
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
            # Status und Begründung
            status = facility.get('status', 'Frei')
            reason = facility.get('status_reason', '')
            status_item = QTableWidgetItem(status)
            if status == "Frei":
                status_item.setBackground(QtGui.QColor(0, 200, 0))
            else:
                status_item.setBackground(QtGui.QColor(200, 0, 0))
            self.table.setItem(row, 4, status_item)
            self.table.setItem(row, 5, QTableWidgetItem(reason))

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
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Telefon", "Fax"])
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
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        
class ServicePlanningDialog(QDialog):
    def __init__(self, parent=None, service_id=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.service_id = service_id
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Dienstplanung")
        self.setMinimumSize(1000, 700)

        main_layout = QVBoxLayout()

        # Toolbar mit Aktionen
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("Neuer Dienst")
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
        self.calendar = CalendarWidget()
        self.calendar.clicked.connect(self.date_selected)
        left_side.addWidget(self.calendar)

        # Dienste Liste
        self.services_list = QTableWidget()
        self.services_list.setColumnCount(6)
        self.services_list.setHorizontalHeaderLabels(["ID", "Einrichtung", "Dienstname", "Beginn", "Pause", "Ende"])
        self.services_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.services_list.setSelectionMode(QTableWidget.SingleSelection)
        left_side.addWidget(self.services_list)

        content.addLayout(left_side)
        main_layout.addLayout(content)
        self.setLayout(main_layout)

        # Initial Dienste laden
        self.load_services()

    def date_selected(self, date):
        # Zeige nur Dienste für das gewählte Datum an
        services = self.db.get_services_for_date(date)
        self.services_list.setRowCount(len(services))
        for row, service in enumerate(services):
            self.services_list.setItem(row, 0, QTableWidgetItem(str(service['id'])))
            self.services_list.setItem(row, 1, QTableWidgetItem(service.get('facility_name', '')))
            # Dienstname statt Uhrzeit anzeigen
            beschreibung = service.get('beschreibung', '').strip()
            dienstname = beschreibung if beschreibung else "Dienst"
            self.services_list.setItem(row, 2, QTableWidgetItem(dienstname))
            self.services_list.setItem(row, 3, QTableWidgetItem(str(service['beginn'])))
            self.services_list.setItem(row, 4, QTableWidgetItem(str(service['pause'])))
            self.services_list.setItem(row, 5, QTableWidgetItem(str(service['ende'])))
        self.services_list.resizeColumnsToContents()

    def load_services(self):
        # Zeige alle Dienste an
        services = self.db.get_all_services()
        self.services_list.setRowCount(len(services))
        for row, service in enumerate(services):
            self.services_list.setItem(row, 0, QTableWidgetItem(str(service['id'])))
            self.services_list.setItem(row, 1, QTableWidgetItem(service.get('facility_name', '')))
            # Dienstname statt Uhrzeit anzeigen
            beschreibung = service.get('beschreibung', '').strip()
            dienstname = beschreibung if beschreibung else "Dienst"
            self.services_list.setItem(row, 2, QTableWidgetItem(dienstname))
            self.services_list.setItem(row, 3, QTableWidgetItem(str(service['beginn'])))
            self.services_list.setItem(row, 4, QTableWidgetItem(str(service['pause'])))
            self.services_list.setItem(row, 5, QTableWidgetItem(str(service['ende'])))
        self.services_list.resizeColumnsToContents()

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
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Dienst bearbeiten" if self.service_id else "Neuer Dienst")
        layout = QFormLayout()

        # Einrichtung auswählen
        self.facility_combo = QComboBox()
        self.load_facilities()

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

        self.description = QLineEdit()
        self.description.setPlaceholderText("Beschreibung (optional)")

        # Layout befüllen
        layout.addRow("Einrichtung:", self.facility_combo)
        layout.addRow("Beginn:", self.begin_datetime)
        layout.addRow("Ende:", self.end_datetime)
        layout.addRow("Pause:", self.pause_spin)
        layout.addRow("Beschreibung:", self.description)

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
        self.facility_combo.clear()
        for facility in facilities:
            self.facility_combo.addItem(facility['name'], facility['id'])

    def load_service(self):
        service = self.db.get_service(self.service_id)
        if service:
            index = self.facility_combo.findData(service['einrichtung_id'])
            if index >= 0:
                self.facility_combo.setCurrentIndex(index)
            try:
                self.begin_datetime.setDateTime(QDateTime.fromString(service['beginn'], "yyyy-MM-dd HH:mm:ss"))
                self.end_datetime.setDateTime(QDateTime.fromString(service['ende'], "yyyy-MM-dd HH:mm:ss"))
            except Exception:
                pass
            self.pause_spin.setValue(service['pause'])
            self.description.setText(service.get('beschreibung', ''))

    def get_service_data(self):
        return {
            'einrichtung_id': self.facility_combo.currentData(),
            'beginn': self.begin_datetime.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            'ende': self.end_datetime.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            'pause': self.pause_spin.value(),
            'beschreibung': self.description.text()
        }

class ServiceExporter:
    def __init__(self):
        self.db = DatabaseManager()
    
    def export_monthly_services(self, facility_id, year, month):
        facility = self.db.get_facility(facility_id)
        services = self.db.get_monthly_services(facility_id, year, month)
        
        filename = f"Dienste_{facility['name']}_{year}_{month}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=A4)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Überschrift
        title = Paragraph(
            f"Gebuchte Dienste - {facility['name']}", 
            styles['Heading1']
        )
        elements.append(title)
        
        # Metadaten
        meta = Paragraph(
            f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}", 
            styles['Normal']
        )
        elements.append(meta)
        
        # Diensttabelle
        data = [['Datum', 'Beginn', 'Ende', 'Pause', 'Beschreibung']]
        for service in services:
            data.append([
                service['date'].strftime('%d.%m.%Y'),
                service['begin'].strftime('%H:%M'),
                service['end'].strftime('%H:%M'),
                f"{service['pause']} Min.",
                service.get('beschreibung', '')
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
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
                color = "#3CB371"
                text = "Dienst"
                beginn = service['beginn']
                if "22:" in beginn or "23:" in beginn or "00:" in beginn:
                    color = "#e74c3c"
                    text = "Nacht"
                elif "06:" in beginn or "07:" in beginn or "08:" in beginn:
                    color = "#8e44ad"
                    text = "Früh"
                elif "14:" in beginn or "15:" in beginn:
                    color = "#27ae60"
                    text = "Spät"
                dienst_lbl = QLabel(f"{text} {beginn[11:16]}")
                dienst_lbl.setAlignment(Qt.AlignCenter)
                dienst_lbl.setStyleSheet(f"background: {color}; color: white; border-radius: 6px; padding: 2px 6px; margin-top: 2px;")
                vbox.addWidget(dienst_lbl)
            self.grid.addWidget(cell, row, col)
            col += 1
            if col > 6:
                col = 0
                row += 1

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

def main():
    # Datenbank initialisieren
    init_db()
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Dark Mode
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, QtCore.Qt.white)
    dark_palette.setColor(QPalette.Base, QtGui.QColor(25, 25, 25))
    dark_palette.setColor(QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, QtCore.Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, QtCore.Qt.white)
    dark_palette.setColor(QPalette.Text, QtCore.Qt.white)
    dark_palette.setColor(QPalette.Button, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, QtCore.Qt.white)
    dark_palette.setColor(QPalette.BrightText, QtCore.Qt.red)
    dark_palette.setColor(QPalette.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QPalette.HighlightedText, QtCore.Qt.black)
    app.setPalette(dark_palette)
    
    # Login Dialog
    login = LoginDialog()
    if login.exec_() == QDialog.Accepted:
        # Dashboard öffnen
        dashboard = Dashboard(login.user_data)
        dashboard.show()
        sys.exit(app.exec_())

if __name__ == "__main__":
    main()