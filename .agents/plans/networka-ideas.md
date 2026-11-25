# Networker — Ideensammlung aus den Sprachmemos

Geclustert aus 62 Sprachaufnahmen, 2025-08-06 bis 2026-12-31.
Originaltext der Transkription, unverändert. Quelle jeweils als Link aufs Transkript.

---

# Top 5 — jetzt umsetzen

In dieser Reihenfolge. Jede Zeile hat genau ein Ergebnis, an dem man sieht, dass sie fertig ist.

| # | Was | Ergebnis, wenn fertig | Warum jetzt |
|---|-----|----------------------|-------------|
| 1 | **Sequences-Modell schreiben und einfrieren** — drei Ebenen Default / Community / User, überschreibbar, Vendor-Sequences aus Git statt mitgeliefert | Ein Dokument plus die Config-Struktur im Code. Danach wird daran nicht mehr gerüttelt. | Kernabstraktion. Jedes weitere Feature baut darauf auf, und sobald fremde User eigene Sequences haben, ist eine Änderung teuer. Über 8 Aufnahmen hinweg konsistent gedacht — die Entscheidung ist inhaltlich schon gefallen, nur nicht festgehalten. |
| 2 | **Generic-Treiber-Fallback plus Warning, Treiber vom Plattform-Typ getrennt** | Unbekannter Vendor führt nicht zum Abbruch: Generic-Treiber, Warnung, Command Sequences laufen trotzdem. | Bestes Verhältnis von Wirkung zu Aufwand im ganzen Backlog. Verwandelt "nicht unterstützt" in "funktioniert eingeschränkt" und vervielfacht die erreichbaren Plattformen ohne Arbeit pro Vendor. |
| 3 | **Positionierung und Monitoring-Grenze in die Doku** — "Lightweight and Simple, der kleine Bruder von Terraform", und ausdrücklich: ersetzt kein Monitoring | Zwei Absätze in README und auf der Webseite. | Beides ist fertig formuliert, steht aber nur im Sprachmemo. Geschrieben entscheidet es künftige Feature-Fragen von selbst und hält den Scope klein. Aufwand: eine Stunde. |
| 4 | **Support-Matrix sichtbar machen** — welche Features, welche Vendors, welche Sequences pro Vendor, und woher sie geladen werden | Ein Befehl, der das ausgibt. | Für ein Tool, dessen Verkaufsargument Einfachheit ist, der Unterschied zwischen benutzbar und undurchsichtig. Fünf Aufnahmen verlangen dasselbe. Voraussetzung für alles mit Agents. |
| 5 | **Inventory: eine Quelle fertig machen, nicht alle** — clab oder SSH-Config, im Lab lauffähig | Ein Pfad, der end-to-end funktioniert, statt sechs halbe. | Grösster Block und meiste offene Fragen. Die eigene Ansage dazu: *"Simplify, simplify, massiv, und dann da bauen wir auf."* Erst wenn eine Quelle steht, lohnt sich die zweite. |

**Ausdrücklich noch nicht:** Skills / Agent / MCP (braucht Nr. 1 und 4 als Grundlage),
Nuts-Integration (dreimal als Frage gestellt, nie entschieden), Netbox / Infrahub
(selbst als "hinten angestellt" eingeordnet), Public Release (erst nach 1–4, sonst
frieren die Abstraktionen zu früh ein).

**Zur Auswahl:** 24 Aufnahmen nennen das Tool beim Namen (die Transkription schreibt
"Networker", "NetWorker" oder "Network"). Die übrigen wurden über die Leitbegriffe des
Tools gefunden — Sequences, Scrapli-Treiber, Vendor-Support, Inventory-Quellen,
CLI-/Config-Flags. Die mit **(?)** markierten Einträge könnten auch den MCP-Server oder
den Explorer/LNE betreffen statt den Networker; bitte selbst entscheiden.

---

# Priorität — die großen Hebel

Geordnet nach Wirkung auf das Produkt. Die Themenabschnitte darunter bleiben als
Nachschlagewerk und sind nicht umsortiert.

| # | Hebel | Wirkung | Aufwand | Warum | Abschnitt |
|---|-------|---------|---------|-------|-----------|
| 1 | **Sequences-Modell festlegen** | sehr hoch | mittel | Kernabstraktion, zieht Vendor-Support, Community, Flags und Introspection nach sich. Teuer zu ändern, sobald User eigene Sequences haben. 8 Aufnahmen, inhaltlich konsistent. | 3 |
| 2 | **Inventory-Modell festlegen** | sehr hoch | hoch | Grösster Block (17 Einträge) und meiste offene Fragen: statisch/dynamisch, versioniert, API oder lokal, welche Quelle zuerst. Eigene Ansage 2026-01-04: *"Simplify, simplify, massiv, und dann da bauen wir auf."* Solange offen, bleibt jede Quelle Einzelarbeit. | 6 |
| 3 | **Treiber von Plattform entkoppeln, Generic-Fallback plus Warning** | hoch | niedrig–mittel | Bestes Verhältnis im Backlog. Drei Aufnahmen kommen unabhängig zum gleichen Schluss. Macht aus "nicht unterstützt" ein "funktioniert eingeschränkt". | 5 |
| 4 | **Positionierung und Monitoring-Grenze schriftlich festhalten** | hoch | sehr niedrig | Beides ist fertig formuliert, steht aber nur im Sprachmemo. Als geschriebene Produktgrenze entscheidet es künftige Feature-Fragen von selbst und verhindert Scope-Ausweitung. | 1, 2 |
| 5 | **Introspection und Support-Matrix** | hoch | mittel | Fünf Aufnahmen verlangen dasselbe. Für ein Tool, dessen Argument Einfachheit ist, der Unterschied zwischen benutzbar und undurchsichtig — und die Antwort auf die Zielgruppenfrage. | 4 |
| 6 | **Public Release fertig machen** | hoch, aber nach 1–5 | niedrig | PyPI plus Docker Hub, Example Config je Plattform, Einstieg, Webseite. Vorher veröffentlichen bindet die Abstraktionen fest, bevor sie sitzen. | 11, 12 |
| 7 | **Skills, Agent, MCP** | mittel–hoch | mittel | Neuester Block (Dez 2026) und am unklarsten — Skill oder Agent oder MCP, und was davon gehört zum Networker statt zum bestehenden MCP-Server. Braucht 1 und 5 als Grundlage, weil ein Agent genau die Introspection braucht. | 9 |
| 8 | **Integrationen: Nuts, LNE, Ansible-Runner** | mittel | mittel–hoch | Dreimal als Frage formuliert, nie als Entscheidung. Jede Integration verdoppelt die Oberfläche. Nach 1 und 2 neu bewerten, dann eine auswählen. | 8 |
| 9 | **Dev-Umgebung, Demo, Workshop** | mittel | niedrig | DevContainer, Codespace, clab, Walkthrough-Video. Günstig und sofort nützlich für Workshop und Kundentermine, verändert das Produkt aber nicht. | 10, 13 |

