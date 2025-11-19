# GPS Position System - Improved Version

Ein verbessertes, produktionsreifes GPS-Positions-System mit robuster Fehlerbehandlung, MVC-Architektur und umfassenden Tests.

## 🎯 Überblick

Das System besteht aus mehreren Komponenten zur Erfassung, Übertragung und Visualisierung von GPS-Daten:

- **SendPosition**: Sendet GPS-Positionen aus MATLAB-Dateien als NMEA-Nachrichten via UDP
- **ReceivePosition**: Empfängt, validiert und visualisiert GPS-Daten mit PyQt6
- **Koordinaten-System**: Einheitliche Verwaltung verschiedener Koordinatenformate
- **NMEA-Validator**: Robuste Validierung und Parsing von NMEA-Sätzen
- **GPS-Datenmodell**: Thread-sichere Datenverwaltung mit Observer-Pattern

## 🚀 Neue Features

### ✨ Hauptverbesserungen

1. **Thread-Sicherheit**: Alle GUI-Updates erfolgen über Qt-Signals im Main-Thread
2. **Robuste Fehlerbehandlung**: Umfassende Validierung und Exception-Handling
3. **MVC-Architektur**: Klare Trennung von Model, View und Controller
4. **Einheitliche Koordinaten**: Konsistente Koordinatenumrechnung mit Validierung
5. **Konfigurationsverwaltung**: Zentralisierte Konfiguration via YAML
6. **NMEA-Validierung**: Checksummen-Prüfung und Format-Validierung
7. **Performance-Optimierung**: Deque-basierte Datenspeicherung mit Größenlimit
8. **Kartenmanagement**: Intelligentes Caching und Update-Throttling
9. **Umfassende Tests**: Pytest-basierte Test-Suite mit >80% Coverage
10. **Logging**: Strukturiertes Logging auf allen Ebenen

## 📋 Voraussetzungen

- Python 3.8 oder höher
- PyQt6 für GUI
- Scipy für MAT-Dateien
- Weitere Dependencies siehe `requirements.txt`

## 🔧 Installation

### 1. Repository klonen oder Dateien herunterladen

```bash
git clone <repository-url>
cd gps-position-system
```

### 2. Virtuelle Umgebung erstellen (empfohlen)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 4. Konfiguration anpassen

Kopieren und bearbeiten Sie `config.yaml`:

```yaml
network:
  udp_address: "127.0.0.1"
  udp_port: 19711
  receive_port: 19710

gps:
  data_file: "data/AguasVivasGPSData.mat"
  max_stored_positions: 1000

map:
  zoom_level: 13
  update_threshold_km: 1.0
```

## 🎮 Verwendung

### GPS-Daten senden

```bash
python SendPosition_improved.py
```

Startet den GPS-Sender, der Positionen aus der MAT-Datei als NMEA-Sätze sendet.

**Funktionen:**
- Lädt GPS-Daten aus MATLAB-Dateien
- Konvertiert zu NMEA RMC-Sätzen
- Sendet via UDP mit konfigurierbarem Intervall
- Vollständige Fehlerprotokollierung

### GPS-Daten empfangen und visualisieren

```bash
python ReceivePosition_improved.py
```

Startet die GUI-Anwendung zum Empfang und zur Visualisierung.

**Funktionen:**
- Empfängt und validiert NMEA-Daten
- Echtzeit-Positionsplot
- OpenStreetMap-Integration
- Statistiken und Tracking-Info
- Export zu Excel
- Thread-sichere Updates

### GUI-Bedienung

1. **Positionsanzeige**: Zeigt aktuelle Position auf Karte und im Plot
2. **Statistiken**: Anzeige von empfangenen Positionen, Distanz, Geschwindigkeit
3. **Save Data**: Speichert gesammelte Daten als Excel-Datei
4. **Clear Data**: Löscht alle gespeicherten Positionen
5. **Append Mode**: Checkbox zum Anhängen an bestehende Dateien

## 🏗️ Architektur

### Komponentenübersicht

