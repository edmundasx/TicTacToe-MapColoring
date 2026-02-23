# Artificial-Intelligence-Course
1. Pagrindinėje funkcijoje solve_map_coloring iškviečiama csp.backtracking_search,
kuriai kaip parametras perduodamas CSP objektas (pvz., MapColoringCSP/CSP instancija),
aprašantis regionus (kintamuosius), jų domenus (spalvas), kaimynystės apribojimus ir apribojimų funkciją.

2. csp.backtracking_search pradeda rekursyviai konstruoti assignment (žemėlapį) regionas -> spalva.
Kiekviename žingsnyje parenkamas dar nepriskirtas kintamasis var (regionas) iš CSP objekto,
dažniausiai naudojant select_unassigned_variable su MRV.
Tada order_domain_values grąžina galimų value (spalvų) sąrašą tam regionui, surikiuotą pagal LCV heuristiką (mažiausiai apribojanti reikšmė).

3. Kiekvienai galimai spalvai atliekamas patikrinimas csp.nconflicts(var, value, assignment): jei konfliktų skaičius yra 0,
priskyrimas var:value->assignment ir tęsiama paieška; jei > 0, ši spalva atmetama.

4. Atlikus priskyrima išsaugomas šis žingsnis atstatymui per šią funkciją:  removals = csp.suppose(var, value)

5. Tada įvyksta „forward_checking“ patikrinimas, kurio metu peržiūrimi kintamojo kaimynai ir, atnaujinant „curr_domains“, pašalinamos negalimos spalvos.
Jei kuriam nors kaimynui nebelieka galimų spalvų, grįžtama atgal naudojant „restore“ ir „unassign“ funkcijas bei bandoma nauja spalva.

6. Jei iference gražina atsakymą - true, tada pradedama rekursija ir steko formavimas:  result = backtrack(assignment),
perduoda esamą dalinį priskyrimą į gilesnį rekursijos lygį; funkcija grįžta tik tada, kai randa pilną sprendinį (grąžina assignment) arba kai šaka žlunga (grąžina None).

7. Kaip įprasta rekursiniam backtracking’ui, galinės būsenos (sprendinio) tikrinimas vyksta pačioje backtrack pradžioje: len(assignment) == len(csp.variables) patikrina, ar visi regionai jau turi priskirtą spalvą.
Jei taip, funkcija grąžina pilną assignment (dict tipo priskyrimą regionas -> spalva).

8. Reikia pabrėžti, kad paskutiniame lygyje kai pasiekiama goal state funkcija gražindama rezultatą aktyvuoja:

     if result is not None:
                    return result

Taip uždarydama stekus.

backtracking_search (5):
backtracking_search entry,
goal test len(assignment)==len(csp.variables),
var=select_unassigned_variable(...),
csp.nconflicts(var,value,assignment)==0,
result=backtrack(assignment) / if result is not None: return result



1. Sukuriamas game objektas -> Jame nurodomos žaidimo taisyklės ir ypatybės -> Paleidžia play_game funkcija pradedanti matcha
2. play_game sukuria pradinę būseną su tuščia lenta, paleidžiamas while ciklas iš kiekvieno žaidėjo minimax funkcijos gražinantis ėjimą:
move = player_fn(self, state)

O ėjimas įrašomas kaip naują būsena:
state = self.result(state, move)

Šis ciklas vyksta iki terminal_test gražins true, kad žaidimas pasiekė pabaigą.

3.  Žaidėjo funkcija minimax:
    1) Nustato esamos būsenos žaidėjo eilę
    2) Nustato legal moves
    3) Filtravimas -> Lambda funkcija kiekvienam legaliam veiksmui iš esamos būsenos paleidžia min_value funkcija, simuliuodama priešininko optimaliausią ėjimą.
    4) Čia prasideda rekursija min_value funkcijoje:
        1) Tikrina ar tenkinama žaidimo pabaigos sąlyga. Jei taip gražina įvertinimą.
        2) Jei ne paleidžiamas ciklas esamos būsenos legaliems ėjimams, čia formuojamas STEKAS LIFO
        3) Įvertinant priešininko (min) optimaliausią ėjimą iškviečiama max_value funkcija ir taip papildomas STEKAS.(max value funkcijai perduodama simuliuojama busena per game.result pritaikius veiksmus)
        4) Max_value vertina dabartinio žaidėjo optimaliausią ėjimą (max), atlieka tas pačias galinės būsenos patikrinimo funkcijas.
        5) Dar kartą iškviečiama min_value funkciją ir einama gilyn kol vis kintant busenai pacioje pradzioje tenkinama game.terminal_test(busena) salyga.
        6) Cia prasideda steko atlaisvinimas, perduodamos reiksmes i zemesnius kintamuju lygius.
    5) Grįžtama į lambda funkcija ir čia darbas tesiamas kitam veiksmui, jei šiame etape gaunasi taip, kad yra kelios lygios reikšmės, python pagal nutylėjimą renkasi pati pirmiausią.

Rekursijos steke min_value naudoja alpha kaip „reikšmingumo slenkstį“.
Jei ji randa ėjimą, kuris Max situaciją padaro blogesnę nei jau turimas geriausias Max pasirinkimas, ji nustoja skaičiuoti, nes ta šaka tampa nebereikšminga galutiniam sprendimui.


minimax_decision entry,
return max(moves, key=...),
max_value entry,
terminal_test/utility return,
s2=game.result(state,a)
