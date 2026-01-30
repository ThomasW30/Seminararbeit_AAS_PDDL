"""
UPF Problem Builder aus AAS
============================

Baut ein Planungsproblem direkt als UPF-Objekt aus der kombinierten AASX-Datei
und loest es mit dem integrierten Fast Downward Planner.

Struktur:
- AASLoader:          AASX laden, AAS-Rollen erkennen, Referenzen aufloesen
- AASExtractor:       Daten aus AAS-Submodels extrahieren (Typen, Praedikate, Aktionen, etc.)
- UPFProblemBuilder:  Extrahierte Daten in UPF-Objekte umwandeln
- PlanSolver:         UPF-Problem loesen und Ergebnis speichern

Verwendet:
- BaSyx Python SDK (basyx.aas) fuer AAS-Zugriff
- Unified Planning Framework (UPF) fuer Planungsproblem und Solver
"""

from basyx.aas import model
from basyx.aas.adapter.aasx import AASXReader
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import argparse

import unified_planning as up
from unified_planning.shortcuts import (
    UserType, BoolType, Fluent, InstantaneousAction, Object, Problem,
    OneshotPlanner, Not
)
from unified_planning.io import PDDLWriter


# =============================================================================
# Klasse 1: AASLoader - AASX laden & Referenzen aufloesen
# =============================================================================