```
gps-position-system/
├── config.yaml                    # Zentrale Konfiguration
├── config_loader.py              # Konfigurationsverwaltung
├── coordinates.py                # Koordinatensystem
├── nmea_validator.py            # NMEA-Validierung
├── gps_data_model.py           # Datenmodell (Model)
├── gps_data_mat_play_improved.py  # MAT-Datei-Player
├── SendPosition_improved.py    # GPS-Sender
├── ReceivePosition_improved.py # GPS-Empfänger (View + Controller)
├── test_gps_system.py         # Test-Suite
├── requirements.txt           # Python-Abhängigkeiten
└── README.md                 # Diese Datei
```

### MVC-Pattern

**Model** (`gps_data_model.py`):
- `GPSDataModel`: Thread-sichere Datenverwaltung
- `GPSPosition`: Einzelne Position mit Metadaten
- `GPSTrack`: Track-Analyse und Statistiken
- Observer-Pattern für Änderungsbenachrichtigungen

**View** (`ReceivePosition_improved.py`):
- `GPSPlotView`: Visualisierung im Plot
- `MapManager`: Kartendarstellung
- Qt-Widgets für UI-Elemente

**Controller** (`ReceivePosition_improved.py`):
- `ReceiveNmea`: Hauptcontroller
- Event-Handling und Datenfluss
- Signal/Slot-Kommunikation

## 🧪 Tests ausführen

### Alle Tests

```bash
pytest test_gps_system.py -v
```

### Mit Coverage-Report

```bash
pytest test_gps_system.py --cov=. --cov-report=html
```

### Einzelne Testklassen

```bash
pytest test_gps_system.py::TestCoordinates -v
pytest test_gps_system.py::TestNMEAValidator -v
pytest test_gps_system.py::TestGPSDataModel -v
```

## 📊 Code-Qualität

### Linting

```bash
# Flake8
flake8 *.py --max-line-length=100

# Pylint
pylint *.py

# MyPy (Type Checking)
mypy *.py
```

### Formatierung

```bash
# Black formatter
black *.py
```

## 🔍 API-Dokumentation

### Coordinates-Modul

```python
from coordinates import Coordinate, Position

# Koordinate erstellen
lat = Coordinate(48.1234, 'N')
lon = Coordinate(11.5678, 'E')

# Position erstellen
pos = Position.from_decimal(48.1234, 11.5678, 100.0)

# Distanz berechnen
pos1 = Position.from_decimal(48.0, 11.0)
pos2 = Position.from_decimal(48.1, 11.0)
distance = pos1.distance_to(pos2)  # in km

# NMEA-Format
nmea_lat = Coordinate.from_nmea('4807.404', 'N')
print(nmea_lat.decimal_degrees)  # 48.1234
```

### NMEA-Validator

```python
from nmea_validator import NMEAValidator, NMEAGenerator

# NMEA validieren
nmea_str = "$GPRMC,123456.00,A,4807.404,N,01131.324,E,0.0,0.0,191124,,,A*6C"
is_valid = NMEAValidator.is_valid_nmea(nmea_str)

# NMEA parsen
parsed = NMEAValidator.safe_parse(nmea_str)
if parsed:
    info = NMEAValidator.extract_position_info(parsed)
    print(info['latitude'], info['longitude'])

# NMEA generieren
nmea = NMEAGenerator.generate_rmc(48.1234, 11.5678)
```

### GPS-Datenmodell

```python
from gps_data_model import GPSDataModel, GPSPosition

# Model erstellen
model = GPSDataModel(max_positions=1000)

# Observer registrieren
def on_new_position(pos):
    print(f"New: {pos.latitude}, {pos.longitude}")

model.register_observer(on_new_position)

# Position hinzufügen
pos = GPSPosition(48.1234, 11.5678, 100.0)
model.add_position(pos)

# Statistiken abrufen
stats = model.get_statistics()
print(f"Total distance: {stats['total_distance']:.2f} m")
```

## ⚙️ Konfiguration

### Netzwerk-Einstellungen

```yaml
network:
  udp_address: "127.0.0.1"     # Ziel-IP-Adresse
  broadcast_address: "172.16.79.255"  # Broadcast-Adresse
  udp_port: 19711               # Ziel-Port
  receive_port: 19710           # Empfangs-Port
  timeout: 5.0                  # Timeout in Sekunden
```

