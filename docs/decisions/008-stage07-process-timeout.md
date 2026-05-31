# 008 — Stage 07: pebble.ProcessPool statt ProcessPoolExecutor für Worker-Timeouts

**Status:** accepted  
**Date:** 2026-05-31

## Context

Stage 07 (extract_refs) verarbeitet ~6 100 Gesetz-JSON-Dateien mit der
`legal-reference-extraction`-Bibliothek (refex) in einem Prozess-Pool.
Einige Gesetze lösen in refex einen Infinite Loop aus — vermutlich
Randfälle im internen Parser für bestimmte Zitatstrukturen.

Die ursprüngliche Implementierung nutzte `concurrent.futures.ProcessPoolExecutor`
mit `fut.result(timeout=120)`. Beim ersten vollständigen Pipeline-Lauf hing
Stage 07 nach ~95 % (alphabetisch kurz nach "wasmotrv") für mehr als 8 Stunden,
ohne `refs_raw.json` zu schreiben. Das `timeout`-Argument von `fut.result()` war
wirkungslos, weil es nur das **Warten** im Haupt-Thread abbricht — der Worker-Prozess
selbst bleibt im Infinite Loop am Leben. Alle Pool-Slots waren belegt, keine neuen
Tasks konnten starten.

### Warum es so lange dauerte, das zu erkennen

Der Hang war schwer zu diagnostizieren, weil zwei Faktoren gleichzeitig wirkten:

1. **WSL2 + `/mnt/c/`-Filesystem ist generell sehr langsam** für I/O mit vielen
   kleinen Dateien (9P-Netzwerkprotokoll zwischen Linux-VM und Windows-Host). Stage 07
   dauert auf diesem Setup legitim 30–90 Minuten — ein Hang sieht anfangs nicht anders
   aus als normaler Betrieb.

2. **Kein sichtbarer Fortschritt im Log.** Der Snakemake-Output für Stage 07 besteht
   nur aus `_log.warning()`-Meldungen einzelner Gesetze (CaseCitation-Fehler) und einem
   500er-Zähler. Da die Gesetze alphabetisch sortiert verarbeitet werden, fehlte jede
   Rückmeldung wie „X von 6124 fertig". Als der Pool hing, sah das Log einfach eingefroren
   aus — identisch mit einem momentan stillen, aber arbeitenden Pool.

3. **`kill` auf den Snakemake-Orchestrator tötete die Worker nicht.** Nach dem ersten
   `kill`-Versuch lief der Orchestrator-Prozess nicht mehr, aber die vier Worker-Prozesse
   blieben als Zombies am Leben und fraßen weiter CPU. Der zweite Pipeline-Lauf (mit dem
   naiven `fut.result(timeout=120)`-Fix) startete neue Worker zusätzlich zu den alten,
   was die Diagnose weiter erschwerte.

**Für zukünftige Runs:** Wenn Stage 07 nach 45 Minuten noch kein `refs_raw.json`
produziert hat und `ps aux | grep extract_refs` Worker mit hoher CPU-Zeit zeigt,
ist es ein Hang — nicht nur Langsamkeit. Dann mit `kill -9` auf alle Worker-PIDs
und Neustart mit diesem Fix.

## Decision

Ersatz von `concurrent.futures.ProcessPoolExecutor` durch **`pebble.ProcessPool`**
mit `pool.map(..., timeout=60)`.

`pebble` implementiert echte Prozess-Timeouts: beim Ablauf wird der Worker-Prozess
per SIGKILL beendet und ein neuer Prozess gestartet. Der Iterator über die Ergebnisse
wirft `concurrent.futures.TimeoutError` für das betroffene Gesetz; der Aufruf-Code
fängt das ab, loggt eine Warnung und macht weiter.

```python
from pebble import ProcessPool
from concurrent.futures import TimeoutError as FutureTimeoutError

with ProcessPool(max_workers=threads, initializer=init_extractor) as pool:
    future = pool.map(process_law_file, paths, timeout=60)
    it = future.result()
    for slug in slugs:
        try:
            refs = next(it)
        except FutureTimeoutError:
            _log.warning("timeout in %s — skipped", slug)
        except Exception as exc:
            _log.warning("error in %s: %s", slug, exc)
```

## Alternatives considered

- **`fut.result(timeout=N)` mit ProcessPoolExecutor** — abgelehnt: bricht nur den
  Warteaufruf ab, der Worker-Prozess läuft weiter und belegt seinen Pool-Slot dauerhaft.

- **`multiprocessing.Pool` mit `apply_async().get(timeout=N)`** — gleiches Problem:
  der Worker-Prozess wird nicht terminiert, nur der Warteaufruf gibt auf. Zusätzlich
  müssten alle Futures vor der Schleife submitted werden, was den Code unübersichtlicher
  macht.

- **Subprocess-pro-Gesetz** (`subprocess.run(..., timeout=30)`) — würde echte Kills
  liefern, aber ~6 100 Prozess-Starts verlangsamen Stage 07 erheblich und erfordern
  eine umständliche JSON-über-stdout-Serialisierung.

- **Problemgesetze identifizieren und blacklisten** — fragil: neue GII-Versionen
  könnten weitere Fälle einführen; ein generisches Timeout ist robuster.

## Consequences

- `pebble` ist neue Dependency in `pipeline/pyproject.toml`.
- Gesetze, die nach 60 Sekunden nicht fertig sind, werden übersprungen (kein Ref-Verlust
  im kritischen Pfad, da solche Gesetze typischerweise Sonderfälle mit ungewöhnlichem
  Zitatformat sind).
- Der 60s-Timeout ist konservativ; auf langsamer Hardware (WSL2 + /mnt/c/) ist das
  ausreichend für alle nicht-hängenden Gesetze (~1–5 s/Gesetz im Normalfall).
- Bei einem vollständigen Neu-Lauf auf der WSL2-/mnt/c/-Filesystem-Kombination ist
  Stage 07 trotzdem langsam (~30–90 min); auf einem nativen Linux-Dateisystem
  (z. B. `~/repos/`) wäre es deutlich schneller.
