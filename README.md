# Fronius Smart Meter Emulator (Home Assistant Custom Integration)

Liest die aktuelle PV-Erzeugung eines Fronius-Wechselrichters über die **Fronius
Solar API** aus und stellt sie über einen emulierten **Fronius Smart Meter**
(Modbus TCP, SunSpec Model 213) im Netzwerk bereit. Die Fronius Wallbox (z. B.
Flex Home 22) verbindet sich wie mit einem echten Smart Meter und kann so
PV-geführt laden, ohne dass ein physischer Zähler vorhanden sein muss.

> ⚠️ Dies ist eine inoffizielle, community-basierte Nachbildung des Fronius
> Smart-Meter-Protokolls (SunSpec Modbus Map, Model 213). Es besteht keine
> Verbindung zu oder Unterstützung durch die Fronius International GmbH. Vor dem
> produktiven Einsatz unbedingt mit der eigenen Wallbox/dem eigenen
> Datamanager testen.

## Funktionsweise

1. Ein `DataUpdateCoordinator` fragt periodisch
   `http://<Fronius-Host>/solar_api/v1/GetPowerFlowRealtimeData.fcgi` ab.
2. Der ausgewählte Wert (`P_PV` oder `P_Grid`) wird in die entsprechenden
   SunSpec-Register (u. a. `Total Real Power`, Register 40097) eines
   simulierten dreiphasigen Smart Meters geschrieben.
3. Ein integrierter Modbus-TCP-Server hält diese Register bereit. Die Wallbox
   (oder der Datamanager) wird als "Zähler via Modbus TCP" auf die IP der
   Home-Assistant-Instanz und den konfigurierten Port konfiguriert.

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
2. Host/IP des Fronius Wechselrichters bzw. Datamanagers angeben (dort muss
   die Solar API erreichbar sein, standardmäßig ist sie das).
3. Modbus-TCP-Port für den emulierten Zähler wählen (Standard: `1502`, siehe
   Hinweis zu Port 502 unten).
4. Auf der Wallbox bzw. im Fronius Datamanager unter den Zähler-Einstellungen
   "Zähler via Modbus TCP" mit der IP der Home-Assistant-Instanz und dem
   gewählten Port eintragen.

Über die Optionen der Integration lassen sich später anpassen: Abfrageintervall,
Bind-Adresse/Port des Modbus-Servers, Quelle (`P_PV`/`P_Grid`) und Vorzeichen.

## Hinweis zu Port 502

Fronius-Geräte adressieren Zähler standardmäßig auf Modbus-Port `502`. Dieser
Port ist privilegiert (< 1024) und lässt sich je nach Home-Assistant-Setup
(Container-Rechte) nicht immer direkt binden. Die Integration verwendet daher
standardmäßig Port `1502` – die meisten Fronius-Geräte erlauben, bei der
Zähler-Konfiguration einen abweichenden Port anzugeben. Falls nicht, kann per
Portweiterleitung (z. B. `iptables`/Router) von `502` auf `1502` umgeleitet
werden, oder Home Assistant mit der Fähigkeit `CAP_NET_BIND_SERVICE` bzw. als
root betrieben werden, um Port `502` direkt zu binden.

## Vorzeichen-Konvention

Ein SunSpec-Zähler meldet Leistung mit Vorzeichen: **positiv = Bezug aus dem
Netz, negativ = Einspeisung/Überschuss**. Die Integration invertiert `P_PV`
standardmäßig (`invert_sign = true`), damit die volle PV-Erzeugung der Wallbox
als verfügbarer Überschuss erscheint. Falls stattdessen `P_Grid` (bereits
vorzeichenrichtig von der Fronius Solar API geliefert) verwendet werden soll,
Inversion in den Optionen deaktivieren und Verhalten am Hausanschluss
verifizieren – abhängig von der Fronius-Firmware-Version kann sich die
Vorzeichenkonvention von `P_Grid` unterscheiden.

## Registerkarte (zur Fehlersuche)

Basis-Adresse `40000` ("SunS"-Marker), Common Block (Model 1) ab `40002`,
Meter Block (Model 213, float) ab `40069`, Nutzleistung gesamt
(`Total Real Power`) bei Register `40097`–`40098`. Vollständige Belegung siehe
[`custom_components/fronius_meter_emulator/sunspec.py`](custom_components/fronius_meter_emulator/sunspec.py).

## Bekannte Einschränkungen

- Spannungen/Frequenz/Leistungsfaktor sind feste Nominalwerte (230 V/400 V,
  50 Hz, PF 1.0) – die Fronius Solar API liefert keine Phasenwerte.
- Die Gesamtleistung wird gleichmäßig auf die drei simulierten Phasen
  aufgeteilt.
- Energiezähler (Wh-Total) werden aktuell nicht befüllt.

## Vor dem Veröffentlichen

`manifest.json` enthält Platzhalter (`@your-github-username`,
`github.com/your-github-username/...`) für `codeowners`/`documentation` –
bitte vor einer Veröffentlichung durch die eigenen Angaben ersetzen.
