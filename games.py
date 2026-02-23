"""
Tik TicTacToe (AIMA 5 skyriaus logika supaprastinta iki vieno žaidimo).

Šis failas turi:
- Game bazinę klasę su play_game()
- TicTacToe žaidimą (būsena = GameState)
- Minimax ir Alpha-Beta paieškas
- Paprastus žaidėjus (random, query, minimax, alpha-beta)

Būsenos (GameState) duomenys:
- to_move  : kieno eilė ('X' arba 'O')
- utility  : užkoduota nauda iš X perspektyvos (1 X laimi, -1 O laimi, 0 kita)
- board    : dict {(x,y): 'X'/'O'} užpildyti langeliai
- moves    : list[(x,y)] likę legalūs ėjimai
"""

from __future__ import annotations
from collections import namedtuple
import random
from math import inf
from typing import Callable, List, Tuple, Dict, Optional

Move = Tuple[int, int]
Board = Dict[Move, str]

GameState = namedtuple("GameState", "to_move utility board moves")


# =========================================================
# Game bazė (kad TicTacToe turėtų play_game)
# =========================================================

class Game:
    """
    Bazinė žaidimo klasė.
    TicTacToe paveldi šitą klasę, todėl gauna play_game().
    """

    #Kordinatės legalies veiksmas
    def actions(self, state: GameState) -> List[Move]:
        raise NotImplementedError
    #Išveda nauja būsena
    def result(self, state: GameState, move: Move) -> GameState:
        raise NotImplementedError
    #Įvertinimas būsenos naudingumo
    def utility(self, state: GameState, player: str) -> int:
        raise NotImplementedError
    #patikrinimas paskutinio veiksmo
    def terminal_test(self, state: GameState) -> bool:
        # Terminalas jei nėra legalų ėjimų (arba žaidimas laimėtas)
        return not self.actions(state)
    #Kurio zaidejo ejimas
    def to_move(self, state: GameState) -> str:
        return state.to_move
    #Vaizdas
    def display(self, state: GameState) -> None:
        print(state)
    #Whole match loop
    def play_game(self, *players: Callable[["Game", GameState], Optional[Move]]) -> int:
        """
        Paleidžia pilną žaidimą.
        - state pradeda nuo self.initial
        - kiekvienas player funkcija parenka ėjimą
        - state = result(state, move)
        - jei terminal_test -> baigiam ir grąžinam utility X perspektyvoje

        Duomenų pasikeitimas kiekvienam ėjimui:
        - board papildomas nauju (x,y)->'X'/'O'
        - moves sutrumpėja (pašalinamas panaudotas ėjimas)
        - to_move persijungia ('X' <-> 'O')
        - utility gali tapti 1/-1 jei kažkas laimi
        """
        state = self.initial #Pradedame žaidima nuo pradines busenos
        while True: #Ciklas
            #[4] zaidedeju funkcijos paleidziamas
            for player_fn in players: #Zaideijo funkcijos
                move = player_fn(self, state)#Dabartinio zaidejo funkcija paleidzia veiksma kuris is minimax sugrazina koordinates
                state = self.result(state, move)  # NAUJA būsena po ėjimo #[6] is tu korodinaciu sukuriamas naujas state

                if self.terminal_test(state):#Tikrina ar zaidimas baigtas [8] ar baigtas?
                    self.display(state)#Prrintina final busena [9] rodyti
                    return self.utility(state, "X")  # grąžinam rezultatą X perspektyvoje [10] kas laimejo


# =========================================================
# Minimax (DFS per žaidimo būsenų medį)
# =========================================================

