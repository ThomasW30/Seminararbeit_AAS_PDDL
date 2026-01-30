# GitHub Upload Anleitung

Diese Anleitung beschreibt, wie der `Seminararbeit_AAS_UPF` Ordner auf GitHub hochgeladen wird.

## Voraussetzungen

- Git installiert
- GitHub Account vorhanden
- Terminal/Command Prompt geöffnet

## Schritt-für-Schritt Anleitung

### 1. Git-Repository initialisieren

```bash
cd Seminararbeit_AAS_UPF
git init
```

Dies erstellt ein neues Git-Repository im Ordner.

### 2. .gitignore erstellen

Erstelle eine Datei `.gitignore` mit folgendem Inhalt:

```
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
.DS_Store
*.egg-info/
dist/
build/
.venv/
venv/
```

Dies verhindert, dass Python-Cache-Dateien und andere temporäre Dateien hochgeladen werden.

### 3. Dateien zum Git-Staging hinzufügen

```bash
git add .
```

Dies fügt alle Dateien zum Staging-Bereich hinzu.

### 4. Ersten Commit erstellen

```bash
git commit -m "Initial commit: AAS zu PDDL Transformation"
```

Alternativ mit ausführlicherer Commit-Message:

```bash
git commit -m "Initial commit: AAS zu PDDL Transformation

- Implementierung der AAS zu PDDL Transformation
- MPS500 Produktionssystem Beispiel
- Mini-Beispiel für Veranschaulichung
- Unified Planning Framework Integration
- Fast Downward Solver"
```

### 5. GitHub Repository erstellen

1. Gehe zu [github.com](https://github.com)
2. Klicke auf "New repository" (grüner Button oben rechts)
3. Repository-Einstellungen:
   - **Name**: z.B. `Seminararbeit_AAS_PDDL` oder `AAS_UPF_Transformation`
   - **Description**: `Automatische Transformation von Asset Administration Shells (AAS) zu PDDL mit Unified Planning Framework`
   - **Visibility**:
     - **Public**: Öffentlich sichtbar
     - **Private**: Nur für dich und eingeladene Personen sichtbar
   - **WICHTIG**:
     - ❌ **NICHT** "Add a README file" anklicken
     - ❌ **NICHT** ".gitignore" auswählen
     - ❌ **NICHT** "Choose a license" auswählen
     - (Diese Dateien existieren bereits lokal)
4. Klicke auf "Create repository"

### 6. Remote hinzufügen und pushen

Nach dem Erstellen des Repositories zeigt GitHub dir Befehle an. Verwende die folgenden Befehle (ersetze `DEIN_USERNAME` und `REPOSITORY_NAME`):

```bash
git remote add origin https://github.com/DEIN_USERNAME/REPOSITORY_NAME.git
git branch -M main
git push -u origin main
```

**Beispiel:**
```bash
git remote add origin https://github.com/ThomasW30/Seminararbeit_AAS_PDDL.git
git branch -M main
git push -u origin main
```

### 7. Authentifizierung

Beim ersten Push wirst du nach Authentifizierung gefragt:
- **Username**: Dein GitHub Username
- **Password**: Dein Personal Access Token (NICHT dein GitHub Passwort!)

**Personal Access Token erstellen (falls noch nicht vorhanden):**
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)"
3. Scopes auswählen: `repo` (voller Zugriff auf Repositories)
4. Token generieren und SICHER SPEICHERN (wird nur einmal angezeigt!)

## Fertig!

Dein Repository ist jetzt auf GitHub verfügbar unter:
```
https://github.com/DEIN_USERNAME/REPOSITORY_NAME
```

## Weitere Änderungen pushen (später)

Wenn du später Änderungen machst:

```bash
git add .
git commit -m "Beschreibung der Änderungen"
git push
```

## Zusammenfassung

```bash
# Alle Befehle auf einmal (zum Kopieren)
cd Seminararbeit_AAS_UPF
git init
git add .
git commit -m "Initial commit: AAS zu PDDL Transformation"
git remote add origin https://github.com/DEIN_USERNAME/REPOSITORY_NAME.git
git branch -M main
git push -u origin main
```

## Hinweise

- Der Ordner `pddl/output/` und `pddl/solutions/` sind leer - das ist normal, sie werden beim Ausführen des Skripts gefüllt
- Die AASX-Dateien sind binäre Dateien - sie werden trotzdem hochgeladen
- Bei Problemen: `git status` zeigt den aktuellen Status an
- Bei Fragen zu Git: `git --help` oder spezifisch `git commit --help`