---

## 1. Positionierung und Abgrenzung

**Lightweight and Simple — der kleine Bruder von Terraform** (2025-12-11, [`20251211 170519-53C7E150`](../../../../../voice-memo-transcripts/20251211%20170519-53C7E150.md))
> Beim Networker nochmal genauer, einfach sagen das Lightweight and Simple Terraform ein Ding ist das kleine Bruder und es viel schneller startet als Abstraktion, als Abgrenzung.

**Webseite und Abgrenzung gegenüber Cluster ssh** (2026-12-28, [`20261228 154447-BB041D1E`](../../../../../voice-memo-transcripts/20261228%20154447-BB041D1E.md))
> Irgendwohin auf jeden Fall die Webseite vom Network auf hinfam machen und vielleicht einmal abgrenzen gegenüber Cluster, was es da so alles gibt.

**Einstieg: für wen ist das eigentlich** (2025-11-23, [`20251123 140007-033E216B`](../../../../../voice-memo-transcripts/20251123%20140007-033E216B.md))
> Beim Network mal hinterlegen als Einstieg, für wen das eigentlich sein soll. Und auch in der Beschreibung das muss man so beschreiben. Für Einstieg und so.

**Zielgruppe schärfen** (2026-12-28, [`20261228 154537-DC15724C`](../../../../../voice-memo-transcripts/20261228%20154537-DC15724C.md))
> Ich möchte auch nochmal die neue Zielgruppe für mich selber beschreiben. System Integrators oder Network Integrators genau. NOCs, wie ich damit umgehen kann. Um nochmal zu überlegen, was man dann zeigt.

**Namensfindung** (2026-01-15, [`20260115 142315-5F6678E9`](../../../../../voice-memo-transcripts/20260115%20142315-5F6678E9.md))
> Vielleicht wäre es am besten, wenn wir es auch noch machen. NW. N... N... N... NAP underscore... NAP underscore... NAP underscore... Generator. So in die Richtung, oder? Oder vielleicht ist das auch okay, weil... alles Teil der Plattform ist.

---

## 2. Abgrenzung zum Monitoring — was Lightweight Testing NICHT ist

**Kernaussage, die klar formuliert werden muss** (2025-12-13, [`20251213 134213-256F782B`](../../../../../voice-memo-transcripts/20251213%20134213-256F782B.md))
> ganz wichtig zu formulieren dass für dieses lightweight testing im network nicht das monitoring ersetzt werden soll das heißt ich möchte nicht irgendwie link state oder oder port channel down oder sowas abfragen und dann wirklich schauen okay konnektivität ist da und so weiter bis hin halt zum bilder und wenn ich nachher sagen okay konnektivität nicht aber was mache ich jetzt als nächstes dann kann ich irgendwelche show commands ist schon aber auch da kann man sagen kittys der weg geht dann eben über einen lm guided am fahrt der dann einfach den networker nutzen kann denn ich kann ich selber entscheiden welche kommandos sondern die kommandos sind vor geht durch die sequenzes vom network

---

## 3. Sequences — das Kernkonzept

**Trennung Devices/Groups von Commands/Sequences** (2025-08-07, [`20250807 191915-DF67296C`](../../../../../voice-memo-transcripts/20250807%20191915-DF67296C.md))
> separieren von den device groups und devices von den commands und sequences

**Sequences herausziehen, an die Plattform hängen, unabhängig speichern** (2025-08-07, [`20250807 194631-ABFDA13F`](../../../../../voice-memo-transcripts/20250807%20194631-ABFDA13F.md))
> Wenn man die Sequences rausnimmt, kann man ja gleich auch mal die Plattform mit den Sequences dass die der Plattform ja, man kann sich raus, dass die Squires und so gespeichert werden. Das ist quasi independentes Touring.

**Predefined Sequences plus User Command Sequences, mit Override** (2025-08-08, [`20250808 134550-A54A0E2D`](../../../../../voice-memo-transcripts/20250808%20134550-A54A0E2D.md))
> vielleicht doch nochmal einfach sagen hey, predefined sequences und dann user command sequences dass man da sagen kann, gut der user soll das können, hat der eigene adden, globale config und dann noch das überschreiben auch

**Community Sequences — default aus, Review vor Aufnahme** (2025-08-14, [`20250814 202857-9D139A50`](../../../../../voice-memo-transcripts/20250814%20202857-9D139A50.md))
> Möglichkeit Community Sequences anzubieten, die dann halt einfach in einem Community pfatteln, vielleicht per default nicht enabled, aber die man halt enablen kann, die auch irgendwo reviewt werden müssen, bevor sie reinkommen.

**Drei Listen: Default, Community, User** (2025-12-20, [`20251220 103449-8CA476F6`](../../../../../voice-memo-transcripts/20251220%20103449-8CA476F6.md))
> Sequences sind auch so Listen mit Default, Community und User und vielleicht ist es halt nur Sequences von User, nur von allen oder von wer immer was haben will.

**Vendor Sequences aus Git ziehen statt mit dem Tool ausliefern** (2025-08-22, [`20250822 080552-7C20CA2B`](../../../../../voice-memo-transcripts/20250822%20080552-7C20CA2B.md))
> beim config einfach mal die Wendor Sequences mit rein nehmen auch dass die im Prinzip halt auch im cold-victier liegen die Frage ist wie kann man das machen oder? die würd's ja dann ziehen, naja die könnte man einfach vom gtap ziehen bei mir nicht statt dass man die mit dem tool mit liefern muss

**Sequences mit Parametern** (2026-12-28, [`20261228 152042-BDCD4BE0`](../../../../../voice-memo-transcripts/20261228%20152042-BDCD4BE0.md))
> Mal überlegen wie man noch Sequences einfach keinen Parameter übergeben. So etwas wie zum Beispiel Ping, dann macht er halt Markus, ah gut, dass der dann Ping dorthin macht und dann ja gut. Trotzdem können sie vielleicht nicht so schlecht sein, aber Ping, ja, mal überlegen.

**Bestätigung vor dem Ausführen einer Sequence** (2025-12-20, [`20251220 102953-C942C4EA`](../../../../../voice-memo-transcripts/20251220%20102953-C942C4EA.md))
> Bei einem Run von der Sequence um oder auch ein Flag einbauen, dass ich immer gefragt hätte, hey, guck, das sind die Kommandos, die ich ausfüge, ist das okay? So, ich weiß, dass der User das nochmal bestätigen muss, bevor die ausgeführt werden. Und dann sagt, hey, das ist der Default, den kann ich aber auch überschreiben.

---

## 4. Config-Introspection und Transparenz

