
# easyjob Timecard – Home Assistant Integration

Diese Integration verbindet **protonic easyjob Timecard** und den **easyjob Ressourcenplan (Kalender)** mit Home Assistant.

Du kannst:
- Deine aktuelle Arbeitszeit sehen
- Die Zeiterfassung direkt starten und stoppen
- Urlaube, Kranktage oder Mobile Office als Status anzeigen
- Den Ressourcenplan als Kalender einbinden

Mehrere Benutzer werden unterstützt.

> **Version 1.0.0** – Erster stabiler Release. Neu: Unterstützung für easyjob WebApi v2, automatischer Reauth-Flow bei ungültigen Zugangsdaten.

---

## ✨ Funktionen

- Login über easyjob
- Arbeitszeit-Sensoren (Minuten als Ganzzahl)
- Start- und Stop-Button für Zeiterfassung
- Kalender-Entity (Ressourcenplan)
- Status-Binary-Sensoren (z. B. Urlaub, Krank, Mobile Office)
- Verbindungsstatus-Sensor
- Vollständig über die Home-Assistant-UI konfigurierbar

---

## 📦 Installation

### Über HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=forrohe93&repository=easyjob-timecard-home-assistant-integration&category=Integration)

### Manuell

1. Ordner `easyjob_timecard` nach `config/custom_components/` kopieren
2. Home Assistant neu starten
3. Integration hinzufügen:
   - **Einstellungen → Geräte & Dienste → Integration hinzufügen**
   - nach **easyjob Timecard** suchen

---

## ⚙️ Einrichtung

Die Konfiguration erfolgt vollständig über die UI.

Benötigt werden:
- easyjob URL
- Benutzername
- Passwort
- Optional: SSL-Zertifikatsprüfung deaktivieren (bei Self-Signed Zertifikaten)

### API-Version auswählen

Bei der Einrichtung kannst du zwischen **v1** und **v2** wählen:

- **v1** – Für ältere easyjob-Installationen. Standard, wenn du dir nicht sicher bist.
- **v2** – Für aktuelle Installationen ab easyjob WebApi 6.0.

Die Version kann jederzeit über die Einstellungen der Integration geändert werden. Ein Neustart von Home Assistant ist dafür nicht nötig.

### Status-Sensoren auswählen

Während der Einrichtung kannst du auswählen, für welche Ressourcenstati eigene Binary-Sensoren erstellt werden sollen (z. B. Urlaub, Krank, Mobile Office).

Ein Status-Sensor ist **Ein**, wenn der entsprechende Eintrag im Ressourcenplan aktuell aktiv ist.

Wird ein Status später entfernt, wird die Entität automatisch aus Home Assistant gelöscht.

---

## 📊 Entitäten

### Sensoren

- **Work Minutes** – Gearbeitete Minuten heute
- **Work Minutes geplant** – Geplante Minuten
- **Total Work Minutes** – Gesamtarbeitszeit
- **Work Time** – Aktuelle laufende Zeit
- **Holidays** – Urlaubstage

---

### Binary-Sensoren

- **Verbunden** – API erreichbar
- **Zeiterfassung aktiv** – Zeiterfassung läuft aktuell
- **Status aktiv: <Name>** – Gewählter Status ist aktuell aktiv

---

### Buttons

- **Start** – Startet die Zeiterfassung
- **Stop** – Stoppt die Zeiterfassung

---

### Kalender

- **Ressourcenplan** (`calendar.*`)

Attribut:
- `event_color` – HEX-Farbwert des aktuellen oder nächsten Events

---

## 🖼️ Beispiel Lovelace

### Arbeitszeit

```yaml
type: entities
title: Timecard
entities:
  - binary_sensor.easyjob_heiko_worktime_active
  - sensor.easyjob_heiko_work_minutes
  - sensor.easyjob_heiko_total_work_minutes
  - button.easyjob_heiko_start
  - button.easyjob_heiko_stop
```

### Kalender

```yaml
type: calendar
entities:
  - calendar.easyjob_heiko_ressourcenplan
```

(Entity-IDs ggf. anpassen)

---

## 🔒 Sicherheit

- Zugangsdaten bleiben lokal in Home Assistant
- HTTPS-Unterstützung
- Keine externe Cloud notwendig

---

## 🚧 Hinweise

- Funktion abhängig von der easyjob-API
- Standard-Kalenderkarte nutzt `event_color` nicht automatisch für Farben

---

## 📄 Lizenz

MIT License
