# Fronius Smart Meter Emulator (Home Assistant Custom Integration)

Stellt den aktuellen Wert einer bereits in Home Assistant vorhandenen
PV-Erzeugungs-Entity (z. B. eines Template-Sensors/Helpers) über einen
emulierten **Fronius Solar API HTTP-Server** im Netzwerk bereit. Die Fronius
Wallbox (z. B. Flex Home 22) kann darauf wie auf einen echten Fronius
Datamanager zugreifen und PV-geführt laden – auch ohne dass ein Fronius
Wechselrichter vorhanden ist.

> ⚠️ Dies ist eine inoffizielle, community-basierte Nachbildung der lokalen
> Fronius Solar API auf Basis der öffentlich dokumentierten JSON-Struktur. Es
> besteht keine Verbindung zu oder Unterstützung durch die Fronius
> International GmbH. Unbedingt vor dem produktiven Einsatz mit der eigenen
> Wallbox testen – siehe Hinweis "Bekannte Unsicherheiten" unten.

## Funktionsweise

1. Sie wählen bei der Einrichtung eine bestehende Home-Assistant-Entity aus,
   die die aktuelle PV-Erzeugungsleistung liefert (z. B. ein Template-Sensor,
   der aus vorhandenen Werten berechnet wird).
2. Die Integration reagiert auf Zustandsänderungen dieser Entity (kein
   Polling) und hält den Wert für einen eingebauten HTTP-Server bereit.
3. Der HTTP-Server beantwortet Anfragen unter denselben Pfaden wie ein echter
   Fronius Datamanager:
   - `GET /solar_api/GetAPIVersion.cgi`
   - `GET /solar_api/v1/GetPowerFlowRealtimeData.fcgi` (liefert `Body.Data.Site.P_PV`)
4. Die Wallbox wird so konfiguriert, dass sie die IP der Home-Assistant-Instanz
   (und den gewählten Port) als Datenquelle verwendet.

## Installation

### Über HACS (custom repository)
1. HACS → Integrationen → ⋮ → Benutzerdefinierte Repositories.
2. Dieses Repository als Typ "Integration" hinzufügen.
3. "Fronius Smart Meter Emulator" installieren, Home Assistant neu starten.

### Manuell
`custom_components/fronius_meter_emulator` in das `custom_components`-Verzeichnis
der Home-Assistant-Konfiguration kopieren und Home Assistant neu starten.

## Einrichtung

1. Einstellungen → Geräte & Dienste → Integration hinzufügen → "Fronius Smart
   Meter Emulator".
2. Die Entity auswählen, die Ihre PV-Erzeugungsleistung enthält (Einheit `W`
   oder `kW`, beides wird automatisch umgerechnet).
3. HTTP-Port wählen (Standard: `8080`).
4. Auf der Wallbox die IP der Home-Assistant-Instanz (ggf. mit Port, falls die
   Wallbox das unterstützt) als Fronius-Datenquelle eintragen.

Über die Optionen der Integration lassen sich Bind-Adresse und Port später
anpassen.

## Bekannte Unsicherheiten

Fronius dokumentiert nicht öffentlich, wie genau die Wallbox einen
Datamanager im lokalen Netz anspricht (z. B. ob zusätzlich zu
`GetPowerFlowRealtimeData.fcgi` weitere Endpunkte, ein bestimmter Port oder
eine Discovery per mDNS/UPnP erwartet werden). Diese Integration implementiert
die zwei am häufigsten benötigten, öffentlich dokumentierten Solar-API-Aufrufe.

**Falls die Wallbox den emulierten Server nicht erkennt:** Bitte den
tatsächlichen Request der Wallbox mitschneiden (z. B. Netzwerk-Mitschnitt am
Router, oder die Zugriffe im Home-Assistant-Log/`aiohttp`-Access-Log prüfen)
und mir den angefragten Pfad mitteilen – dann kann der Server entsprechend
erweitert werden.

## Registerdaten, die aktuell nicht befüllt werden

`P_Grid`, `P_Load`, `P_Akku`, `rel_Autonomy`, `rel_SelfConsumption` sowie die
Energiezähler werden als `null` gemeldet, da keine entsprechende Datenquelle
vorhanden ist. Nur `P_PV` wird aus der ausgewählten Entity befüllt.

## Vor dem Veröffentlichen

`manifest.json` enthält Platzhalter (`@your-github-username`,
`github.com/your-github-username/...`) für `codeowners`/`documentation` –
bitte vor einer Veröffentlichung durch die eigenen Angaben ersetzen.
