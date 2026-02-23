# csp.py (minimal) — only what you need for Map Coloring (CSP + Backtracking)

from __future__ import annotations

import random
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple
# APRIBOJIMAS colorA != colorB
ConstraintFn = Callable[[str, Any, str, Any], bool]


# -----------------------------
# Small helpers (no AIMA deps)
# -----------------------------

def first(seq):
    return next(iter(seq))


def count_true(items):
    return sum(1 for x in items if x)


def argmin_random_tie(seq, key):
    """Atsitiktinis tie-break, kai keli elementai turi tą patį minimumą."""
    best = None
    best_key = None
    for x in seq:
        k = key(x)
        if best is None or k < best_key:
            best, best_key = [x], k
        elif k == best_key:
            best.append(x)
    return random.choice(best)


# -----------------------------
# CSP core (minimal)
# -----------------------------

class CSP:
    # CSP KLASE: minimalus aprašymas žemėlapio spalvinimui
    def __init__(
        self,
        variables: List[str],
        domains: Dict[str, List[Any]],
        neighbors: Dict[str, List[str]],
        constraints: ConstraintFn,
    ):
        self.variables = variables              # REGIONAI
        self.domains = domains                  # GALIMOS SPALVOS
        self.neighbors = neighbors              # KAIMYNYSTĖS GRAFAS
        self.constraints = constraints          # APRIBOJIMAI (kaimynai negali turėti tos pačios spalvos)

        self.curr_domains: Optional[Dict[str, List[Any]]] = None  # naudojama (paieskos busena - sprendimu priemimui, atimti spalvas leistinos reiksmes) cia saugomos spalvos visiems aplinkiniams regionams inference (forward checking)
        self.nassigns = 0

    def assign(self, var: str, val: Any, assignment: Dict[str, Any]) -> None:
        assignment[var] = val
        self.nassigns += 1

    def unassign(self, var: str, assignment: Dict[str, Any]) -> None:
        if var in assignment:
            del assignment[var]

    def nconflicts(self, var: str, val: Any, assignment: Dict[str, Any]) -> int:
        """Kiek konfliktų turi var=val su jau nuspalvintais kaimynais."""
        conflicts = 0
        for n in self.neighbors.get(var, []):
            if n in assignment and not self.constraints(var, val, n, assignment[n]):
                conflicts += 1
        return conflicts

    # --- pruning support (minimal) ---

    def support_pruning(self) -> None:
        if self.curr_domains is None:
            self.curr_domains = {v: list(self.domains[v]) for v in self.variables}

    def suppose(self, var: str, value: Any) -> List[Tuple[str, Any]]:
        """
        Laikinas "suppose": var domeną paliekam tik [value],
        o pašalintas reikšmes grąžinam per restore(removals).
        """
        self.support_pruning()
        assert self.curr_domains is not None
        removals = [(var, v) for v in self.curr_domains[var] if v != value]
        self.curr_domains[var] = [value]
        return removals

    def prune(self, var: str, value: Any, removals: List[Tuple[str, Any]]) -> None:
        """Išmetam value iš var domeno (forward checking metu)."""
        assert self.curr_domains is not None
        if value in self.curr_domains[var]:
            self.curr_domains[var].remove(value)
            removals.append((var, value))

    def choices(self, var: str) -> List[Any]:
        """Jei yra curr_domains — naudojam juos, kitaip originalų domeną."""
        return (self.curr_domains or self.domains)[var]

    def restore(self, removals: List[Tuple[str, Any]]) -> None:
        """Atstatom pruning metu pašalintas reikšmes."""
        assert self.curr_domains is not None
        for var, value in removals:
            self.curr_domains[var].append(value)


# -----------------------------
# Heuristics (useful + minimal)
# -----------------------------

def first_unassigned_variable(assignment: Dict[str, Any], csp: CSP) -> str:
    """Paimam pirmą nepriskirtą regioną (paprasta strategija)."""
    return first([v for v in csp.variables if v not in assignment])


def num_legal_values(csp: CSP, var: str, assignment: Dict[str, Any]) -> int:
    """Kiek legalių spalvų dar turi var pagal esamą priskyrimą."""
    if csp.curr_domains is not None:
        # Jei inference jau apkarpė domenus, tai tiesiog domeno dydis
        return len(csp.curr_domains[var])
    # Kitu atveju skaičiuojam per konfliktus
    return count_true(csp.nconflicts(var, val, assignment) == 0 for val in csp.domains[var])