class AASLoader:
    """Laedt eine AASX-Datei und stellt BaSyx-Zugriffsmethoden bereit."""

    def __init__(self, aasx_path: Path):
        self.aasx_path = aasx_path
        self.obj_store = None
        self.all_aas = []
        self.component_aas_list = []

        # Planning Configuration (aus System-AAS)
        self.domain_name: str = None
        self.problem_name: str = None
        self.requirements: List[str] = ["strips", "typing"]

    def load_aasx(self):
        """Laedt die AASX-Datei und filtert Komponenten-AAS."""
        print("=" * 80)
        print("AASLoader - Lade AASX")
        print("=" * 80)

        with AASXReader(str(self.aasx_path)) as reader:
            self.obj_store = model.DictObjectStore()
            reader.read_into(object_store=self.obj_store, file_store=None)

        self.all_aas = [obj for obj in self.obj_store if isinstance(obj, model.AssetAdministrationShell)]

        for aas in self.all_aas:
            if self._get_aas_role(aas) == "component":
                self.component_aas_list.append(aas)

        print(f"\n[OK] Geladen: {len(self.component_aas_list)} Komponenten-AAS (von {len(self.all_aas)} gesamt)")
        for aas in self.component_aas_list:
            print(f"  - {aas.id_short}")
        print()

        self._extract_planning_configuration()

    def _get_aas_role(self, aas: model.AssetAdministrationShell) -> str:
        """Bestimmt die Rolle einer AAS (system oder component)."""
        for sm_ref in aas.submodel:
            sm = self.obj_store.get(sm_ref.get_identifier())
            if sm and sm.id_short == 'TechnicalData':
                for elem in sm.submodel_element:
                    if elem.id_short == 'AASRole' and isinstance(elem, model.Property):
                        return elem.value

        if "System" in aas.id_short:
            print(f"  [WARNUNG] AAS '{aas.id_short}' hat kein AASRole Property, verwende Fallback")
            return "system"
        return "component"

    def _extract_planning_configuration(self):
        """Extrahiert Planning Configuration aus System-AAS oder leitet sie vom Dateinamen ab."""
        print("=" * 80)
        print("[0] PLANNING CONFIGURATION EXTRAKTION")
        print("=" * 80)

        system_aas = next((aas for aas in self.all_aas if self._get_aas_role(aas) == "system"), None)

        if not system_aas:
            # Fallback: Domain Name aus AASX-Dateinamen ableiten
            derived_name = self.aasx_path.stem  # "mps500.aasx" -> "mps500"
            self.domain_name = derived_name
            self.problem_name = derived_name
            print(f"  [INFO] Keine System-AAS gefunden")
            print(f"  [INFO] Domain Name abgeleitet aus Dateinamen: {self.domain_name}")
            print()
            return

        planning_config_found = False
        for sm_ref in system_aas.submodel:
            sm = self.obj_store.get(sm_ref.get_identifier())
            if sm and sm.id_short == 'PlanningConfiguration':
                planning_config_found = True
                print(f"  [OK] PlanningConfiguration gefunden in {system_aas.id_short}")

                for elem in sm.submodel_element:
                    if elem.id_short == 'domainName' and isinstance(elem, model.Property):
                        self.domain_name = elem.value
                        print(f"    Domain Name: {self.domain_name}")
                    elif elem.id_short == 'problemName' and isinstance(elem, model.Property):
                        self.problem_name = elem.value
                        print(f"    Problem Name: {self.problem_name}")
                    elif elem.id_short == 'requirements' and isinstance(elem, model.SubmodelElementCollection):
                        self.requirements = []
                        for req_prop in elem.value:
                            if isinstance(req_prop, model.Property):
                                self.requirements.append(req_prop.value)
                        print(f"    Requirements: {', '.join(self.requirements)}")
                print()
                break

        if not planning_config_found:
            # Fallback 1: SoftwareNameplate -> SoftwareNameplateInstance -> InstanceName (IDTA 02007-1-0)
            for sm_ref in system_aas.submodel:
                sm = self.obj_store.get(sm_ref.get_identifier())
                if sm and sm.id_short == 'SoftwareNameplate':
                    for elem in sm.submodel_element:
                        # Suche in SoftwareNameplateInstance SMC
                        if elem.id_short == 'SoftwareNameplateInstance' and isinstance(elem, model.SubmodelElementCollection):
                            for sub_elem in elem.value:
                                if sub_elem.id_short == 'InstanceName' and isinstance(sub_elem, model.Property):
                                    self.domain_name = sub_elem.value
                                    self.problem_name = sub_elem.value
                                    print(f"  [OK] Domain Name aus SoftwareNameplate/SoftwareNameplateInstance/InstanceName: {self.domain_name}")
                                    print()
                                    return

            # Fallback 2: Domain Name aus AASX-Dateinamen ableiten
            derived_name = self.aasx_path.stem
            self.domain_name = derived_name
            self.problem_name = derived_name
            print(f"  [INFO] Domain Name abgeleitet aus Dateinamen: {self.domain_name}")
            print()
            return

        if not self.domain_name:
            raise ValueError("domainName fehlt in PlanningConfiguration!")
        if not self.problem_name:
            self.problem_name = self.domain_name
            print(f"  [INFO] problemName fehlt, verwende domain_name: {self.problem_name}")

    def get_component_submodels(self, submodel_name: str):
        """Gibt alle Submodels mit dem gegebenen Namen aus Komponenten-AAS zurueck."""
        submodels = []
        for aas in self.component_aas_list:
            for sm_ref in aas.submodel:
                sm = self.obj_store.get(sm_ref.get_identifier())
                if sm and sm.id_short == submodel_name:
                    submodels.append(sm)
        return submodels

    def resolve_predicate_reference(self, ref_element: model.ReferenceElement) -> str:
        """Folgt einer predicateDefinitionRef zur Predicate-Definition und liest den predicate_name."""
        if not ref_element.value or not ref_element.value.key:
            raise ValueError("ReferenceElement hat keine Keys!")

        keys = ref_element.value.key
        if len(keys) < 2:
            raise ValueError(f"predicateDefinitionRef hat ungueltige Struktur: {len(keys)} Keys (erwartet: >=2)")

        submodel_id = keys[0].value
        predicate_id_short = keys[1].value

        predicate_submodel = self.obj_store.get(submodel_id)
        if not predicate_submodel:
            raise KeyError(f"PredicateDefinitions Submodell nicht gefunden: {submodel_id}")

        predicate_element = None
        for elem in predicate_submodel.submodel_element:
            if elem.id_short == predicate_id_short:
                predicate_element = elem
                break

        if not predicate_element:
            raise KeyError(f"Predicate Element '{predicate_id_short}' nicht gefunden in {predicate_submodel.id_short}")

        if isinstance(predicate_element, model.SubmodelElementCollection):
            for prop in predicate_element.value:
                if prop.id_short == 'predicateName' and isinstance(prop, model.Property):
                    return prop.value

        raise KeyError(f"predicateName Property nicht gefunden in '{predicate_id_short}'")

    def resolve_parameter_reference(self, ref_element: model.ReferenceElement) -> str:
        """Folgt einer parameterBindingRef zur ProcessParameter-Definition und liest die Variable."""
        if not ref_element.value or not ref_element.value.key:
            raise ValueError("ReferenceElement hat keine Keys!")

        keys = ref_element.value.key
        if len(keys) < 4:
            raise ValueError(f"parameterBindingRef hat ungueltige Struktur: {len(keys)} Keys (erwartet: >=4)")

        submodel_id = keys[0].value
        process_op_id = keys[1].value
        param_id = keys[3].value

        capabilities_sm = self.obj_store.get(submodel_id)
        if not capabilities_sm:
            raise KeyError(f"Capabilities Submodell nicht gefunden: {submodel_id}")

        process_operator = None
        for elem in capabilities_sm.submodel_element:
            if elem.id_short == process_op_id:
                process_operator = elem
                break

        if not process_operator:
            raise KeyError(f"ProcessOperator '{process_op_id}' nicht gefunden in {capabilities_sm.id_short}")

        process_params = None
        for elem in process_operator.value:
            if elem.id_short == 'ProcessParameters':
                process_params = elem
                break

        if not process_params:
            raise KeyError(f"ProcessParameters nicht gefunden in {process_op_id}")

        for param_smec in process_params.value:
            if param_smec.id_short == param_id:
                for prop in param_smec.value:
                    if prop.id_short == 'Property' and isinstance(prop, model.Property):
                        return prop.value

        raise KeyError(f"Parameter '{param_id}' nicht gefunden in ProcessParameters")