**Config Introspection — woher kommt was** (2025-12-25, [`20251225 163208-28B4E49B`](../../../../../voice-memo-transcripts/20251225%20163208-28B4E49B.md))
> nochmal ein branch machen und das dann auch in den docs ankündigen bzw. have a follow introspection oder config infrospection das heißt wo kann für alles abfragen woher hat er die variable wo wie wird sie angewandt was ist die info dazu für sequences zum beispiel devices von wo werden sie geladen welche command sind supported und so weiter

**Anzeigen was supported ist — Features, Vendors, Sequences pro Vendor** (2026-12-28, [`20261228 150530-7151731F`](../../../../../voice-memo-transcripts/20261228%20150530-7151731F.md))
> Also ein sehr einfacher Weg wäre ich zum Beispiel sagen, welche Features sind supported, welche Wände sind supported, welche Features pro Wender, welche Sequences pro Wender zum Beispiel, und das einfach sehen kann.

**Vendor Support streamlinen, Herkunft der Sequences anzeigen** (2026-12-28, [`20261228 145914-CF40B3AB`](../../../../../voice-memo-transcripts/20261228%20145914-CF40B3AB.md))
> Auf jeden Fall Next Steps ist der Vendor Support Streamline, so dass ich dann auch anzeigen kann von wo die Sequences angezogen werden und dann dass ich sehe welche Sequences supported sind für welche Vendors und dass man die wichtigsten Vendors supporten, also Cisco, Nokia, Arista, Microtec, Linux General, dass man auch die natürlich zum Laptop sein kann, auch cool für Tests, damit man das zeigen kann.

**Plattformspezifische Command-Section in der Help** (2025-08-20, [`20250820 085411-DAB71C05`](../../../../../voice-memo-transcripts/20250820%20085411-DAB71C05.md))
> eine Plattform spezifische Section von Command Marken in Help und dass man sieht, dass das woanders dran hängt.

**Info-Sequence pro Vendor abfragbar** (2025-08-30, [`20250830 202334-04E25681`](../../../../../voice-memo-transcripts/20250830%20202334-04E25681.md))
> Wie kann ich eigentlich? Wäre noch cool, wenn ich für einen Vendor sage, Envy Info Sequence, also Envy Info Health, Ehe-Status und dann noch Minus Minus Vendor Microthek oder All. Generell zeigt einfach alle an, was macht er da eigentlich? Wäre noch cool zu wissen.

---

## 5. Plattform- und Vendor-Support, Treiber

**Supported Platforms sichtbar machen, SR Linux dazu, Autodetection überlegen** (2026-12-26, [`20251226 150738-B9149D28`](../../../../../voice-memo-transcripts/20251226%20150738-B9149D28.md))
> Auf jeden Fall müssen die Plattforms noch im Networker, die supported sind. Somit unbedingt das R-Linux dazu kommen und dann gibt es eine Überlegung, ob man nicht eine Autodetection machen kann. Jetzt gerade nicht.

**Scrapli: nur Vendors als Default, die Scrapli auch unterstützt** (2025-08-14, [`20250814 213031-C22C839A`](../../../../../voice-memo-transcripts/20250814%20213031-C22C839A.md))
> bei Scrappli nur bei den vendors als default machen die Scrappli auch unterstützt

**Auf Generic Treiber zurückfallen plus Warning** (2025-10-29, [`20251029 192516-5984D4DA`](../../../../../voice-memo-transcripts/20251029%20192516-5984D4DA.md))
> Im Skrappli einfach auf den Generic Treiber zurückfallen, wenn das Wendor nicht supported ist. Und dann das probieren und wenigstens eine Warning ausgeben, dass der Wendor nicht supported wird. Nicht schlecht.

**Generic Treiber bei Cumulus — Command Sequences funktionieren trotzdem** (2025-10-30, [`20251030 181021-557CDD5C`](../../../../../voice-memo-transcripts/20251030%20181021-557CDD5C.md))
> Kurz rausfinden, wie Scrably's Hand hat, wenn ich jetzt auf den Cumulus einlog, weil da eigentlich einfach auch Generic Treiber nehmen kann. Sagen, immerhin funktionieren die Command Sequences, die man hinterlegt.

**Treiber von der Plattform entkoppeln** (2025-10-16, [`20251016 180740-0A508D84`](../../../../../voice-memo-transcripts/20251016%20180740-0A508D84.md))
> Als letzte Aufgabe schauen wir jetzt einfach mal noch, dass einmal das Firmen-Upgrade läuft beim MicroTick neben Backup und dass auch das Scrubli so funktioniert, dass man einfach sagen kann, okay, Treiber Scrubli, Type, iOS 6e und dass man dann aber das auch entkoppelt von der Plattform, die wir verwenden, weil wenn es jetzt Viber Linux ist, dann ist für uns trotzdem die Plattform mehr aus Cumulus oder dafür haben wir dann die Enview-Commands oder was auch immer. Genau.

**Generiktreiber gegen echte Industrie-Hardware testen** (2025-12-20, [`20251220 102827-F782D07A`](../../../../../voice-memo-transcripts/20251220%20102827-F782D07A.md))
> Der Pfadschimmer, den Generiktreiber gegen Hirschmann, Siemens und Garderoß ausprobieren lassen vom NetWorker.

**Test gegen fremde Infrastruktur organisieren** (2025-12-21, [`20251221 173500-C3FA8ECF`](../../../../../voice-memo-transcripts/20251221%20173500-C3FA8ECF.md))
> Fatschi sagen, dass er sein, dass ich bei den Desktop schon schicken kann, wenn ich so weit bin, wenn alles läuft. Und trotzdem noch fragen, ob der Telski jetzt mal läuft, dass ich mal die Networker-Sachen gegen seine Infrastruktur daheim testen kann. Gegen den Garderoßen, den Schneecktreiber, Siemens und die anderen Gustls.

**Parser für fehlende Plattformen implementieren** (2025-11-15, [`20251115 132508-83F32612`](../../../../../voice-memo-transcripts/20251115%20132508-83F32612.md))
> Anzeigen, dass ich ab Ende November, September, Januar, soviel ich kann mithelfe, die Parse zu implementieren für die fehlenden Plattformen, zu validieren, was wir da haben und dass bis dann losgeht das Zeug bereit sein muss und dass der Thomas jetzt sein Zeug abschließen muss.

**NTC-Templates pro Vendor** (2025-08-06, [`20250806 054733-D9E3F498`](../../../../../voice-memo-transcripts/20250806%20054733-D9E3F498.md))
> Beim Resource ist die NTC-Template zu runterladen und dann die Resource Implementation so machen für den MCP Server, dass er auf den Vendor geht, wenn man nach einem speziellen Vendor fragt.

