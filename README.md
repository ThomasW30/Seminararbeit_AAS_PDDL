# AAS zu PDDL Transformation mit Unified Planning Framework

Dieses Projekt implementiert eine automatische Transformation von Asset Administration Shells (AAS) nach PDDL (Planning Domain Definition Language) und nutzt das Unified Planning Framework (UPF) zur Lösung von Planungsproblemen.

## Überblick

Das System liest AASX-Dateien (AAS Exchange Format), extrahiert Planungsinformationen aus den Submodels und generiert daraus:
- PDDL Domain und Problem Dateien
- UPF-basierte Problemlösungen
- Ausführbare Aktionssequenzen

## Voraussetzungen

- Python >= 3.8 (empfohlen: 3.10 oder 3.12)
- pip (Python Package Manager)

## Installation

```bash
pip install -r requirements.txt
```

Installiert folgende Bibliotheken:
- `basyx-python-sdk==2.0.0` - AAS Modellierung und AASX-Verarbeitung
- `unified_planning==1.3.0` - Planungs-Framework
- `up-fast-downward==0.5.2` - Fast Downward PDDL Solver

## Verwendung

### Standard-Ausführung (MPS500 Beispiel)
```bash
python generate_and_solve_upf.py
```

Das Skript sucht automatisch nach `*Combined*.aasx` Dateien im `aasx_output/` Ordner und verarbeitet diese.

### Explizite AASX-Datei angeben
```bash
python generate_and_solve_upf.py --input aasx_output/MPS500_Combined_All_AAS.aasx
```

### Ausgabe-Verzeichnis anpassen
```bash
python generate_and_solve_upf.py --output meine_loesungen/
```

## Ordnerstruktur

```
Seminararbeit_AAS_UPF/
├── README.md                           # Diese Datei
├── requirements.txt                    # Python Dependencies
├── generate_and_solve_upf.py          # Hauptskript (AAS → PDDL → Lösung)
│
├── aasx_output/                       # MPS500 Produktionssystem
│   ├── MPS500_Combined_All_AAS.aasx  # Kombinierte AASX (alle AAS)
│   ├── CarrierAAS.aasx               # Einzelne Component AAS
│   ├── ConveyorBeltAAS.aasx
│   ├── ProcessingStationAAS.aasx
│   └── ...
│
├── mini_example/                      # Vereinfachtes Beispiel
│   ├── MiniSystem_Combined.aasx      # (Für Veranschaulichung in Hausarbeit)
│   ├── CarrierAAS.aasx
│   └── ...
│
└── pddl/
    ├── output/                        # Generierte PDDL Dateien
    │   ├── mps500_domain.pddl        # MPS500 PDDL Domain
    │   └── mps500_problem.pddl       # MPS500 PDDL Problem
    └── solutions/                     # Lösungen
        └── solution_UPF_20260130_005507.txt  # MPS500 Lösung (128 Aktionen)
```

## Verfügbare PDDL-Dateien

Das Repository enthält bereits generierte PDDL-Dateien für das MPS500-Beispiel:

### Domain & Problem
- **[pddl/output/mps500_domain.pddl](pddl/output/mps500_domain.pddl)** - PDDL Domain für MPS500 Produktionssystem
- **[pddl/output/mps500_problem.pddl](pddl/output/mps500_problem.pddl)** - PDDL Problem Instance

### Lösung
- **[pddl/solutions/solution_UPF_20260130_005507.txt](pddl/solutions/solution_UPF_20260130_005507.txt)** - Berechnete Lösung mit 128 Aktionen

Diese Dateien wurden automatisch aus den AASX-Dateien im `aasx_output/` Ordner generiert und mit dem Fast Downward Solver gelöst.
```

## Beispiele

### MPS500 Produktionssystem
Das vollständige MPS500 Beispiel (`aasx_output/`) demonstriert ein realitätsnahes Produktionssystem mit:
- Trägern (Carrier)
- Förderbändern (Conveyor Belts)
- Bearbeitungsstationen (Processing Stations)
- Lagern (Warehouses)
- Qualitätskontrolle (Quality Control)
- Versandbereich (Shipping)

**Ausführung:**
```bash
python generate_and_solve_upf.py
```

### Mini-Beispiel
Das vereinfachte Mini-Beispiel (`mini_example/`) zeigt die grundlegende AAS-Struktur mit:
- 1 Träger (Carrier)
- 2 Förderbändern (Conveyors)
- 1 Produkt (Product)
- 1 Station (Station)

**Hinweis:** Das Mini-Beispiel dient zur Veranschaulichung der AAS-Struktur in der Hausarbeit. Das Hauptskript ist für das MPS500-Beispiel optimiert.

## Ausgabe

Nach erfolgreicher Ausführung werden folgende Dateien generiert:

### 1. PDDL Domain (`pddl/output/[Name]_domain.pddl`)
- Typen-Hierarchie
- Prädikate (Fluents)
- Aktionen (Process Operators)

### 2. PDDL Problem (`pddl/output/[Name]_problem.pddl`)
- Objekte (Instances)
- Initial State
- Goal State

### 3. Lösung (`pddl/solutions/solution_UPF_[timestamp].txt`)
- Aktionssequenz
- Metadaten (AASX-Quelle, Domain-Name, Solving-Zeit)
- Status (SOLVED_SATISFICING, etc.)

### Beispiel-Ausgabe:
```
======================================================================
UPF PROBLEM AUFGEBAUT
======================================================================
  Domain:     MPS500_Planungssystem
  Typen:      8
  Fluents:    15
  Aktionen:   12
  Objekte:    25
  Goals:      3

[PDDL] Export nach: pddl/output/
  [OK] MPS500_Planungssystem_domain.pddl
  [OK] MPS500_Planungssystem_problem.pddl

[UPF] Solving mit Fast Downward...
  Status: SOLVED_SATISFICING
  Aktionen: 128
  Solver-Zeit: 0.45s

[OK] Lösung gespeichert: pddl/solutions/solution_UPF_20260130_123456.txt
```

## Architektur

Das Skript ist in 4 Hauptklassen strukturiert:

1. **AASLoader** - Lädt AASX-Dateien und löst Referenzen auf
2. **AASExtractor** - Extrahiert Planungsdaten aus AAS Submodels
3. **UPFProblemBuilder** - Baut UPF-Problemobjekte auf
4. **PlanSolver** - Löst das Problem mit Fast Downward

## Lizenz

Dieses Projekt wurde im Rahmen einer Seminararbeit an der Helmut-Schmidt-Universität Hamburg erstellt.

## Kontakt

Bei Fragen oder Problemen wenden Sie sich bitte an den Autor der Seminararbeit.