# =============================================================================
# Klasse 2: AASExtractor - Daten aus AAS-Submodels extrahieren
# =============================================================================

class AASExtractor:
    """Extrahiert Planungsdaten aus AAS-Submodels in einfache Datenstrukturen."""

    def __init__(self, loader: AASLoader):
        self.loader = loader

    def extract_type_hierarchy(self) -> Dict[str, Optional[str]]:
        """Liest TypeHierarchy aus AAS. Gibt {type_name: parent_name} zurueck."""
        print("=" * 80)
        print("[1] TYPEN EXTRAHIEREN")
        print("=" * 80)

        hierarchy = {}  # type_name -> parent_name (None = Root)

        def extract_from_entity(entity: model.Entity, parent_name: str = None):
            type_name = entity.id_short
            hierarchy[type_name] = parent_name
            for statement in entity.statement:
                if isinstance(statement, model.Entity):
                    extract_from_entity(statement, type_name)

        for sm in self.loader.get_component_submodels('TypeHierarchy'):
            for elem in sm.submodel_element:
                if isinstance(elem, model.Entity) and elem.id_short == "EntryNode":
                    for statement in elem.statement:
                        if isinstance(statement, model.Entity):
                            extract_from_entity(statement, None)
                    break

        print(f"  [OK] {len(hierarchy)} Typen extrahiert")
        for name, parent in hierarchy.items():
            if parent:
                print(f"    {name} -> {parent}")
            else:
                print(f"    {name} (Root)")
        print()

        return hierarchy

    def extract_predicate_definitions(self) -> List[Dict]:
        """Liest PredicateDefinitions aus AAS.

        Gibt Liste von Dicts zurueck:
        [{'name': str, 'params': [{'var': str, 'type': str}]}]
        """
        print("=" * 80)
        print("[2] PRAEDIKATE EXTRAHIEREN")
        print("=" * 80)

        predicates = []

        for sm in self.loader.get_component_submodels('PredicateDefinitions'):
            for elem in sm.submodel_element:
                if isinstance(elem, model.SubmodelElementCollection):
                    pred = self._extract_predicate(elem)
                    if pred and not any(p['name'] == pred['name'] for p in predicates):
                        predicates.append(pred)

        print(f"  [OK] {len(predicates)} Praedikate extrahiert")
        for p in predicates:
            params_str = ", ".join([f"{pr['var']}: {pr['type']}" for pr in p['params']])
            print(f"    {p['name']}({params_str})")
        print()

        return predicates

    def _extract_predicate(self, pred_smec: model.SubmodelElementCollection) -> Optional[Dict]:
        """Extrahiert ein einzelnes Praedikat aus einer SubmodelElementCollection."""
        pred_name = None
        params = []

        for elem in pred_smec.value:
            if elem.id_short == 'predicateName':
                pred_name = elem.value
            elif elem.id_short == 'parameters':
                for param_smec in elem.value:
                    param_var = None
                    param_type = None
                    for prop in param_smec.value:
                        if prop.id_short == 'Property':
                            param_var = prop.value
                        elif prop.id_short == 'Type':
                            param_type = prop.value
                    if param_var and param_type:
                        params.append({'var': param_var, 'type': param_type})

        if pred_name:
            return {'name': pred_name, 'params': params}
        return None

    def extract_process_operators(self) -> List[Dict]:
        """Liest Capabilities/ProcessOperators aus AAS.

        Gibt Liste von Dicts zurueck:
        [{'name': str, 'params': [{'var': str, 'type': str}],
          'preconditions': [condition_dict], 'effects': [condition_dict]}]
        """
        print("=" * 80)
        print("[3] AKTIONEN EXTRAHIEREN")
        print("=" * 80)

        operators = []

        for sm in self.loader.get_component_submodels('Capabilities'):
            for elem in sm.submodel_element:
                if isinstance(elem, model.SubmodelElementCollection):
                    op = self._extract_operator(elem)
                    if op:
                        operators.append(op)

        print(f"  [OK] {len(operators)} Aktionen extrahiert")
        for op in operators:
            print(f"    {op['name']} ({len(op['preconditions'])} Pre, {len(op['effects'])} Eff)")
        print()

        return operators

    def _extract_operator(self, op_smec: model.SubmodelElementCollection) -> Optional[Dict]:
        """Extrahiert einen ProcessOperator aus einer SubmodelElementCollection.

        Die Rolle (Precondition/Effect) wird ueber expressionGoal bestimmt:
        - expressionGoal == "Requirement" -> Precondition
        - expressionGoal == "Assurance"   -> Effect
        """
        action_name = None
        param_defs = []
        preconditions = []
        effects = []

        # Alle Conditions aus hasInput und hasOutput sammeln
        all_conditions_smecs = []

        for elem in op_smec.value:
            if elem.id_short == 'Name':
                action_name = elem.value
            elif elem.id_short == 'ProcessParameters':
                for param_smec in elem.value:
                    param_var = None
                    param_type = None
                    for prop in param_smec.value:
                        if prop.id_short == 'Property':
                            param_var = prop.value
                        elif prop.id_short == 'Type':
                            param_type = prop.value
                    if param_var and param_type:
                        param_defs.append({'var': param_var, 'type': param_type})
            elif elem.id_short in ('hasInput', 'hasOutput'):
                for cond_smec in elem.value:
                    all_conditions_smecs.append(cond_smec)

        # Conditions nach expressionGoal sortieren
        for cond_smec in all_conditions_smecs:
            cond = self._extract_condition(cond_smec)
            if cond:
                if cond['expression_goal'] == 'Requirement':
                    preconditions.append(cond)
                elif cond['expression_goal'] == 'Assurance':
                    effects.append(cond)

        if not action_name:
            return None

        return {
            'name': action_name,
            'params': param_defs,
            'preconditions': preconditions,
            'effects': effects
        }

    def _extract_condition(self, cond_smec: model.SubmodelElementCollection) -> Optional[Dict]:
        """Extrahiert eine Condition aus InstanceDescription.

        Liest expressionGoal (Requirement/Assurance) fuer die Rollenzuweisung.
        """
        predicate_name = None
        expression_goal = None
        interpretation_logic = None
        param_bindings = []

        for elem in cond_smec.value:
            if isinstance(elem, model.SubmodelElementCollection) and elem.id_short == 'InstanceDescription':
                for desc_elem in elem.value:
                    if desc_elem.id_short == 'predicateDefinitionRef' and isinstance(desc_elem, model.ReferenceElement):
                        predicate_name = self.loader.resolve_predicate_reference(desc_elem)
                    elif desc_elem.id_short == 'expressionGoal':
                        expression_goal = desc_elem.value
                    elif desc_elem.id_short == 'interpretationLogic':
                        interpretation_logic = desc_elem.value
                    elif desc_elem.id_short == 'parameterBindingRefs':
                        for ref_elem in desc_elem.value:
                            if isinstance(ref_elem, model.ReferenceElement):
                                variable = self.loader.resolve_parameter_reference(ref_elem)
                                if variable:
                                    param_bindings.append(variable)

        if not predicate_name:
            return None

        return {
            'predicate': predicate_name,
            'expression_goal': expression_goal,
            'interpretation_logic': interpretation_logic,
            'param_refs': param_bindings
        }

    def extract_instances(self) -> List[Dict]:
        """Liest Instances aus AAS. Gibt [{'name': str, 'type': str}] zurueck."""
        print("=" * 80)
        print("[4] INSTANZEN EXTRAHIEREN")
        print("=" * 80)

        instances = []

        for sm in self.loader.get_component_submodels('Instances'):
            for elem in sm.submodel_element:
                if isinstance(elem, model.SubmodelElementCollection):
                    instance_name = None
                    instance_type = None
                    for prop in elem.value:
                        if prop.id_short == 'instanceName' and isinstance(prop, model.Property):
                            instance_name = prop.value
                        elif prop.id_short == 'instanceType' and isinstance(prop, model.Property):
                            instance_type = prop.value
                    if instance_name and instance_type:
                        instances.append({'name': instance_name, 'type': instance_type})

        print(f"  [OK] {len(instances)} Instanzen extrahiert")
        for inst in instances:
            print(f"    {inst['name']} : {inst['type']}")
        print()

        return instances

    def extract_initial_states_and_goals(self):
        """Liest alle States aus AAS und sortiert nach expressionGoal.

        expressionGoal == "ActualValue"  -> InitialState
        expressionGoal == "Requirement"  -> Goal

        Gibt (init_states, goals) zurueck.
        """
        print("=" * 80)
        print("[5+6] STATES EXTRAHIEREN (ueber expressionGoal)")
        print("=" * 80)

        init_states = []
        goals = []

        # Alle States aus InitialStates und Goals sammeln
        for sm in self.loader.get_component_submodels('Instances'):
            for inst_smec in sm.submodel_element:
                if isinstance(inst_smec, model.SubmodelElementCollection):
                    for elem in inst_smec.value:
                        if isinstance(elem, model.SubmodelElementCollection) and elem.id_short in ('InitialStates', 'Goals'):
                            for state_smec in elem.value:
                                state = self._extract_state(state_smec)
                                if state:
                                    if state['expression_goal'] == 'ActualValue':
                                        init_states.append(state)
                                    elif state['expression_goal'] == 'Requirement':
                                        goals.append(state)

        print(f"\n  Initial States (ActualValue): {len(init_states)}")
        for s in init_states:
            bindings_str = ", ".join([f"{k}={v}" for k, v in s['bindings'].items()])
            print(f"    {s['predicate']}({bindings_str})")

        print(f"\n  Goals (Requirement): {len(goals)}")
        for g in goals:
            bindings_str = ", ".join([f"{k}={v}" for k, v in g['bindings'].items()])
            print(f"    {g['predicate']}({bindings_str})")

        if not goals:
            print("  [WARNUNG] Keine Goals gefunden")

        print()
        return init_states, goals

    def _extract_state(self, state_smec: model.SubmodelElementCollection) -> Optional[Dict]:
        """Extrahiert einen State aus einer SubmodelElementCollection.

        Liest expressionGoal (ActualValue/Requirement) fuer die Rollenzuweisung.
        """
        predicate_name = None
        expression_goal = None
        param_bindings = {}

        for elem in state_smec.value:
            if isinstance(elem, model.ReferenceElement) and elem.id_short == 'predicateDefinitionRef':
                predicate_name = self.loader.resolve_predicate_reference(elem)
            elif isinstance(elem, model.Property) and elem.id_short == 'expressionGoal':
                expression_goal = elem.value
            elif isinstance(elem, model.SubmodelElementCollection) and elem.id_short == 'parameterBindings':
                for binding_smec in elem.value:
                    param = None
                    value = None
                    for prop in binding_smec.value:
                        if prop.id_short == 'parameter':
                            param = prop.value
                        elif prop.id_short == 'value':
                            value = prop.value
                    if param and value:
                        param_bindings[param] = value

        if not predicate_name or not param_bindings:
            return None

        return {
            'predicate': predicate_name,
            'expression_goal': expression_goal,
            'bindings': param_bindings
        }


