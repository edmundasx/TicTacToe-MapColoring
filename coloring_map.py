"""
Data source (GADM administrative boundaries):
https://gadm.org/download_country_v3.html#google_vignette
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import csv

import geopandas as gpd
import matplotlib.pyplot as plt

import csp  # minimal CSP: MapColoringCSP + backtracking_search (+ mrv/lcv/forward_checking)


# =========================
# [01] Settings (keep simple)
# =========================

REGION_FIELD = "NAME_1"  # "NAME_2" jei nori smulkesnių vienetų

SHP_LEVEL_1 = Path("./data/gadm36_LTU_shp/gadm36_LTU_1.shp")
SHP_LEVEL_2 = Path("./data/gadm36_LTU_shp/gadm36_LTU_2.shp")

DOMAIN_LETTERS = "RGBY"  # pabandyk "RGB", jei nori 3 spalvų

TRACE_JSON = Path("trace.json")
TRACE_CSV = Path("trace.csv")

FIG_SIZE = (10, 10)
TITLE = "Lietuvos regionų žemėlapis (CSP nuspalvinimas)"


# =========================
# [02] Load + build regions
# =========================

def load_country_gdf(region_field: str) -> gpd.GeoDataFrame:
    # [02.1] Pasirink shapefile pagal admin lygį
    shp_path = SHP_LEVEL_1 if region_field == "NAME_1" else SHP_LEVEL_2

    # [02.2] Patikrink, ar failas egzistuoja
    if not shp_path.is_file():
        raise FileNotFoundError(f"Shapefile nerastas: {shp_path.resolve()}")

    # [02.3] Įkelk GeoDataFrame
    return gpd.read_file(str(shp_path))


def build_region_geometries(country_gdf: gpd.GeoDataFrame, group_field: str) -> gpd.GeoDataFrame:
    """
    Grąžina GeoDataFrame, kur kiekviena eilutė = 1 regionas, su sujungta geometrija.
    """
    # [03.1] Group by region name (NAME_1 arba NAME_2)
    grouped = country_gdf.groupby(group_field)

    # [03.2] Sumuok geometrijas į vieną (MultiPolygon/Polygon)
    regions_df = grouped.geometry.apply(lambda s: s.unary_union).reset_index()

    # [03.3] Paversk į GeoDataFrame
    regions_gdf = gpd.GeoDataFrame(regions_df, geometry="geometry", crs=country_gdf.crs)

    # [03.4] Normalizuok pavadinimus
    regions_gdf[group_field] = regions_gdf[group_field].astype(str).str.strip()

    return regions_gdf


# =========================
# [04] Adjacency (touches)
# =========================

def _candidate_indices(regions_gdf: gpd.GeoDataFrame, geom) -> List[int]:
    """
    Kandidatai pagal spatial index (jei yra). Jei ne — grąžina visus indeksus.
    """
    sindex = getattr(regions_gdf, "sindex", None)
    if sindex is None:
        return list(range(len(regions_gdf)))

    # Modernus API (GeoPandas/Shapely)
    if hasattr(sindex, "query"):
        try:
            return list(sindex.query(geom, predicate="intersects"))
        except TypeError:
            # senesnės versijos nepalaiko predicate
            return list(sindex.query(geom))
        except Exception:
            pass

    # Fallback: intersection pagal bounds
    try:
        return list(sindex.intersection(geom.bounds))
    except Exception:
        return list(range(len(regions_gdf)))


def build_adjacency(regions_gdf: gpd.GeoDataFrame, name_col: str) -> Dict[str, List[str]]:
    """
    neighbor_dict: region_name -> [adjacent_region_names]
    Naudojam touches (ribos liečiasi).
    """
    # [04.1] Vardas -> geometrija
    geom_by_name = {row[name_col]: row.geometry for _, row in regions_gdf.iterrows()}
    names = list(geom_by_name.keys())

    neighbors: Dict[str, List[str]] = {}

    # [04.2] Kaimynų paieška
    for a in names:
        a_geom = geom_by_name[a]
        neigh_list: List[str] = []

        # [04.3] Kandidatai pagal spatial index (greitina)
        idxs = _candidate_indices(regions_gdf, a_geom)
        candidate_names = regions_gdf.iloc[idxs][name_col].tolist()

        # [04.4] Tikslus touches tikrinimas
        for b in candidate_names:
            if a == b:
                continue
            if a_geom.touches(geom_by_name[b]):
                neigh_list.append(b)

        # [04.5] Deterministinis rezultatas
        neighbors[a] = sorted(set(neigh_list))

    return neighbors


# =========================
# [05] Solve CSP + trace
# =========================

def solve_map_coloring(
    neighbor_dict: Dict[str, List[str]],
    domain_letters: str,
    max_steps: int = 50_000,
    log_events: Optional[set[str]] = None,
) -> Tuple[Optional[Dict[str, str]], List[Dict[str, Any]]]:
    # [05.1] Sukuriamas CSP objektas iš regionų kaimynystės ir spalvų domeno
    regions_csp = csp.MapColoringCSP(list(domain_letters), neighbor_dict)

    # [05.2] Trace (step-by-step įrašai vizualizacijai)
    trace: List[Dict[str, Any]] = []

    # [#1] Backtracking (DFS) su heuristikomis
    solution = csp.backtracking_search(
        regions_csp,
        select_unassigned_variable=csp.mrv,          # MINIMUM REMAINING VALUE (mažiausiai likusių spalvų)
        order_domain_values=csp.lcv,                 # LEAST CONSTRAINING VALUE (mažiausiai "užspaudžia" kaimynus)
        inference=csp.forward_checking,              # Paprastas inference (be AC3/mac)
        trace=trace,
        max_steps=max_steps,
    )

    # Jei tavo csp.py neturi 'log_events', filtruojam čia (paprastas variantas)
    if log_events is not None:
        trace = [t for t in trace if t.get("event") in log_events]

    return solution, trace


def save_trace(trace: List[Dict[str, Any]], json_path: Path, csv_path: Path) -> None:
    # [05.4] JSON
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)

    # [05.5] CSV
    fieldnames = list(trace[0].keys()) if trace else ["step", "depth", "event", "var", "val", "assignment"]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in trace:
            w.writerow(row)


# =========================
# [06] Plotting
# =========================

def build_plot_colors(
    region_names: List[str],
    solution: Optional[Dict[str, str]],
) -> Dict[str, Tuple[float, float, float, float]]:
    """
    region -> RGBA (matplotlib)
    """
    # [06.1] Fallback: unikalios spalvos kiekvienam regionui
    fallback = plt.cm.get_cmap("tab20", max(1, len(region_names)))
    color_dict = {name: fallback(i) for i, name in enumerate(region_names)}

    # [06.2] Jei yra CSP sprendinys – mapink R/G/B/Y į 4 spalvas
    if solution:
        cmap4 = plt.cm.get_cmap("tab20", 4)
        letter_to_rgba = {"R": cmap4(0), "G": cmap4(1), "B": cmap4(2), "Y": cmap4(3)}
        for region, letter in solution.items():
            color_dict[region] = letter_to_rgba.get(letter, color_dict[region])

    return color_dict


def plot_regions(
    regions_gdf: gpd.GeoDataFrame,
    name_col: str,
    color_dict: Dict[str, Tuple[float, float, float, float]],
    title: str,
    fig_size: Tuple[int, int],
) -> None:
    # [06.3] Figure + axis
    fig, ax = plt.subplots(figsize=fig_size)

    # [06.4] Nubraižyk regionus (vienu plot'u)
    colors = [color_dict.get(n) for n in regions_gdf[name_col].tolist()]
    regions_gdf.plot(ax=ax, color=colors, edgecolor="black", linewidth=0.8)

    # [06.5] Etiketės (representative_point saugiau nei centroid)
    for _, row in regions_gdf.iterrows():
        name = row[name_col]
        pt = row.geometry.representative_point()
        ax.text(pt.x, pt.y, name, fontsize=9, ha="center", va="center")

    ax.set_title(title)
    ax.set_axis_off()
    plt.show()


# =========================
# [07] Main
# =========================

def main() -> None:
    # [07.1] Įkelk geoduomenis
    country = load_country_gdf(REGION_FIELD)

    # [07.2] Suformuok regionus (1 geometrija regionui)
    regions = build_region_geometries(country, REGION_FIELD)

    # [07.3] Sudaryk adjacency
    neighbor_dict = build_adjacency(regions, REGION_FIELD)
    print("[Adjacency dict]")
    print(neighbor_dict)

    # [07.4] Spręsk CSP + trace
    solution, trace = solve_map_coloring(
        neighbor_dict,
        DOMAIN_LETTERS,
        max_steps=50_000,
        log_events={"ASSIGN", "BACKTRACK", "GOAL"},  # pradžiai ne triukšminga
    )

    print("\n[CSP solution]")
    print(solution)
    print(f"[Trace events] {len(trace)}")

    # [07.5] Išsaugok trace
    save_trace(trace, TRACE_JSON, TRACE_CSV)
    print(f"[Saved] {TRACE_JSON.resolve()}")
    print(f"[Saved] {TRACE_CSV.resolve()}")

    # [07.6] Nubraižyk
    region_names = regions[REGION_FIELD].tolist()
    color_dict = build_plot_colors(region_names, solution)
    plot_regions(regions, REGION_FIELD, color_dict, TITLE, FIG_SIZE)


if __name__ == "__main__":
    main()