def minmax_decision(state: GameState, game: Game) -> Optional[Move]:
    """
    GameState - cia dabartine zaidimo busenam, game interface su zaidimo taisyklemis
    Minimax sprendimas: parenka geriausią ėjimą MAX žaidėjui (tam, kas dabar juda).
    TicTacToe atveju MAX laikom "player" (dabartinis state.to_move).
    """
    #zaidejo nustatymas state - saugo zzaidedeja, to_mov perduoda is game
    player = game.to_move(state)############################################## 1
    #ciklas visiem veiksmam cia vyksta busenos ivertinimo palankumas -1 0 1
    def max_value(s: GameState) -> int:
        # Jei pabaiga – grąžinam final state
        if game.terminal_test(s):
            return game.utility(s, player)
        v = -inf # pati blogiausia reiksme ieskat geriausiops
        for a in game.actions(s): #eina per visus galimnus ejimus
            v = max(v, min_value(game.result(s, a)))#Cia simuliuojama galima busena,ir lyginami busenu rezultatai isvedaant kiekvienai busenai auksciausia imanoma rezultata
        return int(v) #max reiskme
    #tas pats principas skirtas isvesti maziausia reiksme is esamos busenos
    def min_value(s: GameState) -> int:
        if game.terminal_test(s):
            return game.utility(s, player)
        v = inf
        for a in game.actions(s):
            v = min(v, max_value(game.result(s, a)))
        return int(v) #min reiskme

    # Parenkam ėjimą, kuris duoda didžiausią "min_value" (nes po mūsų eis MIN)
    moves = game.actions(state) #sarasas legaliu veiksmu/busenu ############################################# 2
    if not moves:
        return None # jei nieko nera
    #3
    return max(moves, key=lambda a: min_value(game.result(state, a))) # Grąžina ėjimą (a), kurio įvertinimas (key) yra didžiausias

    # 1. Apskaičiuojame vertes visiems ėjimams
    scored_moves = [(a, min_value(game.result(state, a))) for a in moves]

    # 2. Randame geriausią vertę (pvz. 1)
    best_score = max(score for a, score in scored_moves)

    # 3. Atrenkame visus ėjimus, kurie turi tą vertę, ir pasirenkame atsitiktinį
    best_moves = [a for a, score in scored_moves if score == best_score]
    return random.choice(best_moves)


def alpha_beta_search(state: GameState, game: Game) -> Optional[Move]:
    """
    Alpha-beta pruning: tas pats kaip minimax, tik greičiau,
    nes nupjauna šakas, kurios negali pagerinti rezultato.
    """
    player = game.to_move(state)

    def max_value(s: GameState, alpha: float, beta: float) -> int:
        if game.terminal_test(s):
            return game.utility(s, player)
        v = -inf
        for a in game.actions(s):
            v = max(v, min_value(game.result(s, a), alpha, beta)) # Cia nustatoma dabartines busenos alpha ir beta geriausia reiksme
            if v >= beta: # jei sakos verte didesne ties ja ir apsistosiem
                return int(v)  # pjūvis (beta cut)
            alpha = max(alpha, v)
        return int(v)

    def min_value(s: GameState, alpha: float, beta: float) -> int:
        if game.terminal_test(s):
            return game.utility(s, player)
        v = inf
        for a in game.actions(s):
            v = min(v, max_value(game.result(s, a), alpha, beta))
            if v <= alpha:
                return int(v)  # pjūvis (alpha cut)
            beta = min(beta, v)
        return int(v)

    best_score = -inf
    beta = inf
    best_action = None

    for a in game.actions(state):
        v = min_value(game.result(state, a), best_score, beta)
        if v > best_score:
            best_score = v
            best_action = a

    return best_action


# =========================================================
# Žaidėjai (player funkcijos)
# =========================================================

def query_player(game: Game, state: GameState) -> Optional[Move]:
    """
    Žmogus įveda ėjimą.
    Pvz įvedimas: (1, 1)
    """
    print("Dabartinė būsena:")
    game.display(state)
    print("Legalūs ėjimai:", game.actions(state))
    if not game.actions(state):
        return None
    move_string = input("Tavo ėjimas? ")
    try:
        return eval(move_string)  # paprasta, bet ne saugu realiam projekte
    except Exception:
        return None


def random_player(game: Game, state: GameState) -> Optional[Move]:
    """Atsitiktinis legalus ėjimas."""
    moves = game.actions(state)
    return random.choice(moves) if moves else None


def minmax_player(game: Game, state: GameState) -> Optional[Move]:
    """Žaidėjas, kuris renkasi minimax sprendimą."""
    return minmax_decision(state, game)#[5] cia pateikiakama daline busena tiksliau move coords


def alpha_beta_player(game: Game, state: GameState) -> Optional[Move]:
    """Žaidėjas, kuris renkasi alpha-beta sprendimą."""
    return alpha_beta_search(state, game)


# =========================================================
# TicTacToe žaidimas
# =========================================================