### GPS-Einstellungen

```yaml
gps:
  data_file: "data/AguasVivasGPSData.mat"
  start_timeout: 5              # Startverzögerung
  time_between_positions: 1.0   # Intervall zwischen Positionen
  max_stored_positions: 1000    # Max. gespeicherte Positionen
```

### Karten-Einstellungen

```yaml
map:
  delta_lat: 0.075             # Kartenausschnitt Breite
  delta_lon: 0.15              # Kartenausschnitt Länge
  zoom_level: 13               # OSM Zoom-Level (0-19)
  update_threshold_km: 1.0     # Min. Distanz für Update
  cache_size: 100              # Anzahl gecachter Karten
```

### Logging-Einstellungen

```yaml
logging:
  level: "INFO"                # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "gps_system.log"
  max_bytes: 10485760          # 10MB
  backup_count: 5
```

## 🐛 Fehlerbehebung

### Problem: "ModuleNotFoundError"

**Lösung**: Stellen Sie sicher, dass alle Abhängigkeiten installiert sind:
```bash
pip install -r requirements.txt
```

### Problem: UDP-Pakete kommen nicht an

**Lösung**: 
1. Prüfen Sie Firewall-Einstellungen
2. Verifizieren Sie IP-Adresse und Port in `config.yaml`
3. Testen Sie mit Loopback (127.0.0.1) zuerst

### Problem: Karten werden nicht geladen

**Lösung**:
1. Prüfen Sie Internetverbindung
2. OSM-Server könnten temporär überlastet sein
3. User-Agent in `helper_maps.py` überprüfen

### Problem: GUI friert ein

**Lösung**: Das sollte mit der neuen Version nicht mehr passieren (Thread-Sicherheit). Falls doch:
1. Prüfen Sie Log-Dateien auf Fehler
2. Reduzieren Sie `max_stored_positions`
3. Erhöhen Sie `update_threshold_km`

## 📈 Performance-Tipps

1. **Begrenzen Sie gespeicherte Positionen**: `max_stored_positions: 500`
2. **Erhöhen Sie Karten-Update-Schwelle**: `update_threshold_km: 2.0`
3. **Reduzieren Sie Plot-Updates**: Längeres Intervall in `time_between_positions`
4. **Deaktivieren Sie Debug-Logging**: `level: "INFO"` statt `"DEBUG"`

## 🤝 Beitragen

Verbesserungen sind willkommen! Bitte:

1. Fork das Repository
2. Feature-Branch erstellen (`git checkout -b feature/AmazingFeature`)
3. Tests für neue Features hinzufügen
4. Code formatieren (`black *.py`)
5. Commit mit aussagekräftiger Nachricht
6. Push zum Branch
7. Pull Request öffnen

## 📝 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe LICENSE-Datei für Details.

## 👏 Credits

- NMEA-Parsing: pynmea2
- Kartendaten: OpenStreetMap Contributors
- GUI: PyQt6 Framework

## 📞 Support

Bei Fragen oder Problemen:
- GitHub Issues: [Link zum Repository]
- E-Mail: [Ihre E-Mail]
- Dokumentation: Siehe Code-Docstrings

## 🔄 Änderungsprotokoll

### Version 2.0.0 (Aktuell)

#### ✨ Neue Features
- MVC-Architektur implementiert
- Einheitliches Koordinatensystem
- NMEA-Validierung mit Checksummen
- Thread-sichere GUI-Updates
- Konfigurationsverwaltung
- Umfassende Test-Suite
- Strukturiertes Logging

#### 🔧 Verbesserungen
- Performance-Optimierungen
- Intelligentes Karten-Caching
- Observer-Pattern für Datenmodell
- Bessere Fehlerbehandlung
- Dokumentation vervollständigt

#### 🐛 Bugfixes
- Thread-Sicherheitsprobleme behoben
- NMEA-Generierung korrigiert
- Koordinaten-Konvertierung verbessert
- Speicherlecks eliminiert

### Version 1.0.0 (Original)
- Basis-Funktionalität
- UDP-Übertragung
- Einfache GUI
- MAT-Datei-Support
