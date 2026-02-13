# easyjob Timecard -- Home Assistant Integration

Diese Custom Integration bindet **protonic easyjob Timecard** und den
**easyjob Ressourcenplan (Kalender)** in Home Assistant ein. Damit
kannst du deine Arbeitszeit direkt in Home Assistant sehen **und
starten/stoppen** -- inklusive Kalender-Einträgen wie z. B. **Urlaub**,
**Mobile Office** oder **Krank**.

Die Integration unterstützt **mehrere Benutzer** (z. B. mehrere Personen
im Haushalt mit derselben Firma).

------------------------------------------------------------------------

## ✨ Features

-   🔐 Login über easyjob OAuth Token (`/token`)
-   📊 Arbeitszeit-Sensoren (Minuten werden als **Ganzzahl** angezeigt)
-   ▶️⏹ Start & Stop der Zeiterfassung über Buttons
-   🔄 Automatische Aktualisierung via `DataUpdateCoordinator`
-   🩺 Diagnose-Sensor für Verbindungsstatus (**Verbunden**)
-   🧩 Binary Sensor: **Zeiterfassung aktiv** (on/off, Icon abhängig vom
    Status)
-   🗓️ **Kalender-Entity**: easyjob Ressourcenplan
    -   inkl. Attribut **`event_color`** (HEX-Farbwert des
        aktuellen/nächsten Events)
    -   Daten werden über den Coordinator gecacht (keine separaten
        API-Calls pro Kalender-Update)
-   🆕 **Dynamische Status-Binary-Sensoren**
    -   Frei auswählbar im Config-/Options-Flow
    -   Ein Sensor pro ausgewähltem Ressourcenstatus (z. B. Urlaub,
        Krank, Mobile Office)
    -   Sensor ist **„Ein"**, wenn der Status aktuell aktiv ist
    -   Automatische Bereinigung bei Entfernen im Options Flow
-   🔧 Konfigurierbar über UI (inkl. Passwort ändern & SSL-Verify)
-   🏠 Volle Home-Assistant-UI-Integration (Config Flow & Options Flow)

------------------------------------------------------------------------

## 📦 Installation

### Über HACS