def mrv(assignment: Dict[str, Any], csp: CSP) -> str:
    """
    MRV: parenkam regioną su mažiausiai likusių legalių spalvų.
    Naudinga, nes greičiau aptinka aklavietes.
    """
    unassigned = [v for v in csp.variables if v not in assignment]
    return argmin_random_tie(unassigned, key=lambda v: num_legal_values(csp, v, assignment))


def unordered_domain_values(var: str, assignment: Dict[str, Any], csp: CSP) -> List[Any]:
    """Spalvas bandom tokia tvarka, kaip jos pateiktos domene."""
    return list(csp.choices(var))


def lcv(var: str, assignment: Dict[str, Any], csp: CSP) -> List[Any]:
    """
    LCV: pirmiau bandom spalvas, kurios sukelia mažiausiai konfliktų su kaimynais.
    """
    return sorted(csp.choices(var), key=lambda val: csp.nconflicts(var, val, assignment))


# -----------------------------
# Inference (minimal)
# -----------------------------

def no_inference(csp: CSP, var: str, value: Any, assignment: Dict[str, Any], removals: List[Tuple[str, Any]]) -> bool:
    return True


def forward_checking(csp: CSP, var: str, value: Any, assignment: Dict[str, Any], removals: List[Tuple[str, Any]]) -> bool:
    """
    Forward checking:
    Po var=value priskyrimo iš kaimynų domenų išmetam konfliktuojančias spalvas.
    Jei kaimynas lieka su tuščiu domenu -> aklavietė (False).
    """
    csp.support_pruning()
    assert csp.curr_domains is not None

    for B in csp.neighbors.get(var, []):
        if B in assignment:
            continue
        for b in list(csp.curr_domains[B]):
            if not csp.constraints(var, value, B, b):
                csp.prune(B, b, removals)
        if not csp.curr_domains[B]:
            return False
    return True


# -----------------------------
# Backtracking search (DFS)
# -----------------------------
#########################################################################################################[#2]
def backtracking_search(
    csp: CSP,
    select_unassigned_variable= mrv,
    order_domain_values     = lcv,
    inference               = forward_checking,
    trace: Optional[List[Dict[str, Any]]] = None,   # Jei paduosi [], kaups žingsnius vizualizacijai
    max_steps: Optional[int] = None,                # Apsauga, kad trace neišsipūstų
) -> Optional[Dict[str, Any]]:
    """
    Backtracking (DFS) mapos spalvinimui.
    trace įrašai: TRY, CONFLICT, ASSIGN, INFER_FAIL, BACKTRACK, GOAL
    """

    step = 0

    def log(event: str, assignment: Dict[str, Any], var: Optional[str] = None, val: Any = None):
        nonlocal step
        if trace is None:
            return
        step += 1
        if max_steps is not None and step > max_steps:
            raise RuntimeError(f"Trace exceeded max_steps={max_steps}.")
        trace.append({
            "step": step,
            "depth": len(assignment),
            "event": event,
            "var": var,
            "val": val,
            "assignment": dict(assignment),  # snapshot
        })