**Nur Defaults überschreiben, Änderungen an Plattform-Defaults detektieren** (2026-01-10, [`20260110 115339-ED263506`](../../../../../voice-memo-transcripts/20260110%20115339-ED263506.md))
> wir müssen einfach das so bauen dass wir einfach tatsächlich nur die defaults overriden auch im Chor wir müssen nicht wir machen uns viel wenn wir alles da rein tun aber wie jetzt bei Saikom eben das problem wenn sich verändert dass man dann da den Namen nicht haben oder gut das kann man überlegen ob dann ob man dann einfach sagt hey guck mal so merkt man es oder machen wir bauen ein Mechanismus ein der sowas detektiert dass wenn sich was verändert hat das müssen wir natürlich schon im Testing vorher irgendwie rausfinden bei neuen Versionen mal überlegen wie das gehen kann im Sinne von die Plattform unterstützt jetzt oder hat jetzt plötzlich einen neuen default im bekommen dass wir dies detektieren oder für jede Plattform was in den neuen defaults dass wir das sichten dass wir überlegen was das für uns heißt

**Example Config pro Plattform plus C-Lab** (2025-11-22, [`20251122 164142-F1E973CA`](../../../../../voice-memo-transcripts/20251122%20164142-F1E973CA.md))
> Network and Example Config für jede Plattform. Die müssen einfach Example in die Default Config, dass man da einfach sieht, alles klar. Und ein C-Lab-Reihen halt. So kann ich nicht mehr auffahren und das austesten.

**Read-Only Login pro Plattform** (2026-08-09, [`20260809 084029-1E541F60`](../../../../../voice-memo-transcripts/20260809%20084029-1E541F60.md))
> Jede sollte noch Read-Only Logins machen können. Jede Plattform sollte einen Read-Only User haben, auf die wir einloggen, sodass auch die Kunden da auf die Geräte könnten.

---

## 6. Inventory

**SSH-Config als Inventory-Quelle** (2025-12-23, [`20251223 191832-F51BA669`](../../../../../voice-memo-transcripts/20251223%20191832-F51BA669.md))
> Eine Inventoryoption natürlich für Networker, weil ja die SSH-Config kann ja auch nehmen. Das kann ja relativ simpel sein.

**Config-Option, SSH-Config NICHT einzulesen, auch als CLI-Flag** (2026-12-30, [`20261230 153352-2CA6A45C`](../../../../../voice-memo-transcripts/20261230%20153352-2CA6A45C.md))
> Networker Config Option, das SSH nicht einliest. SSH Config bzw. das muss auch potenziell auf der Command Line mitgeben können als Option.

**Nornir Inventory, Dynamic Read oder Translator ins Device-/Group-Format** (2025-08-14, [`20250814 202709-6BAC3BD9`](../../../../../voice-memo-transcripts/20250814%20202709-6BAC3BD9.md))
> ein Noir Inventory, Dynamic Read oder Translator ins Code Device und Group Config Format wäre cool. Da kann man direkt beim Container Lab sagen. Oder halt dann einfach die entsprechende SSH Config, die man dann sagt, nimm die doch. Also die wäre eigentlich auch noch möglich, stimmt. Die wäre noch cool. Wobei eben mit den Labels und so ist es glaube noch cooler mit Noir, mit den Gruppen. Die Labels und Groups und genau. Oder einfach eben das Video schon gemacht. Dann direkt übersetzen nach oder an der Fly übersetzen, genau.

**Dynamic Inventory auf der Webseite vorzeigen** (2025-08-14, [`20250814 203255-65F549BF`](../../../../../voice-memo-transcripts/20250814%20203255-65F549BF.md))
> Dynamic Inventory mit Melanie. Wär auch noch cool, oder? Und das dann einfach genau auf der Webseite zeigen. Mit dem Tool. Und sagt, hey, so einfach geht es hier. Zack, holt das. Transformator. Und dahin. Zack. Oder ich muss einfach sagen, was zu was. Und dann hat man es.

**Container Lab schreibt direkt ins Networker-Inventory, vorinstalliert ausliefern** (2025-12-11, [`20251211 131721-72AF3F69`](../../../../../voice-memo-transcripts/20251211%20131721-72AF3F69.md))
> Mega cool, wenn C-Lab auch in den Networker Inventory schreiben würde und der Networker schon dabei wäre und der einfach mitgeliefert würde, dass die Leute es einfach schnell und einfach benutzen können, weil es so simpel ist. Vorinstalliert, fertig.

**Gruppen on the fly erzeugen, wenn CLAB keine hat** (2025-12-20, [`20251220 101832-81A691E1`](../../../../../voice-memo-transcripts/20251220%20101832-81A691E1.md))
> Selbst wenn CLAB keine Gruppe hat, On The Fly einen erzeugen für alle Devices in der Gruppe. Und klar, wenn man halt Kommandos laufen lässt gegen die ganze Gruppe, die halt bei anderen nicht supported sind, dann fehlen die halt einfach.

**C-Lab Kind nach Scrapli mappen** (2025-12-20, [`20251220 101911-307E029E`](../../../../../voice-memo-transcripts/20251220%20101911-307E029E.md))
> nochmal genau das Mapping von C-Lab Kind bei uns anschauen vielleicht kann ich auf das einfach nehmen und das dann nach Scrappling mappen

**C-Lab Inventory lesen, um Online-Status zu sehen** (2025-12-20, [`20251220 104432-D5FC845A`](../../../../../voice-memo-transcripts/20251220%20104432-D5FC845A.md))
> Ein cooles Gimmick wäre noch, wenn ich das C-Lab Inventory läse, um zu gucken, welche Devices, welche Online sind, von den Devices.

**Inventory aus dem LNE generieren, Gruppen über Tags** (2025-12-13, [`20251213 134817-81069E80`](../../../../../voice-memo-transcripts/20251213%20134817-81069E80.md))
> Aus dem LNE auch ein Inventory für Networker kann man generieren lassen und dann zum Beispiel über Tags Gruppenzugehörigkeiten machen und so.

**Mit LNE lokal syncen** (2026-12-31, [`20261231 185434-42922B47`](../../../../../voice-memo-transcripts/20261231%20185434-42922B47.md))
> Sync mit RNE wäre auch noch cooles Inventory, dass man das lokal syncen kann und dann es hat. Oder sogar als dann ein Inventory, aber ja, das ist auch nichts besser, wenn die Gruppen zustande kommen.

**Dynamic Inventory Netbox / Infrahub — später** (2025-12-20, [`20251220 104622-D22B2B38`](../../../../../voice-memo-transcripts/20251220%20104622-D22B2B38.md))
> Offensichtlich so Dynamic Inventory Sachen wie Netbox und AutoPorter Infra Hub können wir dann noch machen, aber wir sind natürlich erstmal hinten angestellt.

**Ansible Inventory nutzen** (2025-12-20, [`20251220 100352-2D6B5455`](../../../../../voice-memo-transcripts/20251220%20100352-2D6B5455.md))
> Check what it needs to do. The Enzible Inventory Dance 2 and the simple stuff. Might as well use that.

