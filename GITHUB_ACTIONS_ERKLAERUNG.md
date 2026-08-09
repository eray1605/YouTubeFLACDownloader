# GitHub Actions & Builds — Erklärt

## Was sind GitHub Builds?

Stell dir vor, du hast einen Roboter, der jedes Mal wenn du Code hochlädst automatisch Aufgaben für dich erledigt. **Das ist GitHub Actions.**

Normalerweise musst du deine App **manuell** auf deinem PC bauen:
```bash
pyinstaller --onefile main.py
```
Das Problem: Du sitzt auf **Windows**. Du kannst keine `.app` für Mac oder eine Linux-Binary bauen — PyInstaller baut immer nur für das aktuelle Betriebssystem.

**GitHub Actions löst das:** GitHub hat Server mit Windows, macOS und Linux. Du sagst GitHub: *"Bau meine App auf allen 3 Systemen"* — und GitHub macht das automatisch für dich. Kostenlos.

---

## Wie funktioniert das?

### 1. Die Workflow-Datei

Alles beginnt mit **einer einzigen YAML-Datei** im Ordner:
```
dein-repo/
└── .github/
    └── workflows/
        └── build.yml       ← Diese Datei steuert alles
```

GitHub schaut automatisch in `.github/workflows/` — jede `.yml`-Datei dort ist ein Workflow.

---

### 2. Aufbau einer Workflow-Datei (Schritt für Schritt)

Hier ist unsere `build.yml` erklärt:

#### 🔹 Wann soll der Workflow starten?

```yaml
on:
  push:
    tags:
      - "v*"
```

**Bedeutung:** Der Workflow startet nur, wenn ein Git-Tag gepusht wird, das mit `v` anfängt (z.B. `v1.0.0`, `v1.1.2`).

Andere Möglichkeiten wären:
```yaml
on:
  push:
    branches: [main]        # Bei jedem Push auf main
  pull_request:              # Bei jedem Pull Request
  workflow_dispatch:         # Manuell per Knopfdruck
```

#### 🔹 Berechtigungen

```yaml
permissions:
  contents: write
```

Der Workflow darf Releases erstellen und Dateien hochladen.

#### 🔹 Die Build-Matrix

```yaml
jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: windows-latest
            name: Windows
            artifact: YT-Music-Downloader-Windows
          - os: macos-latest
            name: macOS
            artifact: YT-Music-Downloader-macOS
          - os: ubuntu-latest
            name: Linux
            artifact: YT-Music-Downloader-Linux
```

**Das ist das Herzstück.** Eine **Matrix** bedeutet: GitHub führt den gleichen Job **3x parallel** aus — einmal auf Windows, einmal auf macOS, einmal auf Linux.

- `fail-fast: false` → Wenn Windows fehlschlägt, laufen macOS und Linux trotzdem weiter
- `os` → Welches Betriebssystem der GitHub-Server nutzen soll
- `artifact` → Name der fertigen ZIP-Datei

#### 🔹 Die Steps (Schritte)

Jeder Job besteht aus **Steps** — das sind die einzelnen Befehle:

```yaml
steps:
  # 1. Code aus dem Repo herunterladen
  - uses: actions/checkout@v4

  # 2. Python installieren
  - uses: actions/setup-python@v5
    with:
      python-version: "3.11"

  # 3. FFmpeg installieren (je nach OS anders)
  - name: Install FFmpeg (Linux)
    if: runner.os == 'Linux'
    run: sudo apt-get update && sudo apt-get install -y ffmpeg

  - name: Install FFmpeg (macOS)
    if: runner.os == 'macOS'
    run: brew install ffmpeg

  - name: Install FFmpeg (Windows)
    if: runner.os == 'Windows'
    run: choco install ffmpeg -y

  # 4. Python-Pakete installieren
  - run: pip install customtkinter yt-dlp Pillow requests pyinstaller

  # 5. App bauen mit PyInstaller
  - run: pyinstaller --onefile --noconsole --name "YTMusicDownloader" main.py

  # 6. Als ZIP verpacken
  # 7. Als Artifact hochladen
  # 8. GitHub Release erstellen
```

**Wichtige Konzepte:**