class TicTacToe(Game):#[1] - > Obejtkas sukuriamas
    """
    TicTacToe ant h x v lentos, reikia k iš eilės laimėti.
    Koordinatės: (x, y) nuo 1 iki h/v (kaip AIMA kode).

    State keičiasi per result():
    - į board įrašomas (move -> to_move)
    - iš moves pašalinamas move
    - to_move persijungia į kitą žaidėją
    - utility perskaičiuojamas pagal paskutinį ėjimą
    """

    def __init__(self, h: int = 3, v: int = 3, k: int = 3):
        self.h = h
        self.v = v
        self.k = k

        # Pradinis legalų ėjimų sąrašas (visi langeliai tušti)
        moves: List[Move] = [(x, y) for x in range(1, h + 1) for y in range(1, v + 1)]

        # Pradinė būsena: X pradeda, lenta tuščia, utility=0
        self.initial = GameState(to_move="X", utility=0, board={}, moves=moves) #[2] - > Pradine busena
    #galimi ejimai
    def actions(self, state: GameState) -> List[Move]:
        """Legalūs ėjimai = visi likę tušti langeliai (state.moves)."""
        return list(state.moves)
    #naujos busenos ikelimas
    def result(self, state: GameState, move: Optional[Move]) -> GameState:
        """
        Sukuria naują būseną po ėjimo.

        Duomenų pokyčiai:
        - board kopijuojamas (nes state yra "immutable" namedtuple)
        - board[move] = 'X' arba 'O'
        - move pašalinamas iš moves
        - to_move perjungiamas
        - utility atnaujinamas (jei šitas ėjimas laimėjo)
        """
        if move is None or move not in state.moves:
            # Neteisingas ėjimas – grąžinam tą pačią būseną
            return state

        board: Board = dict(state.board)  # kopija
        board[move] = state.to_move       # įrašom X/O į lentą

        moves = list(state.moves)         # kopija
        moves.remove(move)                # pašalinam panaudotą ėjimą

        # Persijungia žaidėjas
        next_player = "O" if state.to_move == "X" else "X"

        # utility skaičiuojam pagal tai, ar paskutinis ėjimas laimėjo
        util = self.compute_utility(board, move, state.to_move) #[7] apskaiciavimas rezullatu

        return GameState(to_move=next_player, utility=util, board=board, moves=moves)
    #dabartines busenos rezulatatatas
    def utility(self, state: GameState, player: str) -> int:
        """
        Utility visada laikoma iš X perspektyvos:
        +1 jei X laimi, -1 jei O laimi, 0 jei niekas dar nelaimėjo.
        Jei klausiam iš O perspektyvos – ženklą apverčiam.
        """
        return state.utility if player == "X" else -state.utility
    #ar liko galimo veiksmy?
    def terminal_test(self, state: GameState) -> bool:
        """Terminalas jei kažkas laimėjo (utility != 0) arba nebėra ėjimų."""
        return state.utility != 0 or len(state.moves) == 0
    #render
    def display(self, state: GameState) -> None:
        """Atspausdina lentą 3x3 (ar h x v)."""
        board = state.board
        for x in range(1, self.h + 1):
            row = []
            for y in range(1, self.v + 1):
                row.append(board.get((x, y), "."))
            print(" ".join(row))
        print("to_move:", state.to_move, "| utility(X):", state.utility)
        print()
    #nustatyti final score
    def compute_utility(self, board: Board, move: Move, player: str) -> int:
        """
        Jei po šito move žaidėjas sudaro k iš eilės – grąžina:
        +1 jei laimėjo X
        -1 jei laimėjo O
         0 jei nelaimėjo niekas
        """
        if (
            self.k_in_row(board, move, player, (0, 1)) or   # vertikaliai
            self.k_in_row(board, move, player, (1, 0)) or   # horizontaliai
            self.k_in_row(board, move, player, (1, 1)) or   # įstrižai \
            self.k_in_row(board, move, player, (1, -1))     # įstrižai /
        ):
            return 1 if player == "X" else -1
        return 0
    # skaiciuoja kiek is eiles simboliu kad nustatyti pabaiga
    def k_in_row(self, board: Board, move: Move, player: str, delta: Move) -> bool:
        """
        Tikrina ar per move eina linija (delta kryptimi) su >= k vienodų simbolių.

        Duomenų idėja:
        - pradedam nuo move
        - einam delta kryptimi ir skaičiuojam kiek langelių yra player
        - tada einam priešinga kryptimi ir pridedam
        """
        dx, dy = delta
        x0, y0 = move

        count = 1  # pats move

        # Pirmyn
        x, y = x0 + dx, y0 + dy
        while board.get((x, y)) == player:
            count += 1
            x, y = x + dx, y + dy

        # Atgal
        x, y = x0 - dx, y0 - dy
        while board.get((x, y)) == player:
            count += 1
            x, y = x - dx, y - dy

        return count >= self.k


# =========================================================
# Greitas testas (galima ištrinti, jei importuoji iš kito failo)
# =========================================================
if __name__ == "__main__":
    game_object = TicTacToe()

    # Pvz: atsitiktinis vs atsitiktinis
    game_object.play_game(random_player, random_player) #[3] Play-game paleidziamas

    # Pvz: alpha-beta vs random
    # game_object.play_game(alpha_beta_player, random_player)

    # Pvz: minimax vs random
    # game_object.play_game(minmax_player, random_player)

    # Pvz: žmogus vs alpha-beta
    # game_object.play_game(query_player, alpha_beta_player)
