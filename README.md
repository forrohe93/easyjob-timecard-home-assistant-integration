# easyjob Timecard – Home Assistant Integration

Diese Custom Integration bindet **protonic easyjob Timecard** und den **easyjob Ressourcenplan (Kalender)** in Home Assistant ein.  
Damit kannst du deine Arbeitszeit direkt in Home Assistant sehen **und starten/stoppen** – inklusive Kalender-Einträgen wie z. B. **Urlaub** oder **Mobile Office**.

Die Integration unterstützt **mehrere Benutzer** (z. B. mehrere Personen im Haushalt mit derselben Firma).

---

## ✨ Features

- 🔐 Login über easyjob OAuth Token (`/token`)
- 📊 Arbeitszeit-Sensoren (Minuten werden als **Ganzzahl** angezeigt)
- ▶️⏹ Start & Stop der Zeiterfassung über Buttons
- 🔄 Automatische Aktualisierung via DataUpdateCoordinator
- 🩺 Diagnose-Sensor für Verbindungsstatus (**Verbunden**)
- 🧩 Binary Sensor: **Zeiterfassung aktiv** (on/off, Icon abhängig vom Status)
- 🗓️ **Kalender-Entity**: easyjob Ressourcenplan (z. B. Urlaub, Mobile Office)
  - inkl. Attribut **`event_color`** (HEX-Farbwert des aktuellen/nächsten Events)
- 🔧 Konfigurierbar über UI (inkl. Passwort ändern & SSL-Verify)
- 🏠 Volle Home-Assistant-UI-Integration (Config Flow & Options Flow)

---

## 📦 Installation

### Manuell

1. Kopiere den Ordner `easyjob_timecard` nach:
   ```
   config/custom_components/
   ```

2. Home Assistant **neu starten**

3. Integration hinzufügen:
   - **Einstellungen → Geräte & Dienste → Integration hinzufügen**
   - nach **easyjob Timecard** suchen

---

## ⚙️ Konfiguration

Die Konfiguration erfolgt **vollständig über die UI**.

### Benötigte Daten

| Feld | Beschreibung |
|-----|-------------|
| easyjob URL | Basis-URL deiner easyjob-Instanz |
| Benutzername | easyjob Benutzername |
| Passwort | easyjob Passwort |
| SSL-Zertifikat prüfen | Deaktivieren bei Self-Signed Zertifikaten |

👉 Änderungen (z. B. neues Passwort oder SSL-Verify) können später über  
**Integration → Konfigurieren** vorgenommen werden.

---

## 📊 Entitäten

### Sensoren

| Sensor | Beschreibung |
|------|-------------|
| Holidays | Urlaubstage (Zähler) |
| Work Minutes | Gearbeitete Minuten heute |
| Work Minutes geplant | Geplante Minuten |
| Total Work Minutes | Gesamtarbeitszeit |
| Work Time | Aktuelle laufende WorkTime (falls vorhanden) |

> Hinweis: Minuten-Werte werden als **Ganzzahl** ausgegeben.

---

### Binary Sensoren

| Binary Sensor | Bedeutung |
|--------------|----------|
| **Verbunden** | Technische Verbindung zur API ok (Diagnose) |
| **Zeiterfassung aktiv** | Zeiterfassung läuft aktuell (work_time != null) |

---

### Buttons

| Button | Aktion |
|------|-------|
| Start | Startet die Zeiterfassung |
| Stop | Beendet die Zeiterfassung |

---

### Kalender

| Entity | Beschreibung |
|-------|-------------|
| **Ressourcenplan** (`calendar.*`) | Kalender aus `/api.json/dashboard/calendar` (z. B. Urlaub, Mobile Office) |

**Kalender-Attribute**
- `event_color`: HEX-Farbwert (z. B. `#FF0000`) des aktuellen/nächsten Events (entspricht dem `event`/State des Kalenders)

---

## 🧪 Diagnose

Der Binary Sensor **„Verbunden“** ist als *Diagnose-Entity* markiert und erscheint im Geräte-Dialog unter **Diagnose**.

Er zeigt an, ob:
- Authentifizierung erfolgreich war (Token gültig)
- API erreichbar ist
- der letzte Datenabruf erfolgreich war

---

## 🖼️ Lovelace Beispielkarten

### Arbeitszeit (Status + Buttons)

```yaml
type: vertical-stack
cards:
  - type: heading
    heading: Timecard
    icon: mdi:clock-check-outline

  - type: entities
    title: Status
    entities:
      - binary_sensor.easyjob_heiko_connected
      - binary_sensor.easyjob_heiko_worktime_active
      - sensor.easyjob_heiko_work_minutes
      - sensor.easyjob_heiko_work_minutes_planed
      - sensor.easyjob_heiko_total_work_minutes
      - sensor.easyjob_heiko_holidays

  - type: horizontal-stack
    cards:
      - type: button
        entity: button.easyjob_heiko_start
        name: Start
        icon: mdi:play

      - type: button
        entity: button.easyjob_heiko_stop
        name: Stop
        icon: mdi:stop
```

(Entity-IDs ggf. anpassen)

### Ressourcenplan (Kalender)

```yaml
type: calendar
entities:
  - calendar.easyjob_heiko_ressourcenplan
```

> Tipp: Das Attribut `event_color` kannst du z. B. in Templates oder Custom Cards verwenden, um Events farblich zu markieren.

---

## 🔒 Sicherheit

- Passwörter werden ausschließlich lokal in Home Assistant gespeichert
- Kommunikation erfolgt über HTTPS (SSL-Verify optional deaktivierbar)
- Tokens werden automatisch erneuert

---

## 🛠️ Technisches

- Implementiert mit `DataUpdateCoordinator`
- Async via `aiohttp`
- Token-Caching mit Ablaufzeit
- Retry bei 401 (Token Refresh)
- Kalender: `CalendarEntity` mit `async_update()` + `async_get_events()`

---

## 🚧 Bekannte Einschränkungen

- Keine Offline-Pufferung
- API-Verfügbarkeit abhängig von easyjob-Server
- Standard Home-Assistant Kalenderkarte nutzt `event_color` nicht automatisch (für farbige Darstellung ggf. Custom Card nötig)
- Änderungen in der easyjob API können Anpassungen erfordern

---

## 📄 Lizenz

MIT License

---

## 🤝 Mitmachen

Pull Requests und Issues sind willkommen 🙂  
Bitte beschreibe bei Fehlern:
- Home-Assistant-Version
- easyjob-Version (falls bekannt)
- relevante Log-Auszüge
