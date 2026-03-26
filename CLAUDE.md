# CLAUDE.md – easyjob Timecard Integration

## Projekt-Überblick

Home Assistant Custom Integration für **protonic easyjob Timecard** und den easyjob Ressourcenplan (Kalender).

- Repo: https://github.com/forrohe93/easyjob-timecard-home-assistant-integration
- Aktuelle Version: **1.0.0**
- Quality Scale: **bronze**
- HA Mindestversion: 2025.6.0

---

## Architektur

### Dateistruktur

| Datei | Zweck |
|---|---|
| `api.py` | HTTP-Client (`EasyjobClient`), alle API-Calls, Token-Verwaltung |
| `coordinator.py` | `DataUpdateCoordinator` – zentrales Update, Daten-Cache |
| `config_flow.py` | Config Flow (Setup + Options + Reauth) |
| `const.py` | Alle Konstanten |
| `runtime.py` | `RuntimeData` Dataclass – verbindet Client + Coordinator |
| `__init__.py` | Setup/Unload, Entry-Migration, Reauth-Listener |
| `entity.py` | Basis-Entities mit `DeviceInfo` |
| `sensor.py` | Arbeitszeit-Sensoren |
| `binary_sensor.py` | Verbindung, Zeiterfassung aktiv, Ressourcenstatus |
| `button.py` | Start/Stop Buttons |
| `switch.py` | Zeiterfassungs-Switch |
| `select.py` | Ressourcenstatus-Auswahl |
| `calendar.py` | Ressourcenplan-Kalender |
| `services.py` | HA Service + WebSocket `set_resource_state` |
| `diagnostics.py` | HA Diagnose-Download |

### Datenfluss

```
EasyjobClient → EasyjobCoordinator → alle Entities (via CoordinatorEntity)
```

Alle Entities sind Coordinator-basiert (`PARALLEL_UPDATES = 0`). Es gibt keinen direkten API-Call pro Entity-Update.

---

## API-Versionen

Die Integration unterstützt zwei API-Versionen, wählbar im Config Flow:

| Konstante | Wert | Beschreibung |
|---|---|---|
| `API_VERSION_V1` | `"v1"` | Legacy, Standard für bestehende Installationen |
| `API_VERSION_V2` | `"v2"` | easyjob WebApi 6.0+, neue Endpoint-Struktur |
| `DEFAULT_API_VERSION` | `"v1"` | Fallback wenn kein Wert in `entry.data` |

### Versionsbewusste Methoden in `EasyjobClient`

- `async_fetch_details_versioned()` → ruft v1 oder v2 je nach `self.api_version`
- `async_start_versioned()` / `async_stop_versioned()` → analog
- `async_validate_timecard_user()` → v1: `GetWebSettings → IsTimeCardUser`, v2: `details → IdTimeCardUser > 0`

### v1 Endpoints

| Methode | Endpoint |
|---|---|
| Auth | `POST /token` |
| Details | `GET /api.json/Timecard/Details?d=` |
| Start | `POST /api.json/Timecard/StartWorkTime` |
| Stop | `POST /api.json/Timecard/CloseWorkTime` |
| Kalender | `GET /api.json/dashboard/calendar/` |
| WebSettings | `GET /api.json/Common/GetWebSettings` |
| GlobalWebSettings | `GET /api.json/Common/GetGlobalWebSettings` |
| ResourceStates FormData | `GET /api.json/ResourceStates/GetFormData` |
| ResourceStates Save | `POST /api.json/ResourceStates/Save` |

### v2 Endpoints (Timecard)

| Methode | Endpoint |
|---|---|
| Details | `GET /api.json/v2/timecard/common/details?light=false` |
| Start | `POST /api.json/v2/timecard/worktimes/start` |
| Stop | `POST /api.json/v2/timecard/worktimes/close` |
| Validate User | `GET /api.json/v2/timecard/common/details?light=true` |

### v2 Besonderheiten

- Kein `CurrentWorkTime`-Feld → `IdTimeCardWorkTimeCurrent > 0` bedeutet aktive Zeiterfassung
- `work_time` wird als `str({"ID": id_current})` gesetzt, damit der `work_time`-Sensor (`_parse_work_time` via `ast.literal_eval`) unverändert funktioniert
- Kalender und ResourceStates nutzen weiterhin v1-Endpoints (kein v2-Äquivalent in der API-Doku)

---

## Config Flow

### Steps (Setup)
1. `user` – URL, Username, Passwort, SSL, API-Version
2. `status` – Ressourcenstatus-Auswahl für Binary Sensors

### Steps (Options)
- `init` – alle Felder aus Setup + Status-Auswahl in einem Schritt

### Reauth Flow
- Ausgelöst durch `EasyjobAuthError` im Coordinator → `entry.async_start_reauth()`
- Step `reauth_confirm` – nur Username + Passwort, alle anderen Einstellungen bleiben erhalten

### Unique ID
Format: `{base_url_lower}|{username_lower}`

---

## Wichtige Designentscheidungen

- **`api_version` liegt in `entry.data`**, nicht in `entry.options` – ist eine Verbindungseinstellung, keine reine Verhaltens-Option
- **Coordinator kennt die Config Entry** (`self._entry`) – nötig für `async_start_reauth()`
- **`api_version` wird an `EasyjobClient` übergeben**, nicht an den Coordinator – so müssen Button/Switch/Select nichts von der Version wissen
- **`DeviceEntryType.SERVICE`** in `entity.py` – das Gerät ist ein Dienst, kein physisches Gerät
- **Kalender-Cache im Coordinator** – `calendar_items` wird bei jedem Update befüllt, Entities lesen nur lokal daraus (kein eigener Calendar-API-Call pro Request)

---

## Entry Migration

- Version 1 → 2: `unique_id` von `entry_id`-basiert auf `base_url|username` migriert
- Entity Registry und Device Registry werden entsprechend angepasst

---

## Quality Scale Bronze – Erfüllte Regeln

- `action-exceptions` ✅
- `config-entry-unloading` ✅
- `docs-configuration-parameters` ✅
- `docs-installation-parameters` ✅
- `entity-unavailable` ✅
- `integration-owner` ✅ (`@forrohe93`)
- `parallel-updates` ✅ (`PARALLEL_UPDATES = 0` in allen Platform-Dateien)
- `reauthentication-flow` ✅

### Noch offen (für Silver)
- `log-when-unavailable` – kein explizites "wieder verfügbar"-Log
- `test-coverage` – keine automatisierten Tests vorhanden (95% Coverage für Silver nötig)