# =============================================================================
# Klasse 3: UPFProblemBuilder - UPF-Objekte erzeugen
# =============================================================================

class UPFProblemBuilder:
    """Wandelt extrahierte AAS-Daten in UPF-Objekte um."""

    def __init__(self, domain_name: str):
        self.problem = Problem(domain_name)
        self.type_map: Dict[str, UserType] = {}
        self.fluent_map: Dict[str, Fluent] = {}
        self.object_map: Dict[str, Object] = {}
        self._predicate_param_order: Dict[str, List[str]] = {}

    def build_types(self, hierarchy: Dict[str, Optional[str]]):
        """Erzeugt UPF UserType-Objekte aus der Typ-Hierarchie."""
        print("=" * 80)
        print("[1] UPF TYPEN AUFBAUEN (UserType)")
        print("=" * 80)

        processed = set()

        # "object" ist in PDDL implizit, braucht keinen UPF-Type
        if "object" in hierarchy:
            processed.add("object")

        # Iterativ: erzeuge Types deren Parent bereits erzeugt wurde
        changed = True
        while changed:
            changed = False
            for type_name, parent_name in hierarchy.items():
                if type_name in processed:
                    continue

                if parent_name is None or parent_name == "object":
                    self.type_map[type_name] = UserType(type_name)
                    processed.add(type_name)
                    print(f"  + {type_name} (Root)")
                    changed = True
                elif parent_name in self.type_map:
                    self.type_map[type_name] = UserType(type_name, father=self.type_map[parent_name])
                    processed.add(type_name)
                    print(f"  + {type_name} -> {parent_name}")
                    changed = True

        print(f"\n[OK] {len(self.type_map)} UPF-Typen erzeugt\n")

    def build_fluents(self, predicate_defs: List[Dict]):
        """Erzeugt UPF Fluent-Objekte aus Praedikat-Definitionen."""
        print("=" * 80)
        print("[2] UPF FLUENTS AUFBAUEN (Fluent)")
        print("=" * 80)

        for pred in predicate_defs:
            pred_name = pred['name']
            params = {}
            param_order = []

            for p in pred['params']:
                clean_var = p['var'].lstrip('?')
                if p['type'] not in self.type_map:
                    raise KeyError(f"Type '{p['type']}' fuer Fluent '{pred_name}' nicht gefunden!")
                params[clean_var] = self.type_map[p['type']]
                param_order.append(p['var'])

            fluent = Fluent(pred_name, BoolType(), **params)
            self.fluent_map[pred_name] = fluent
            self.problem.add_fluent(fluent, default_initial_value=False)
            self._predicate_param_order[pred_name] = param_order

            params_str = ", ".join([f"{v}: {t}" for v, t in params.items()])
            print(f"  + {pred_name}({params_str})")

        print(f"\n[OK] {len(self.fluent_map)} UPF-Fluents erzeugt\n")

    def build_actions(self, operators: List[Dict]):
        """Erzeugt UPF InstantaneousAction-Objekte aus ProcessOperators."""
        print("=" * 80)
        print("[3] UPF AKTIONEN AUFBAUEN (InstantaneousAction)")
        print("=" * 80)

        for op in operators:
            self._build_action(op)

        print(f"\n[OK] {len(self.problem.actions)} UPF-Aktionen erzeugt\n")

    def _build_action(self, operator: Dict):
        """Erzeugt eine einzelne UPF-Aktion aus einem Operator-Dict."""
        action_name = operator['name']

        # Parameter erzeugen
        action_params = {}
        for p in operator['params']:
            clean_var = p['var'].lstrip('?')
            if p['type'] not in self.type_map:
                raise KeyError(f"Type '{p['type']}' fuer Action '{action_name}' nicht gefunden!")
            action_params[clean_var] = self.type_map[p['type']]

        action = InstantaneousAction(action_name, **action_params)

        # Mapping von ?var -> UPF-Parameter-Objekt
        var_to_param = {}
        for p in operator['params']:
            clean_var = p['var'].lstrip('?')
            var_to_param[p['var']] = action.parameter(clean_var)

        # Preconditions
        for cond in operator['preconditions']:
            fluent = self.fluent_map[cond['predicate']]
            fluent_args = [var_to_param[v] for v in cond['param_refs']]
            fluent_call = fluent(*fluent_args)

            if cond['interpretation_logic'] == 'NotEqual':
                action.add_precondition(Not(fluent_call))
            else:
                action.add_precondition(fluent_call)

        # Effects
        for eff in operator['effects']:
            fluent = self.fluent_map[eff['predicate']]
            fluent_args = [var_to_param[v] for v in eff['param_refs']]
            fluent_call = fluent(*fluent_args)

            if eff['interpretation_logic'] == 'NotEqual':
                action.add_effect(fluent_call, False)
            else:
                action.add_effect(fluent_call, True)

        self.problem.add_action(action)
        print(f"  + {action_name} ({len(operator['preconditions'])} Pre, {len(operator['effects'])} Eff)")

    def build_objects(self, instances: List[Dict]):
        """Erzeugt UPF Object-Objekte aus Instanzen."""
        print("=" * 80)
        print("[4] UPF OBJEKTE AUFBAUEN (Object)")
        print("=" * 80)

        for inst in instances:
            if inst['type'] not in self.type_map:
                raise KeyError(f"Type '{inst['type']}' fuer Instanz '{inst['name']}' nicht gefunden!")
            obj = Object(inst['name'], self.type_map[inst['type']])
            self.object_map[inst['name']] = obj
            self.problem.add_object(obj)
            print(f"  + {inst['name']} : {inst['type']}")

        print(f"\n[OK] {len(self.object_map)} UPF-Objekte erzeugt\n")

    def build_init(self, initial_states: List[Dict]):
        """Setzt UPF Initial Values aus extrahierten States."""
        print("=" * 80)
        print("[5] UPF INITIAL STATE AUFBAUEN (set_initial_value)")
        print("=" * 80)

        count = 0
        for state in initial_states:
            pred_name = state['predicate']
            if pred_name not in self.fluent_map:
                raise KeyError(f"Praedikat '{pred_name}' nicht in Fluent-Map gefunden!")
            if pred_name not in self._predicate_param_order:
                raise KeyError(f"Parameter-Reihenfolge fuer '{pred_name}' nicht bekannt!")

            fluent = self.fluent_map[pred_name]
            param_order = self._predicate_param_order[pred_name]

            args = []
            for var in param_order:
                if var not in state['bindings']:
                    raise ValueError(f"Parameter '{var}' fehlt in Bindings fuer Praedikat '{pred_name}'!")
                obj_name = state['bindings'][var]
                if obj_name not in self.object_map:
                    raise KeyError(f"Objekt '{obj_name}' nicht in Object-Map gefunden!")
                args.append(self.object_map[obj_name])

            self.problem.set_initial_value(fluent(*args), True)
            args_str = " ".join([a.name for a in args])
            print(f"  + ({pred_name} {args_str})")
            count += 1

        print(f"\n[OK] {count} Initial Values gesetzt\n")

    def build_goals(self, goals: List[Dict]):
        """Setzt UPF Goals aus extrahierten Goal-States."""
        print("=" * 80)
        print("[6] UPF GOALS AUFBAUEN (add_goal)")
        print("=" * 80)

        count = 0
        for goal in goals:
            pred_name = goal['predicate']
            if pred_name not in self.fluent_map:
                raise KeyError(f"Praedikat '{pred_name}' nicht in Fluent-Map gefunden!")

            fluent = self.fluent_map[pred_name]
            param_order = self._predicate_param_order[pred_name]

            args = []
            for var in param_order:
                if var not in goal['bindings']:
                    raise ValueError(f"Parameter '{var}' fehlt in Goal-Bindings fuer Praedikat '{pred_name}'!")
                obj_name = goal['bindings'][var]
                if obj_name not in self.object_map:
                    raise KeyError(f"Objekt '{obj_name}' nicht in Object-Map gefunden!")
                args.append(self.object_map[obj_name])

            self.problem.add_goal(fluent(*args))
            args_str = " ".join([a.name for a in args])
            print(f"  + ({pred_name} {args_str})")
            count += 1

        print(f"\n[OK] {count} Goals gesetzt\n")

    def export_pddl(self, output_dir: Path):
        """Exportiert das UPF-Problem als PDDL Domain- und Problem-Dateien (via UPF PDDLWriter)."""
        print("=" * 80)
        print("PDDL EXPORT (via UPF PDDLWriter)")
        print("=" * 80)

        output_dir.mkdir(exist_ok=True, parents=True)

        domain_name = self.problem.name
        domain_file = output_dir / f"{domain_name}_domain.pddl"
        problem_file = output_dir / f"{domain_name}_problem.pddl"

        writer = PDDLWriter(self.problem, needs_requirements=True)
        writer.write_domain(str(domain_file))
        writer.write_problem(str(problem_file))

        print(f"  [OK] Domain:  {domain_file}")
        print(f"  [OK] Problem: {problem_file}")
        print()