[![Open your Home Assistant instance and open a repository inside the
Home Assistant Community
Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=forrohe93&repository=easyjob-timecard-home-assistant-integration&category=Integration)

### Manuell

1.  Kopiere den Ordner `easyjob_timecard` nach:

```{=html}
<!-- -->
```
    config/custom_components/

2.  Home Assistant **neu starten**

3.  Integration hinzufügen:

    -   **Einstellungen → Geräte & Dienste → Integration hinzufügen**
    -   nach **easyjob Timecard** suchen

------------------------------------------------------------------------

## ⚙️ Konfiguration

Die Konfiguration erfolgt **vollständig über die UI**.

### Benötigte Daten

  Feld                    Beschreibung
  ----------------------- -------------------------------------------
  easyjob URL             Basis-URL deiner easyjob-Instanz
  Benutzername            easyjob Benutzername
  Passwort                easyjob Passwort
  SSL-Zertifikat prüfen   Deaktivieren bei Self-Signed Zertifikaten

### Status-Binary-Sensoren auswählen

Während der Einrichtung (oder später über **Konfigurieren**) kannst du
auswählen:

> **„Ressourcenstati für Binärsensoren"**

Für jeden ausgewählten Status wird ein eigener Binary Sensor angelegt.

Beispiel:

-   Urlaub → `binary_sensor.easyjob_<name>_status_active_urlaub`
-   Mobile Office → eigener Sensor
-   Krank → eigener Sensor

Wird ein Status später abgewählt:

-   wird die zugehörige Entität automatisch aus Home Assistant entfernt
-   sie bleibt nicht „unavailable" zurück

------------------------------------------------------------------------

## 📊 Entitäten

### Sensoren

  Sensor                 Beschreibung
  ---------------------- ----------------------------------------------
  Holidays               Urlaubstage (Zähler)
  Work Minutes           Gearbeitete Minuten heute
  Work Minutes geplant   Geplante Minuten
  Total Work Minutes     Gesamtarbeitszeit
  Work Time              Aktuelle laufende WorkTime (falls vorhanden)

> Hinweis: Minuten-Werte werden als **Ganzzahl** ausgegeben.

------------------------------------------------------------------------

### Binary Sensoren

  -----------------------------------------------------------------------
  Binary Sensor             Bedeutung
  ------------------------- ---------------------------------------------
  **Verbunden**             Technische Verbindung zur API ok (Diagnose)

  **Zeiterfassung aktiv**   Zeiterfassung läuft aktuell

  **Status aktiv:           Gewählter Ressourcenstatus ist aktuell aktiv
  `<Name>`{=html}**         
  -----------------------------------------------------------------------

#### Status-Sensor Logik

Ein Status-Binary-Sensor ist **„Ein"**, wenn:

-   ein entsprechender Eintrag im Ressourcenplan existiert
-   dessen Zeitraum das aktuelle Datum/Uhrzeit einschließt

Die Zuordnung erfolgt robust über:

-   Status-ID
-   oder Status-Bezeichnung (Caption)

------------------------------------------------------------------------

### Buttons

  Button   Aktion
  -------- ---------------------------
  Start    Startet die Zeiterfassung
  Stop     Beendet die Zeiterfassung

------------------------------------------------------------------------

### Kalender

  -----------------------------------------------------------------------
  Entity                         Beschreibung
  ------------------------------ ----------------------------------------
  **Ressourcenplan**             Kalender aus
  (`calendar.*`)                 `/api.json/dashboard/calendar`

  -----------------------------------------------------------------------

**Kalender-Attribute**

-   `event_color` → HEX-Farbwert des aktuellen/nächsten Events
-   zeigt das nächste oder aktuell laufende Event

Der Kalender verwendet den globalen `DataUpdateCoordinator`-Cache. Es
werden keine separaten API-Aufrufe pro Kalender-Update durchgeführt.

------------------------------------------------------------------------

## 🧪 Diagnose

Der Binary Sensor **„Verbunden"** ist als *Diagnose-Entity* markiert.

Er zeigt an, ob:

-   Authentifizierung erfolgreich war
-   API erreichbar ist
-   letzter Datenabruf erfolgreich war

------------------------------------------------------------------------

## 🖼️ Lovelace Beispielkarten

### Arbeitszeit (Status + Buttons)

``` yaml
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
      - binary_sensor.easyjob_heiko_status_active_urlaub
      - binary_sensor.easyjob_heiko_status_active_mobile_office
      - sensor.easyjob_heiko_work_minutes
      - sensor.easyjob_heiko_total_work_minutes

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

------------------------------------------------------------------------

### Ressourcenplan (Kalender)

``` yaml
type: calendar
entities:
  - calendar.easyjob_heiko_ressourcenplan
```

------------------------------------------------------------------------

## 🔒 Sicherheit

-   Passwörter werden ausschließlich lokal in Home Assistant gespeichert
-   Kommunikation erfolgt über HTTPS (SSL-Verify optional deaktivierbar)
-   Tokens werden automatisch erneuert
-   Keine externen Cloud-Abhängigkeiten

------------------------------------------------------------------------

## 🛠️ Technisches

-   Implementiert mit `DataUpdateCoordinator`
-   Async via `aiohttp`
-   Token-Caching mit Ablaufzeit
-   Retry bei 401 (Token Refresh)
-   Kalender-Cache mit Lookahead
-   Dynamische Entity-Erstellung basierend auf Options Flow
-   Automatische Bereinigung entfernter dynamischer Entities

------------------------------------------------------------------------

## 🚧 Bekannte Einschränkungen

-   Keine Offline-Pufferung
-   API-Verfügbarkeit abhängig vom easyjob-Server
-   Standard Home-Assistant Kalenderkarte nutzt `event_color` nicht
    automatisch (für farbige Darstellung ggf. Custom Card nötig)
-   Änderungen in der easyjob API können Anpassungen erfordern

------------------------------------------------------------------------

## 📄 Lizenz

MIT License

------------------------------------------------------------------------

## 🤝 Mitmachen

Pull Requests und Issues sind willkommen 🙂

Bitte beschreibe bei Fehlern:

-   Home-Assistant-Version
-   easyjob-Version (falls bekannt)
-   relevante Log-Auszüge