# assignment yra daline busena priskyrimas sudarytas is regiono ir spalvos
    #cia tikrina ar galine busena pasiekta
    ##########################################################################################[#4]
    def is_goal(assignment: Dict[str, Any]) -> bool:
        """Patikra: visi regionai priskirti ir nėra konfliktų."""
        if len(assignment) != len(csp.variables):
            return False
        return all(csp.nconflicts(v, assignment[v], assignment) == 0 for v in csp.variables)

    def backtrack(assignment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # Jei visi regionai nuspalvinti -> sprendinys
        # =========================
        # STEKAS (LIFO) – PUSH
        # =========================
        # Įeinam į naują rekursijos lygį (naujas "frame" Call Stack'e).
        # Įvestis: priskyrimas = dabartinis nuspalvinimas (dict).
        #
        # Pvz. pradžia:
        #   priskyrimas = {}
        #
        # Pvz. jau pažengus:
        #   priskyrimas = {'Vilniaus': 'R', 'Kauno': 'G'}
        ##########################################################################################[#5]
        if len(assignment) == len(csp.variables):
            # =========================
            # TIKSLAS (GOAL) – STEKAS POP (sėkmingas)
            # =========================
            # Reiškia: visi regionai turi spalvą.
            # Pvz. pilnas sprendinys galėtų atrodyti taip:
            #   {
            #     'Vilniaus': 'R',
            #     'Kauno': 'G',
            #     'Klaipėdos': 'B',
            #     'Šiaulių': 'Y',
            #     'Panevėžio': 'B',
            #     'Alytaus': 'Y',
            #     'Marijampolės': 'R',
            #     'Tauragės': 'G',
            #     'Telšių': 'R',
            #     'Utenos': 'G'
            #   }
            # Grąžinam aukštyn — visi steko frame'ai susipopo'ins automatiškai per return.

            log("GOAL", assignment)
            return dict(assignment)

            # regionas
        #čia parenkamas regionas per MRV euristika minimum remaining value paduodant parametrus, kad nustayti kuris regionas turi maziausiai galimu legaliu spalvu
        ##########################################################################################[#6]
        var = select_unassigned_variable(assignment, csp) # REGIONAS

            # Pasirenkam kitą nenuspalvintą regioną:
            # - su MRV: dažniau pasirinks tą, kuriam liko mažiausiai galimų spalvų.
            #
            # Pvz. jei priskyrimas:
            #   {'Vilniaus':'R', 'Kauno':'G', 'Utenos':'B'}
            # tai MRV gali parinkti 'Panevėžio', jei jam liko mažiausiai legalių spalvų.
            # spalva
        ##########################################################################################[#7]
        for value in order_domain_values(var, assignment, csp): # CIKLAS RIKIUOJANTIS SPALVAS (kiek konfliktų ši spalva sukeltų su jau nuspalvintais kaimynais, Grąžina surikiuotą sąrašą, ir tada for ciklas eina per jį nuo pradžios iki galo.)

            # Bandom spalvas LCV tvarka (pirmiau tos, kurios mažiausiai “užspaudžia” kaimynus).
            # Pvz. spalvos: 'R' -> 'G' -> 'B' -> 'Y'

            # -----------------------------------------
            # (1) AKLAVIETĖS TIPAS: "viskas konfliktuoja"
            # -----------------------------------------
            # Konfliktas reiškia: regionas gauna tokią pačią spalvą kaip bent vienas jau nuspalvintas kaimynas.
            #
            # Pvz. jei bandom regionas='Panevėžio' ir turim:
            #   priskyrimas = {'Šiaulių':'R', 'Kauno':'G', 'Utenos':'B'}
            # ir jei Panevėžys ribojasi su Šiauliais, Kaunu, Utena,
            # tada su 3 spalvom (RGB) Panevėžiui nelieka nieko:
            #   - bandai 'R' -> konfliktas su 'Šiaulių':'R'
            #   - bandai 'G' -> konfliktas su 'Kauno':'G'
            #   - bandai 'B' -> konfliktas su 'Utenos':'B'
            # => po ciklo grįšim su return None (aklavietė)

            log("TRY", assignment, var, value)
            ##########################################################################################[#8]
            if csp.nconflicts(var, value, assignment) != 0:
                # FILTRAS                Spalva tinka lokaliai (su dabartiniais kaimynais nekonfliktuoja)

                log("CONFLICT", assignment, var, value)
                continue
            #Priskyrimu saraso papildymas {Regionas: spalva}
            #########################################################################################[#9]
            csp.assign(var, value, assignment)
            # =========================
            # DUOMENYS PASIKEIČIA (priskyrimas padidėja)
            # =========================
            # Pvz. PRIEŠ:
            #   {'Vilniaus':'R', 'Kauno':'G'}
            # PO (pasirinkom regionas='Alytaus', spalva='B'):
            #   {'Vilniaus':'R', 'Kauno':'G', 'Alytaus':'B'}
            #
            # Tai yra DFS "einam gilyn" sprendimo šaka.
            log("ASSIGN", assignment, var, value)

            # atmestos, nes pagal apribojimus jos nebegali būti teisingos šiame paieškos žingsnyje.“
            #########################################################################################[#10]
            removals = csp.suppose(var, value) # Cia issaugomos atmestos reiskmes, jeigu reikes grizti zingsniu atgal,
            # Domenų “pririšimas”: regionui paliekam tik vieną spalvą,
            # o ką išmetėm – įrašom į pasalinimai (kad galėtume atstatyti).


            # Cia esminis patikrinimas ar po priskyrimu, nebus ateityje aklaviete spalvu priskyrimui - nebus galimu spalvu kaimynam, jei viskas ok tesiamas darbas su curr domain ir kitais regionais
            #########################################################################################[#11]
            ok = inference(csp, var, value, assignment, removals) #
            #---- L - I - F - O----#
            # -----------------------------------------
            # (2) AKLAVIETĖS TIPAS: inference padaro domeną tuščią
            # -----------------------------------------
            # MAC/AC3 gali išmesti spalvas iš kaimynų domenų.
            # Jei kuriam nors regionui domenas tampa tuščias => ok == False.
            #
            # Pvz. su 3 spalvom (RGB) po kelių priskyrimų gali nutikti:
            #   priskyrimas = {'Kauno':'R', 'Vilniaus':'G', 'Panevėžio':'B'}
            # o MAC nustato, kad kažkuriam kaimynui (tarkim 'Utenos') nebelieka nei R nei G nei B
            # (visos užblokuotos kaimynų) => domenas tuščias => ok=False => aklavietė.
            #########################################################################################[#12]
            if ok:
                # =========================
                # STEKAS (LIFO) – PUSH
                # =========================
                # Einam giliau su išplėstu priskyrimu.
                # Pvz. kviečiam:
                #   backtrack({'Vilniaus':'R','Kauno':'G','Alytaus':'B'})
                #stekas LIFO
                #########################################################################################[#13]
                result = backtrack(assignment) # CIA rekursija -> einam toliau
                if result is not None: # Jei viskas pavyko sekmingai
                    # =========================
                    # STEKAS – POP (sėkmė)
                    # =========================
                    # Jei gilumoje rado sprendinį – grąžinam jį aukštyn per visus lygius.

                    return result # Stekas grazina is giliausiausios sakos i pirmesne nes tenkina salyga not NONE <<<<<pasiekta galine busena kai tikrina len>>>>>
            else:
                log("INFER_FAIL", assignment, var, value)

            #########################################################################################[#14]
            # Jei ok==False (inference aklavietė) arba gilyn grįžo None:
            csp.restore(removals) # grizimas atgal pagal busena praejusia
            # =========================
            # DUOMENYS PASIKEIČIA (domenai atstatomi)
            # =========================
            # Atstatom visas inference/suppose metu išmestas galimas spalvas.

            csp.unassign(var, assignment) # atstatymas
            # =========================
            # DUOMENYS PASIKEIČIA (priskyrimas sumažėja)
            # =========================
            # Pvz. PRIEŠ:
            #   {'Vilniaus':'R','Kauno':'G','Alytaus':'B'}
            # PO:
            #   {'Vilniaus':'R','Kauno':'G'}
            #
            # Tai yra "backtracking": atšaukiam paskutinį sprendimą ir bandom kitą spalvą tame pačiame lygyje.

            log("BACKTRACK", assignment, var, value)

        # =========================
        # AKLAVIETĖ: jokios spalvos nebetinka – STEKAS POP (nesėkmė)
        # =========================
        # Pvz. jei regionas='Panevėžio' ir priskyrimas buvo:
        #   {'Šiaulių':'R','Kauno':'G','Utenos':'B'}
        # ir naudojam tik RGB,
        # tada visos 3 spalvos konfliktuoja => grįžtam None.

        return None #Where result becomes none
    #cia pagrindinis PIRMAS kvietimas ivyksta
    #sanity check
    ##########################################################################################[#3]
    result = backtrack({})
    if result is not None and not is_goal(result):
        raise AssertionError("Solver returned an invalid assignment.")
    return result


# -----------------------------
# Map Coloring helpers (essential)
# -----------------------------

def different_values_constraint(A: str, a: Any, B: str, b: Any) -> bool:
    """JEI A IR B YRA KAIMYNAI, JU SPALVOS TURI SKIRTIS."""
    return a != b


def parse_neighbors(neighbors: str) -> Dict[str, List[str]]:
    """
    Tekstas -> kaimynystės grafas.
    Pvz: "X: Y Z; Y: Z" -> {'X':['Y','Z'], 'Y':['X','Z'], 'Z':['X','Y']}
    """
    graph = defaultdict(list)
    specs = [spec.strip() for spec in neighbors.split(';') if spec.strip()]

    for spec in specs:
        if ':' not in spec:
            continue
        A, Aneigh = spec.split(':', 1)
        A = A.strip()
        for B in Aneigh.split():
            graph[A].append(B)
            graph[B].append(A)

    # unikalinam, kad nebūtų dublikatų
    return {k: sorted(set(v)) for k, v in graph.items()}


def MapColoringCSP(colors: List[Any], neighbors: Dict[str, List[str]] | str) -> CSP:
    """
    Sukuria CSP žemėlapio spalvinimui.
    colors: pvz ['R','G','B']
    neighbors: dict arba tekstas (parse_neighbors formatas)
    """
    if isinstance(neighbors, str):
        neighbors = parse_neighbors(neighbors)

    variables = list(neighbors.keys())
    domains = {v: list(colors) for v in variables}
    return CSP(variables, domains, neighbors, different_values_constraint)