# =============================================================================
# Klasse 4: PlanSolver - Problem loesen & Ergebnis speichern
# =============================================================================

class PlanSolver:
    """Loest ein UPF-Problem und speichert das Ergebnis."""

    def solve(self, problem: Problem, output_dir: Path = None, metadata: Dict = None):
        """Loest das UPF-Problem mit Fast Downward."""
        print("=" * 80)
        print("LOESE PLANUNGSPROBLEM (Fast Downward via UPF)")
        print("=" * 80)

        with OneshotPlanner(name='fast-downward') as planner:
            result = planner.solve(problem)

            print(f"\n[RESULT] Status: {result.status}")

            if result.status == up.engines.results.PlanGenerationResultStatus.SOLVED_SATISFICING:
                print("[OK] Loesung gefunden!\n")
                print("=" * 80)
                print("PLAN")
                print("=" * 80)

                if result.plan is not None:
                    plan_steps = []
                    for i, action in enumerate(result.plan.actions, 1):
                        step = f"{i}. {action}"
                        print(step)
                        plan_steps.append(step)

                    print(f"\n[INFO] Gesamtzahl Aktionen: {len(result.plan.actions)}")

                    if output_dir:
                        self._save_solution(result, plan_steps, problem, output_dir, metadata)

            elif result.status == up.engines.results.PlanGenerationResultStatus.UNSOLVABLE_PROVEN:
                print("[FEHLER] Problem ist bewiesen unloesbar!")
            elif result.status == up.engines.results.PlanGenerationResultStatus.UNSOLVABLE_INCOMPLETELY:
                print("[WARNUNG] Planner konnte keine Loesung finden (unvollstaendige Suche)")
            elif result.status == up.engines.results.PlanGenerationResultStatus.TIMEOUT:
                print("[WARNUNG] Planner Timeout")
            else:
                print(f"[WARNUNG] Unerwarteter Status: {result.status}")

        return result

    def _save_solution(self, result, plan_steps: List[str], problem: Problem,
                       output_dir: Path, metadata: Dict = None):
        """Speichert die Loesung in eine Textdatei."""
        output_dir.mkdir(exist_ok=True, parents=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"solution_UPF_{timestamp}.txt"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("UPF SOLUTION - Direkt aus AAS generiert\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generiert: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if metadata:
                for key, value in metadata.items():
                    f.write(f"{key}: {value}\n")
            f.write(f"Planner: Fast Downward (via UPF)\n")
            f.write(f"Status: {result.status}\n\n")
            f.write(f"Statistik:\n")
            f.write(f"  - Objekte: {len(problem.all_objects)}\n")
            f.write(f"  - Fluents: {len(problem.fluents)}\n")
            f.write(f"  - Aktionen: {len(problem.actions)}\n")
            f.write(f"  - Initial Values: {len(problem.initial_values)}\n")
            f.write(f"  - Loesungsschritte: {len(result.plan.actions)}\n\n")
            f.write("=" * 80 + "\n")
            f.write("LOESUNGSPLAN\n")
            f.write("=" * 80 + "\n\n")
            f.write("\n".join(plan_steps))
            f.write(f"\n\n")
            f.write("=" * 80 + "\n")
            f.write("ENDE DER LOESUNG\n")
            f.write("=" * 80 + "\n")

        print(f"\n[OK] Loesung gespeichert: {output_file}")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Baut UPF-Planungsproblem aus AAS und loest es direkt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python generate_and_solve_upf.py
  python generate_and_solve_upf.py --input my_system.aasx
  python generate_and_solve_upf.py --input system.aasx --output solutions/
        """
    )

    parser.add_argument(
        '--input', '-i',
        type=str,
        default=None,
        help='Pfad zur kombinierten AASX-Datei (Standard: Auto-Detection im aasx_output/ Ordner)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default='pddl/solutions',
        help='Output-Verzeichnis fuer Loesungsdateien (Standard: pddl/solutions/)'
    )

    args = parser.parse_args()

    # Bestimme Input-Pfad
    if args.input:
        aasx_path = Path(args.input)
        if not aasx_path.exists():
            print(f"[FEHLER] Input-Datei nicht gefunden: {aasx_path}")
            exit(1)
    else:
        base_path = Path(__file__).parent
        aasx_folder = base_path / "aasx_output"

        if not aasx_folder.exists():
            print(f"[FEHLER] Ordner nicht gefunden: {aasx_folder}")
            print("Fuehren Sie zuerst die AAS-Generierung aus:")
            print("  python create_aas_from_json.py")
            print("  python create_combined_aasx.py")
            exit(1)

        combined_files = list(aasx_folder.glob("*Combined*.aasx"))
        if combined_files:
            aasx_path = combined_files[0]
            print(f"[AUTO] Verwende gefundene Combined AASX: {aasx_path.name}")
        else:
            aasx_files = list(aasx_folder.glob("*.aasx"))
            if len(aasx_files) == 1:
                aasx_path = aasx_files[0]
                print(f"[AUTO] Verwende einzige gefundene AASX: {aasx_path.name}")
            elif len(aasx_files) == 0:
                print(f"[FEHLER] Keine AASX-Datei gefunden in {aasx_folder}")
                exit(1)
            else:
                print(f"[FEHLER] Mehrere AASX-Dateien gefunden in {aasx_folder}:")
                for f in aasx_files:
                    print(f"  - {f.name}")
                print("\nBitte geben Sie eine explizit an mit --input")
                exit(1)

    output_dir = Path(args.output)
    pddl_output_dir = Path("pddl/output")

    # 1. AAS laden
    loader = AASLoader(aasx_path)
    loader.load_aasx()

    # 2. Daten extrahieren
    extractor = AASExtractor(loader)
    hierarchy = extractor.extract_type_hierarchy()
    predicates = extractor.extract_predicate_definitions()
    operators = extractor.extract_process_operators()
    instances = extractor.extract_instances()
    init_states, goals = extractor.extract_initial_states_and_goals()

    # 3. UPF-Problem aufbauen
    builder = UPFProblemBuilder(loader.domain_name)
    builder.build_types(hierarchy)
    builder.build_fluents(predicates)
    builder.build_actions(operators)
    builder.build_objects(instances)
    builder.build_init(init_states)
    builder.build_goals(goals)

    print("=" * 80)
    print("UPF PROBLEM AUFGEBAUT")
    print("=" * 80)
    print(f"  Domain:     {builder.problem.name}")
    print(f"  Typen:      {len(builder.type_map)}")
    print(f"  Fluents:    {len(builder.fluent_map)}")
    print(f"  Aktionen:   {len(builder.problem.actions)}")
    print(f"  Objekte:    {len(builder.object_map)}")
    print(f"  Goals:      {len(builder.problem.goals)}")
    print()

    # 4. PDDL exportieren
    builder.export_pddl(pddl_output_dir)

    # 5. Loesen
    solver = PlanSolver()
    result = solver.solve(
        builder.problem,
        output_dir,
        metadata={
            'AASX': str(aasx_path),
            'Domain': loader.domain_name,
            'Problem': loader.problem_name
        }
    )

    print("\n" + "=" * 80)
    print("FERTIG")
    print("=" * 80)