**Inventory muss auch mit NAPALM, gNMI, Netconf gehen** (2026-01-10, [`20260110 114559-137842F7`](../../../../../voice-memo-transcripts/20260110%20114559-137842F7.md))
> Ich kann ja nochmal darüber nachsteigen in unserer Situation. Wenn es sicher nicht für alles ernst wird. Daher macht es auch keinen Sinn, da es zu ernsthaft spezifisch ist. Ernsthaft ist einfach nur der Weg, wie die Inventory da drauf kommt, mit dem was es uns unterstützt. Und da muss man auch sagen, es muss auch mit NAPA funktionieren. Das heißt, wir iteraten da mal drüber. Oder von mir aus haben wir mit Genomac oder Netconf.

**Provider ans Inventory hängen** (2026-01-14, [`20260114 190230-10FEBDB4`](../../../../../voice-memo-transcripts/20260114%20190230-10FEBDB4.md))
> Sollten definitiv nicht vergessen, dass man auch den Provider oder das ObSansible oder Noonion, Mico oder Scrable oder was auch immer ist für das Inventory, dass man das mit irgendwo anhängt und überlegt wo dran kommt das.

**Inventory mit der Galaxy Collection teilen** (2025-12-13, [`20251213 081134-6FB513B8`](../../../../../voice-memo-transcripts/20251213%20081134-6FB513B8.md))
> wie kann man das Inventory an die Galaxy Collection teilen, dass die zwei Sachen Hand in Hand laufen.

**NMD ins Inventory querien, dynamisch** (2025-12-02, [`20251202 163833-CBF9B526`](../../../../../voice-memo-transcripts/20251202%20163833-CBF9B526.md))
> Unten dem Warntester zur Verfügung stellen, dann gucken, ob alles soweit da ist, was man hat. Dafür kann man entweder ein Networker nuxen, dann gucken, was er damals für ein Tool geschrieben hat, zum Querien von NMD ins Inventory und dann dynamisch Ritz, Story-Sults und dann Potenzial. Salz ins Gitter oder einfach runterladen.

**Static Inventory versioniert, Rückkehr zur Vorversion (?)** (2026-01-04, [`20260104 145715-DCC6B992`](../../../../../voice-memo-transcripts/20260104%20145715-DCC6B992.md))
> aus meiner Sicht sollte man ein Static Inventory haben. Das ist jedes mal wenn wir es ändern, die Platte, und zwar über dynamischen Träger, wenn das neueste dazu kommt, dann wird das versioniert und damit kommen wir eben auf die vorige Version zurück und alle Confix Dears haben ein Collection Item Version. Dass wir dann immerhin wieder zurückkommen, wir müssen da nicht so viel synchronisieren und so weiter.

**Inventory-Format zuerst lösen, im Lab, massiv simplifizieren (?)** (2026-01-04, [`20260104 144054-2168C1AD`](../../../../../voice-memo-transcripts/20260104%20144054-2168C1AD.md))
> Thomas muss den Teil erstmal lösen, wenn er ein Inventory hat, wie das auszusehen hat und wie man das dann kontrolliert über Collections oder wie auch immer versioniert kriegen und wie man das deployen. Und woher das Inventory nachher kommt, muss man dann überlegen. Das ist der erste Schritt. Der Teil muss sauber sein. Der allererste Schritt ist aber zurück zu gehen, dass das alles im Lab funktioniert. Simplify, simplify, massiv, und dann da bauen wir auf.

**Alles in der API, auch Gruppen und Hierarchien; Dump zum Debuggen (?)** (2026-01-14, [`20260114 114433-E8A4DDFF`](../../../../../voice-memo-transcripts/20260114%20114433-E8A4DDFF.md))
> Ich denke alles muss in der API leben, auch die Gruppen und die Gruppenhierarchien. Wir brauchen dann für uns einfach zum Debuggen nachher einen Weg zum, oder vielleicht auch zum entwickeln, zum die Sachen auf DIST dumpen, damit es einfacher wird, damit man mit den Inventoryladen, nicht mit dem dynamischen, sondern mit dem lokalen Inventory arbeitet oder so, aber das muss sich halt entwickeln.

**Leichte Inventory-Nodes im Lab, Windows faken** (2026-08-14, [`20260814 210713-AA22FD79`](../../../../../voice-memo-transcripts/20260814%20210713-AA22FD79.md))
> Auf jeden Fall noch im Labs ein paar Inventory Notes reinmachen, die leicht sind. Ja, Windows faken oder so.

---

## 7. Kommandos und Features

**Einfache Kommandos als Einstieg** (2025-11-09, [`20251109 101704-7BB76081`](../../../../../voice-memo-transcripts/20251109%20101704-7BB76081.md))
> zwei drei simple networker sachen mit get vlans get interfaces so was sage ich relevantisch oder auch get firewall rules und dann wäre auch sehr interessant dass man einfach sagt hey get copilot was brauche ich zum aktivieren was kann ich damit testen und so weiter

**Full Backup pro Plattform, Sequence für Run-/Startup-Config** (2025-10-17, [`20251017 115221-7F26AEA8`](../../../../../voice-memo-transcripts/20251017%20115221-7F26AEA8.md))
> Im Backup einfach wirklich nur Full Backup machen mit allem drum und dran, was für jede Plattform braucht und nichts. Nochmal fünf unterschiedliche Command-Supporten. Da kann man dann einfach eine Sequence machen, wenn man nur die Run- und Startup-Configs kriegen will und save.

**Logs abholen und speichern** (2025-12-20, [`20251220 102728-D7A2EDA7`](../../../../../voice-memo-transcripts/20251220%20102728-D7A2EDA7.md))
> Loks abholen im Networker auf jeden Fall, ein Speichern wäre noch cool. Und der Hals sagt, hey, der weiß es schon, aber das haben wir ja nicht. Wenn die Loks auch noch abholt, gibt es schon 1000 oder immer.

**Interface-Details auslesen** (2026-05-23, [`20260523 151245-A695BA34`](../../../../../voice-memo-transcripts/20260523%20151245-A695BA34.md))
> Nächster Job für den Wogen könnte das sein, dass er mal die Interface Info ausliest, ob es was für ein LR hat, was für ein Licht oder was für ein Interface-Typ und Arrow-Counters und so Sachen alles, dass er das mal anfängt.

**Interaktive Shell / als Admin draufklicken und Befehle absetzen** (2025-12-13, [`20251213 135139-84D996BD`](../../../../../voice-memo-transcripts/20251213%20135139-84D996BD.md))
> Mal besprechen, ob das nicht doch einfach wäre, das Feature mit dem draufklicken als Admin und dann eingeloggt sein und die Befehle absetzen zu können. Oder vielleicht auch eine Shell kriegen zu können für Networker, dass man den einfach laufen lassen kann. Das ist ja auch nicht, dass der dann noch an den Tisch bringt, muss man brainstormen.

