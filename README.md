# Fronius Smart Meter Emulator (Home Assistant Custom Integration)

Emuliert ein Fronius-System (Solar API über HTTP + optional Smart Meter IP
über Modbus TCP, beides per mDNS im Netzwerk angekündigt), damit eine Fronius
Wattpilot PV-Überschussladen gegen eine Home-Assistant-Entity durchführen
kann – auch ohne echte Fronius-Hardware.

> ⚠️ Dies ist eine inoffizielle, community-basierte Nachbildung interner
> Fronius-Protokolle. Es besteht keine Verbindung zu oder Unterstützung durch
> die Fronius International GmbH.

**Danksagung:** Die mDNS-Ankündigung, das Modbus-Register-Layout und die
Solar-API-Endpunkte sind portiert von
[l2smith2/fronius-virtual-inverter](https://github.com/l2smith2/fronius-virtual-inverter)
(MIT-Lizenz), das genau dieses Verhalten aus echtem Netzwerkverkehr
zurückentwickelt und gegen reale Wattpilot-Hardware (Firmware 42.5) getestet
hat. Ohne dieses Referenzprojekt wäre insbesondere die proprietäre
"Fronius-SE" mDNS-Ankündigung (nötig, damit die Wattpilot das emulierte
Gerät überhaupt findet) nicht zu erraten gewesen.

## Funktionsweise

1. Sie wählen bei der Einrichtung eine bestehende Home-Assistant-Entity aus,
   die Ihren aktuellen **Netto-Überschusswert** liefert (Erzeugung minus
   Hausverbrauch – nicht nur die reine PV-Erzeugung, siehe unten).
2. Die Integration reagiert auf Zustandsänderungen dieser Entity (kein
   Polling) und hält den Wert für zwei parallel laufende Server bereit:
   - **HTTP-Server**, der die Fronius Solar API v1 nachbildet
     (`GetPowerFlowRealtimeData.fcgi` u. a.), Standardport `80`.
   - **Modbus-TCP-Server**, der einen Fronius Smart Meter IP (SunSpec Model
     213, Unit-ID `240`) nachbildet, Standardport `502`. Kann in den
     Einstellungen deaktiviert werden.
3. Beide Server kündigen sich per mDNS im lokalen Netz an, damit die Wattpilot
   sie automatisch findet:
   - Standard-Bonjour (`_http._tcp.local.`) über Home Assistants eigene
     Zeroconf-Instanz.
   - Die proprietäre Fronius-Ankündigung
     (`_Fronius-SE-Inverter._tcp.local.` / `_Fronius-SE-SmartMeter._tcp.local.`)
     per selbst gebauten UDP-Multicast-Paketen (da Fronius hier ein Format
     jenseits der Standard-Zeroconf-Limits nutzt).

## Vorzeichen-Konvention

Fronius/SunSpec-Konvention: **negativ = Einspeisung/Überschuss, positiv =
Bezug aus dem Netz**. Wenn Ihre Home-Assistant-Entity umgekehrt gepolt ist
(z. B. "+3000 W Überschuss" bei Solarüberschuss, wie es sich umgangssprachlich
anfühlt), lassen Sie die Option **"Vorzeichen umkehren"** aktiviert
(Standardeinstellung). Falls Ihre Entity bereits die Fronius-Konvention
verwendet, deaktivieren Sie die Option.

**Wichtig:** Übermitteln Sie den **Netto-Überschuss** (Erzeugung minus
Hausverbrauch), nicht die reine PV-Erzeugung – ein echter Fronius Smart
Meter sitzt am Einspeisepunkt und meldet genau diesen Nettowert. Nur damit
berücksichtigt die Wallbox Ihre Grundlast korrekt.

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
2. Die Entity mit Ihrem Netto-Überschusswert auswählen.
3. Optional: Systemname, HTTP-Port, Modbus-Emulation (an/aus), Modbus-Port
   und -Unit-ID anpassen.

## Hinweis zu Port 80 / 502

Beide Standardports sind privilegiert (< 1024) und lassen sich je nach
Home-Assistant-Setup (Container-Rechte) nicht immer direkt binden. Falls der
Start mit "Could not bind..." fehlschlägt: entweder Home Assistant mit
`CAP_NET_BIND_SERVICE` betreiben, oder in den Optionen einen Port ≥ 1024
wählen und per Portweiterleitung (Router/`iptables`) auf 80 bzw. 502
umleiten. Die mDNS-Ankündigung transportiert den tatsächlich gewählten Port
korrekt mit, ein abweichender Port sollte also technisch trotzdem
funktionieren.

## Bekannte Unsicherheiten

Weder der HTTP- noch der mDNS-Teil sind offiziell von Fronius dokumentiert.
Sollte die Wattpilot das emulierte Gerät weiterhin nicht finden oder die
PV-Überschusskopplung ablehnen, bitte den tatsächlichen Netzwerkverkehr der
Wallbox mitschneiden (z. B. am Router) und mir die abweichenden Details
mitteilen – dann lässt sich der Server gezielt nachschärfen.
