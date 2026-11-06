
# easyjob Timecard – Home Assistant Integration

Diese Integration verbindet **protonic easyjob Timecard** und den **easyjob Ressourcenplan (Kalender)** mit Home Assistant.

Du kannst:
- Deine aktuelle Arbeitszeit sehen
- Die Zeiterfassung direkt starten und stoppen
- Urlaube, Kranktage oder Mobile Office als Status anzeigen
- Den Ressourcenplan als Kalender einbinden

Mehrere Benutzer werden unterstützt.

> **Version 1.0.3** – Kompatibilität mit Home Assistant 2026.11: Die Integration ließ sich nicht mehr laden, weil die englische Übersetzungsdatei ungültige Werte (`required: true`) im Service-Abschnitt enthielt.

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

## 🤖 Blueprint: Zeiterfassung automatisch starten/stoppen

[![Blueprint importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Fforrohe93%2Feasyjob-timecard-home-assistant-integration%2Fblob%2Fmain%2Fblueprints%2Fautomations%2Feasyjob_worktime_auto.yaml)

Startet die Zeiterfassung, sobald mindestens einer der gewählten Auslöser zutrifft, und stoppt sie, wenn keiner mehr zutrifft:

- **Zonen** – eine Person befindet sich in einer der gewählten Zonen
- **Smarthome-Auslöser** – z. B. ein Home-Office-Schalter, Input Boolean, Binary Sensor oder Zeitplan ist `an`
- **Ressourcenstatus** – laut easyjob-Kalender gilt gerade ein gewählter Status (die Status müssen in den Optionen der Integration als Binary Sensoren aktiviert sein). Optional mit **zusätzlicher Bedingung**: Der Status zählt dann nur, solange z. B. auch der PC eingeschaltet ist oder im Arbeitszimmer Präsenz erkannt wird.

Optional: Pause-Schalter zum vorübergehenden Deaktivieren, Start/Stopp einzeln abschaltbar, Stopp-Verzögerung gegen GPS-Sprünge am Zonenrand.

**Benachrichtigungen:** Ein Gerät mit der Companion App kann informiert werden, wenn die Zeiterfassung gestartet oder gestoppt wurde. Pro Auslöser-Art (Zonen, Smarthome-Auslöser, Ressourcenstatus) lässt sich außerdem „Nachfragen“ aktivieren – dann kommt eine Benachrichtigung mit **Ja/Nein**, und die Aktion wird erst nach „Ja“ ausgeführt.

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