**Raw Outputs der Show Commands als Tech Bundle verschicken** (2025-12-18, [`20251218 135528-2CD45D60`](../../../../../voice-memo-transcripts/20251218%20135528-2CD45D60.md))
> Weitze sagen, dass ein Teil von dem ganzen Rewrite sein muss, dass wir auch via Handy uns einen Tech Bundle schicken, wenn sie Raw Outputs haben und aber auch sie selber die Raw Outputs kriegen können von den Show Commands, was hier auch interessant sein kann. Wenn man einen vor Ort versiert ist, legt ihr ja immer das alles an den ganzen Shows.

**Texte / Kommando-Mapping durchreichen** (2025-08-22, [`20250822 010811-7013D700`](../../../../../voice-memo-transcripts/20250822%20010811-7013D700.md))
> Und auch irgendwie eine Texte für seinem Zeug reinbringen, dass man halt den Networker verwendet dass man dann auch direkt das Texte für seinem Passen kann, dass man da mit was da rausgehen will. Über das Kommando Mapping irgendwie funktionieren wird.

**Dateien im eigenen Repo anfassen statt Kopie** (2025-11-22, [`20251122 143807-5C3AD38F`](../../../../../voice-memo-transcripts/20251122%20143807-5C3AD38F.md))
> Eigentlich wäre es beim Networker doch cooler, wenn man dann in seinem eigenen Repo die Files verändert. Dass sie zurückkommen, dass das nicht eine Kopie ist vom Repo, sondern dass es tatsächlich die Repo-Files anfasst. Statt nach jeder ohne Kopie.

**Command-Line-Teil plus Library/API, Vorbild Tool von Thomas** (2025-12-13, [`20251213 133249-1B8204A9`](../../../../../voice-memo-transcripts/20251213%20133249-1B8204A9.md))
> Aus dem Tool von Thomas bauen wir einfach genau das gleiche wie im Network. Wir machen einen Command Line Teil, der das Passing macht und dann braucht man einen Teil, der einfach auch in unserem Code könnte integriert werden und quasi der API oder der Library anbietet.

---

## 8. CLI- und Config-Flags

**Flag: keine General Sequences, nur User Sequences** (2025-12-20, [`20251220 103227-E9210F5E`](../../../../../voice-memo-transcripts/20251220%20103227-E9210F5E.md))
> Konfig-Flag mit der Option und der Madeline-Flag, dass man keine General Sequences verwenden soll, nur User Sequences.

**Nur ein Ansible-Runner gleichzeitig** (2026-01-19, [`20260119 162746-F8409904`](../../../../../voice-memo-transcripts/20260119%20162746-F8409904.md))
> sicherstellen dass nur eine in Sippelrunner laufen kann zum zeitpunkt x erstmal und das potenziell vielleicht auch nicht von der command line was laufen kann aber zur gleichen zeit

---

## 9. Integrationen

**Nuts verheiraten** (2025-12-12, [`20251212 104320-60C9D570`](../../../../../voice-memo-transcripts/20251212%20104320-60C9D570.md))
> Brainstorming, wie man Nuts mit einem Networker verheiraten könnte.

**Nuts als Addon — mehr Wert?** (2025-12-13, [`20251213 133441-2E47264A`](../../../../../voice-memo-transcripts/20251213%20133441-2E47264A.md))
> Ich überlege inwiefern der NetWorker mit Nuts verbunden auch noch mehr Wert bieten könnte als Addon.

**Network-State abfragbar machen** (2025-12-13, [`20251213 134400-5A22378B`](../../../../../voice-memo-transcripts/20251213%20134400-5A22378B.md))
> Mal mit dem Fudgee-Brainstormen, wie man den Network-State irgendwie besser mit reinnehmen kann und abfragbar machen. Im Sinne von den ganzen Daten, die wir haben. Oder die Eddationale Daten, die wir eventuell reinbringen wollen.

**Ansible Runner remote laufen lassen, Verbindung von sich aus zum Inventory** (2026-01-14, [`20260114 114650-3E5CCCED`](../../../../../voice-memo-transcripts/20260114%20114650-3E5CCCED.md))
> eine der fragen wäre halt auch ob man den ansible runner gerne auch irgendwo remote laufen lassen können wollt wo der von sich aus die verbindung zum inventory aufbauen kann ergo wenn sie zum beispiel ein cloud controller wäre und die automatisierung dann aber vor ort läuft das wäre auch so was wo man sicher sagen könnte es mir noch interessant sich mal zu überlegen design

**Variablennamen nicht umbenennen — Cisco und Mikrotik nutzen unterschiedliche (?)** (2026-01-14, [`20260114 112941-C31F39D3`](../../../../../voice-memo-transcripts/20260114%20112941-C31F39D3.md))
> wichtig beim meeting ist hier klar zu machen dass wenn wir selbst immer unterschiedliche wände haben wie cisco oder microtik dass die variablen haben beide menschen verwenden unterschiedlich sein werden für das was das inventory braucht ob das jetzt eben das nachher napalm oder was auch immer ist oder das oder oder eben wo beides ein zubel das heißt wir werden da auch nicht die macht auch keinen sinn die variablen um zu benennen glaube ich weil es einfach noch eine interaktion einfach die dann noch schwieriger ist mehr ermöglichen wollen dass der kunde einfach auch ein bisschen komplexere sachen konfigurieren kann soll aber klar idealerweise kann wir da sehr dynamisch einladen was wenn es eben ob man per spezifikation gebe was man da machen könnte oder dann zum sagen okay die wertesten vorgeben die gibt es die können da generieren und das ist jetzt halt die frage oder ob ob sowas möglich ist und wenn man das im frontend machen wird was das dann ja wo wie man die daten dann speichern das wäre natürlich die beste verknüpfung sagen hey wir haben einen dynamischen weg wie man da das abfragen

**Mit dem OT-Workshop / Lab verbinden** (2026-01-27, [`20260127 081949-00B73333`](../../../../../voice-memo-transcripts/20260127%20081949-00B73333.md))
> Ich will mit Tim nochmal die Bewerbung durchgehen für den OT-Workshop und dann wirklich rauskristallisieren, was in den vier Stunden gezeigt wird, was möglich wird, was industrielle Netze ausmacht, welche Problemstellungen sich dort auftun. und wie man tatsächlich dann mit so einem Lab, wie wir es haben, Explorativ-Designs testen kann oder aber auch als eben als als große Firma selber so ein Labs ausbauen oder wenn man solche Netze delivert, sagen, hey, wir können hier das testen mit dem ganzen Umgebung, um dann Validated-Designs rauszugeben für solche Umgebungen, die komplett vollautomatisiert sind. Genau. Mit dem Networker noch irgendwo verbinden.

---

## 10. AI, Skills, Agents, MCP

**Als Skill oder Agent registrieren** (2026-12-29, [`20261229 225441-885D9319`](../../../../../voice-memo-transcripts/20261229%20225441-885D9319.md))
> besser gesagt Networker Skill oder Networker Agent dann muss der besser wäre

