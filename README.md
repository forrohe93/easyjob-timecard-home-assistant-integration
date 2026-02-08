# easyjob Timecard – Home Assistant Integration

Diese Custom Integration bindet **protonic easyjob Timecard** in Home Assistant ein.  
Damit kannst du deine Arbeitszeit direkt in Home Assistant sehen **und starten/stoppen**.

Die Integration unterstützt **mehrere Benutzer** (z. B. mehrere Personen im Haushalt mit derselben Firma).

---

## ✨ Features

- 🔐 Login über easyjob OAuth Token (`/token`)
- 📊 Arbeitszeit-Sensoren
- ▶️⏹ Start & Stop der Zeiterfassung über Buttons
- 🔄 Automatische Aktualisierung via DataUpdateCoordinator
- 🩺 Diagnose-Sensor für Verbindungsstatus
- 🧩 Binary Sensor: *Zeiterfassung aktiv*
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

👉 Änderungen (z. B. neues Passwort) können später über  
**Integration → Konfigurieren** vorgenommen werden.

---

## 📊 Entitäten

### Sensoren

| Sensor | Beschreibung |
|------|-------------|
| Datum | Aktuelles Datum |
| Work Minutes | Gearbeitete Minuten heute |
| Work Minutes geplant | Geplante Minuten |
| Total Work Minutes | Gesamtarbeitszeit |
| Holidays | Urlaubstage |
| Work Time | Aktuelle laufende Zeit (falls vorhanden) |

---

### Binary Sensoren

| Binary Sensor | Bedeutung |
|--------------|----------|
| **Verbunden** | Technische Verbindung zur API ok (Diagnose) |
| **Zeiterfassung aktiv** | Zeiterfassung läuft aktuell |

---

### Buttons

| Button | Aktion |
|------|-------|
| Start | Startet die Zeiterfassung |
| Stop | Beendet die Zeiterfassung |

---

## 🧪 Diagnose

Der Binary Sensor **„Verbunden“** ist als *Diagnose-Entity* markiert und erscheint im Geräte-Dialog unter **Diagnose**.

Er zeigt an, ob:
- Authentifizierung erfolgreich war
- API erreichbar ist
- der letzte Datenabruf erfolgreich war

---

## 🖼️ Lovelace Beispielkarte

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

  - type: horizontal-stack
    cards:
      - type: button
        entity: button.easyjob_heiko_start
        icon: mdi:play
      - type: button
        entity: button.easyjob_heiko_stop
        icon: mdi:stop
```

(Entity-IDs ggf. anpassen)

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
- Home-Assistant-Standards konform

---

## 🚧 Bekannte Einschränkungen

- Keine Offline-Pufferung
- API-Verfügbarkeit abhängig von easyjob-Server
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