| Konzept | Bedeutung |
|---------|-----------|
| `uses:` | Benutzt eine fertige Action von GitHub (z.B. Python installieren) |
| `run:` | Führt einen Shell-Befehl aus |
| `if:` | Bedingung — nur auf bestimmtem OS ausführen |
| `shell:` | Welche Shell benutzt wird (bash, powershell) |
| `working-directory:` | In welchem Ordner der Befehl ausgeführt wird |

#### 🔹 Artifacts & Releases

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: ${{ matrix.name }}
    path: ${{ matrix.artifact }}.zip
```

Ein **Artifact** ist eine Datei, die beim Build entsteht und hochgeladen wird. Am Ende sammelt der **Release-Job** alle Artifacts ein und erstellt ein GitHub Release mit Download-Links.

---

## Was habe ich konkret gemacht?

### Schritt 1: Workflow-Datei erstellt
```
.github/workflows/build.yml
```
Diese Datei sagt GitHub, was zu tun ist.

### Schritt 2: Committed und gepusht
```bash
git add .github/workflows/build.yml
git commit -m "Add cross-platform build workflow"
git push origin master
```

### Schritt 3: Git-Tag erstellt
```bash
git tag v1.1.2          # Tag lokal erstellen
git push origin v1.1.2  # Tag zu GitHub pushen → Workflow startet!
```

**Wichtig:** Der Workflow startet erst wenn der **Tag** gepusht wird, nicht beim normalen Push.

### Schritt 4: Fehler gefixt (Trial & Error)

| Version | Problem | Lösung |
|---------|---------|--------|
| v1.1.0 | FFmpeg nicht im PATH auf Windows | PowerShell PATH manuell neu laden |
| v1.1.1 | `pyinstaller` Befehl nicht gefunden (Windows) | `python -m PyInstaller` benutzt stattdessen |
| v1.1.2 | Finale funktionierende Version | Kombination aller Fixes |

---

## Wie triggert man einen neuen Build?

Wenn du Änderungen machst und einen neuen Build willst:

```bash
# 1. Änderungen committen & pushen
git add .
git commit -m "Meine Änderungen"
git push origin master

# 2. Neuen Tag erstellen (Versionsnummer hochzählen!)
git tag v1.2.0
git push origin v1.2.0

# 3. GitHub Actions baut automatisch → Release erscheint
```

---

## Wichtige Git-Tag-Regeln

```bash
git tag v1.0.0           # Tag erstellen
git push origin v1.0.0   # Tag pushen (startet Build)

git tag                   # Alle Tags anzeigen
git tag -d v1.0.0         # Tag lokal löschen
git push origin :v1.0.0   # Tag remote löschen
```

**Semantic Versioning:** `v1.2.3`
- `1` = Major (große Änderungen, nicht rückwärtskompatibel)
- `2` = Minor (neue Features)
- `3` = Patch (Bugfixes)

---

## Übersicht: Der gesamte Flow

```
Du pushst Tag v1.2.0
        │
        ▼
GitHub erkennt: "v*" Tag → Workflow starten!
        │
        ▼
┌───────────────────────────────────────┐
│         3 Jobs starten parallel       │
├─────────────┬───────────┬─────────────┤
│  Windows    │  macOS    │  Linux      │
│  Server     │  Server   │  Server     │
├─────────────┼───────────┼─────────────┤
│ 1. Checkout │ 1. ...    │ 1. ...      │
│ 2. Python   │ 2. ...    │ 2. ...      │
│ 3. FFmpeg   │ 3. ...    │ 3. ...      │
│ 4. pip      │ 4. ...    │ 4. ...      │
│ 5. Build    │ 5. ...    │ 5. ...      │
│ 6. ZIP      │ 6. ...    │ 6. ...      │
│ 7. Upload   │ 7. ...    │ 7. ...      │
└──────┬──────┴─────┬─────┴──────┬──────┘
       │            │            │
       ▼            ▼            ▼
   .exe ZIP     Unix ZIP    Linux ZIP
       │            │            │
       └────────────┼────────────┘
                    ▼
           GitHub Release v1.2.0
           mit allen 3 ZIP-Dateien
```

---

## Nützliche Links

- [GitHub Actions Dokumentation](https://docs.github.com/en/actions)
- [Workflow Syntax Referenz](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [PyInstaller Dokumentation](https://pyinstaller.org/en/stable/)
- [Semantic Versioning](https://semver.org/)