**Als ein oder mehrere Skills registrieren und ausprobieren** (2026-12-28, [`20261228 151319-3E20232D`](../../../../../voice-memo-transcripts/20261228%20151319-3E20232D.md))
> Network als ein oder mehrere Skills registrieren. Wollen wir mal ausprobieren, dass alles geht, wenn er die Docks hat und so.

**Network MCP** (2026-12-29, [`20261229 225400-98E3C813`](../../../../../voice-memo-transcripts/20261229%20225400-98E3C813.md))
> Vielleicht ist ja auch mal noch ein Network MCP ganz cool, der dann einige von den Sachen einfach ermöglicht.

**MCP hinter den Reverse-Proxy** (2025-11-15, [`20251115 133636-137F5B56`](../../../../../voice-memo-transcripts/20251115%20133636-137F5B56.md))
> Auf jeden Fall mal verfolgen, wie ich MCP oder unsere Dinge... Ach so, ja, wenn wir MCP halt hinter den Reverse-Proxy packen kann. Oder klar, wenn wir unser Interface selber machen, dann ist es egal, dann ist ja alles lokal.

**Skills um den MCP bauen, Schema Validation fehlt (?)** (2026-10-07, [`20261007 134208-B003F259`](../../../../../voice-memo-transcripts/20261007%20134208-B003F259.md))
> Wir müssen unbedingt Skills um unseren MCP bauen, dass Patentica die Skills verwenden können. Ein Problem beim Patentica ist eben, dass Schema Validation erstmal fehlt und dann nochmal probieren muss. Ich glaube, dass es das einfach auf Anhieb richtig kriegt mit dem ersten Request.

**MCP-Server soll die Toolbox verstehen (?)** (2026-10-08, [`20261008 111250-9AC3AD11`](../../../../../voice-memo-transcripts/20261008%20111250-9AC3AD11.md))
> Den MCP-Server vielleicht so erweitern oder uns gilt, dass er die Toolbox versteht und dass man dann auch mit dem Agent die Toolbox ein Stück weit befüllen und prüfen kann. Das wäre auch noch cool.

**Asynchroner Agent-Loop über MCP mit Task-ID (?)** (2026-10-06, [`20261006 100856-D7A67C91`](../../../../../voice-memo-transcripts/20261006%20100856-D7A67C91.md))
> Mid PyATS tasks we get a new option in MCP where with MCP tasks we get a new option of asynchronous agent loop using MCP and points where you just get a task id and then query on the task id once you want to continue pretty cool i can mention that

**Skills kultivieren, Scheduled Tasks für Checks im Hintergrund (?)** (2026-09-26, [`20260926 184411-7229EA1D`](../../../../../voice-memo-transcripts/20260926%20184411-7229EA1D.md))
> Wir brauchen unbedingt die Möglichkeit Skills zu kultivieren oder irgendwo aus dem Gelernten, aus dem Workflow irgendwo auch was zu hinterlegen, damit andere auch damit von Profitieren können. Ich sage, hey, das sind auch so Scheduled Tasks oder so sein können, die offline im Hintergrund nachher die Checks machen, wo ich nicht interaktiv, sondern wo ich warte, wo ich Resultate kriege, beziehungsweise wo ich einfach auch informiert werde, wenn was Problematisches vom Score rauskommt zum Beispiel.

**TextFSM-Parser per MCP generieren lassen (?)** (2025-10-05, [`20251005 172608-144C5FE6`](../../../../../voice-memo-transcripts/20251005%20172608-144C5FE6.md))
> Unbedingt überlege, wie ich jetzt nochmal den Chefs-Sending aufnehmen kann, wie man selber Basis schreiben kann mit dem Text-FSM, MCP in Verbindung mit dem Schema aus den wichtigsten Identik-Classes, die wir in Verbindung, oder das eigentlich auch im MCP selber zu haben, oder einfach im MCP selber sagen zu können, hey guck, das ist die Funktion, das müssen wir generieren und den Teil einfach mal irgendwie sinnvoll hinzukriegen, dass man sortiert den Input-Hammer von Western zum Beispiel, was kriegen wir da raus?

**Tool-Calling der gängigen Clients gegen den MCP auswerten (?)** (2025-12-25, [`20251225 161147-2BC80655`](../../../../../voice-memo-transcripts/20251225%20161147-2BC80655.md))
> mal ein Tool schreiben, was einfach sagt, hey, alle gängigen Sealeist, die ich habe, Toolcalling machen lassen gegen unseren MCP und sagen, hey, für die Frage, welche Tools ich verwenden, verwenden sie und das auswerten.

**Anything LLM integrieren — mit MCP, Toolbox und Logs sprechen (?)** (2026-04-05, [`20260405 181305-F95313C9`](../../../../../voice-memo-transcripts/20260405%20181305-F95313C9.md))
> Hier könnte man auch noch das Anything LLM integrieren in die ganze Applikation. Das wäre eigentlich auch noch cool. Sodass es sowohl mit dem MCP als auch mit dem Toolbox und mit den Logs und mit dem Ding sprechen kann.

**Documentation MCP (?)** (2026-05-27, [`20260527 182653-D1E8D83F`](../../../../../voice-memo-transcripts/20260527%20182653-D1E8D83F.md))
> herausfinden wie dieser eine documentation mcp funktioniert ob es nicht aussehen macht dass man eben unsere dokumentation vielleicht auch so als app im swapswitcher drin hat bei uns und dann dagegen eben auch den mcp laufen lassen kann ja nicht sicher was bei uns bringt

**PR-Agent prüft Docs und funktionale Tests** (2025-12-27, [`20251227 102626-46E0E3CB`](../../../../../voice-memo-transcripts/20251227%20102626-46E0E3CB.md))
> für den PR oder Merch Request Agent, dass man da auch noch mal rein tut, dass die für den Networker, dass die Docs geschrieben sind, User Docs, dass die Functionale Tests da sind und was er potenziell dafür auch noch mal für andere Agents nebenher ziehen soll, wenn er die schreibt oder validiert und das immer am Ende halt auch noch mal sagt, hey, okay, das Resultat festhalten in einem PR Review, was auch immer, Planfile und dann daraufhin eben hingeht und sagt, okay, jetzt das Planfile nochmal selber Reviewen mit einem eigenen Agent, der das Planfile Reviewt auf Konsistenz und auf was auch immer, auf Reasoning, das was halt die eigenen anderen Subagents zurückbringen, so einer, der das nochmal bewertet und aktualisiert.

**Plan-Prompt, Hand-off, Validierungs-Agent vor dem Implementieren (?)** (2026-01-10, [`20260110 122726-C47827CF`](../../../../../voice-memo-transcripts/20260110%20122726-C47827CF.md))
> das als Plan Prompt und dann natürlich wenn der Implementation Prompt kommt, wenn ich ein Hand-off mache, dass er sagt, dass er referenziert ist, ein Implementation Prompt, wo nochmal ein Skill, dass es um die Entwicklung geht, die nimmt oder so kein Agent, der das validiert und das Feedback gibt, ob das dem entspricht. Und nur wenn der grünes Licht gibt, der Agent, dann nutzt das Skill und die Refactoring Option.

**Software-Architect-Skill mit dem ganzen Projektkontext (?)** (2026-01-10, [`20260110 122831-28AE9193`](../../../../../voice-memo-transcripts/20260110%20122831-28AE9193.md))
> Nein, das muss wirklich ein Skill sein. Skill kann auch Agents ausführen, aber Skill muss wirklich sagen, ich bin ein Software Architects-Skill für Python und für dieses Projekt. Und habe dann auch den ganzen Kontext dazu. Weil der Agent kriegt ja nur den Prompt. Der ist ja dann reduziert, wenn ich gerade am Implementieren bin.

---

## 11. Entwicklungsumgebung und Testing

**DevPod Container plus Container Lab zum schnellen Ausprobieren** (2025-08-26, [`20250826 172725-19ADFEAD`](../../../../../voice-memo-transcripts/20250826%20172725-19ADFEAD.md))
> Dev-Pod Container bereitstellen, ein bisschen kurzbessert, einfach mal schnell ausfüllen kann das Tool. Mit dem Container Lab hinten dran und schauen kann was er eigentlich alles macht und wie die darauf hinzugeschnitten ist sinnvoll ist. So was könnte man da damals generieren.

**DevContainer und Codespace, dazu ein Video** (2025-08-27, [`20250827 080343-5A6DFD05`](../../../../../voice-memo-transcripts/20250827%20080343-5A6DFD05.md))
> DevContainer adden, wo man dann auch der Container Lab mit Container Lab bzw. einen Codespace, dass man das Zeug einfach mal ausprobieren kann und dann auch ein Video davon machen.

**Was ein Lab eigentlich braucht — deklarativ, Umsetzung, Überwachung, Report (?)** (2025-09-01, [`20250901 171140-E9B42DE0`](../../../../../voice-memo-transcripts/20250901%20171140-E9B42DE0.md))
> Ich mag mal zusammenschreiben, was für so ein Lab eigentlich wichtig ist. Irgendeine Art deklarativen Approach, wie das Lab aussehen soll. Beispiel zum Beispiel ein Container-Lab zeigen. Dann braucht es etwas, was das umsetzt auf die Infrastruktur. Das heißt, laden von den Deklarationen. Dann braucht es etwas während des Testes zum überwachen und irgendwo zusammenführen. Und dann braucht es etwas, um nachher auch ein Report zu generieren, festhaltende Resultate und eine Art Dokumentation zu hinterlegen in irgendeiner Form. Und die Daten mit anzubieten oder mit zu speichern.

**Virtual Images für Container-Lab-Tests anfragen (?)** (2025-12-18, [`20251218 094745-999A229C`](../../../../../voice-memo-transcripts/20251218%20094745-999A229C.md))
> Themen für Josh sind das Geschäftliche mit US-Markt, dann ob er bei hier schon mal nicht mal anfragen kann, ob es auch Virtual Images gibt, damit man im Container-Lab die Tests fahren kann. Das wäre eher als Support für SNMP und einfache Erweiterbarkeit.

**Siemens Scalance Container für Container Lab (?)** (2025-09-01, [`20250901 164753-33827E93`](../../../../../voice-memo-transcripts/20250901%20164753-33827E93.md))
> Siemens fragt, ob es für das Scalance-Zeug auch Container gibt, die ihr im Container-Lab unterstützen könnt und natürlich auch den Mikrozugriff.

**Requirements- und Architecture-Paper als Markdown-Vorlage (?)** (2026-01-27, [`20260127 081223-6C0D30FA`](../../../../../voice-memo-transcripts/20260127%20081223-6C0D30FA.md))
> markdown vorlage finden für so einem requirements and architecture paper schreiben so dass man da ein bisschen eine form vielleicht schon hat dies vorgibt vielleicht gibt es ja was gut verwenden kann oder auch für skill das gibt es ein skills und sowas niederschreiben

---

## 12. Packaging und Release

**Docker Hub neben PyPI** (2025-08-22, [`20250822 152323-4510C459`](../../../../../voice-memo-transcripts/20250822%20152323-4510C459.md))
> Auf Docker Hub auch noch neben PiPi und ein Container-Hochladen-Networker. Der hat SSA hat, wo man draufkommt, von Donauce ausführt. Heute geht's schon.

**Fertig machen, committen, hochladen** (2026-01-15, [`20260115 142010-85CD9D01`](../../../../../voice-memo-transcripts/20260115%20142010-85CD9D01.md))
> wirklich mal die sachen für den network auch kometen und hochladen fertig machen wirklich schade sind

---

## 13. Marketing, Vorträge, Community

**Repo öffentlich machen und pushen** (2025-11-15, [`20251115 132432-F7ECC6A4`](../../../../../voice-memo-transcripts/20251115%20132432-F7ECC6A4.md))
> veröffentlichen, dass man das Repo öffentlich ist. Einmal vom OT-Labs im TNLab-Channel, aber auch vielleicht irgendwo, dass man das in LinkedIn-Kampagne propagieren. Das andere wäre, dass man den Mikrotix-Channel usw. nav und so den Networker mal pushen.

**Slide im Vortrag** (2025-11-18, [`20251118 134052-A3251B2A`](../../../../../voice-memo-transcripts/20251118%20134052-A3251B2A.md))
> Auf jeden Fall vielleicht ein kurzes Thema vom Networker geben. Auf jeden Fall eine Slide rein vom Networker.

**Walkthrough / Video, wie man damit arbeitet** (2026-12-30, [`20261230 140747-DCAD0BA2`](../../../../../voice-memo-transcripts/20261230%20140747-DCAD0BA2.md))
> Einfach mal ein Walkthrough machen, wie ich mit dem Ding arbeite. Und ihnen zeigen, okay, so kann man damit arbeiten. Worktrees, ganzen Features, Skills, bla, was man alles dabei hat. Und einfach mal alles ausprobieren. Anhand so einem ISU-Networker und das aufzeigen.

**Artikel: wie man es zur Verfügung stellt — Codex, Skills, Git-Repo (?)** (2026-10-12, [`20261012 081044-29FBC88F`](../../../../../voice-memo-transcripts/20261012%20081044-29FBC88F.md))
> Ein Artikel kann ja auch darüber sein, wie man eben integrieren kann, dass man vielleicht, wenn man Mereven das jetzt hat, das weiß ich jedenfalls haben, Never-Rain LNA, Never-Rain Explorer und so weiter, dass man dann da einfach sagt, okay, was, was, wie stellen wir es zur Verfügung? Über Codex oder über das Hallogin oder über Skills, Git-Repo und so weiter.
