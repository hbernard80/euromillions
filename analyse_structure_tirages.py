"""Analyse les structures types des tirages EuroMillions, boules uniquement.

Le script extrait une signature de structure pour chaque tirage à partir des 5 boules :
- répartition par dizaines ;
- nombre de boules paires/impaires ;
- répartition bas/haut (1-25 / 26-50) ;
- présence et longueur des suites consécutives ;
- tranche de somme des 5 boules ;
- profil des écarts entre boules triées.

Ces signatures peuvent ensuite être croisées avec les statistiques historiques :
fréquence des structures, numéros les plus sortis dans une structure donnée,
et répartition par dizaines dans cette même structure.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable

CSV_PATH = Path("csv/global.csv")
BALL_COLS = [f"boule_{i}" for i in range(1, 6)]
DECADE_ORDER = ("1-9", "10-19", "20-29", "30-39", "40-49", "50")


@dataclass(frozen=True)
class DrawStructure:
    """Signature comparable d'un tirage, indépendante de l'ordre de sortie."""

    decades: tuple[str, ...]
    even_count: int
    low_count: int
    sequence_lengths: tuple[int, ...]
    sum_bucket: str
    gap_profile: tuple[str, ...]

    @property
    def type_label(self) -> str:
        """Structure type principale : assez précise sans être trop rare."""
        seq = "+".join(map(str, self.sequence_lengths)) if self.sequence_lengths else "0"
        return (
            f"D={','.join(self.decades)} | "
            f"P={self.even_count}/5 | "
            f"B={self.low_count}/5 | "
            f"S={seq}"
        )

    @property
    def label(self) -> str:
        """Signature complète, utile pour qualifier finement une combinaison."""
        return (
            f"{self.type_label} | "
            f"Σ={self.sum_bucket} | "
            f"E={','.join(self.gap_profile)}"
        )


def detect_csv_delimiter(path: Path, encoding: str = "utf-8-sig") -> str:
    """Détecte le séparateur pour accepter `global.csv` ou des exports FDJ."""
    sample = path.read_text(encoding=encoding)[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;").delimiter
    except csv.Error:
        first_line = sample.splitlines()[0] if sample else ""
        return ";" if first_line.count(";") > first_line.count(",") else ","


def load_draws(path: Path = CSV_PATH) -> list[list[int]]:
    """Charge les 5 boules de chaque tirage, sans les étoiles."""
    delimiter = detect_csv_delimiter(path)
    draws: list[list[int]] = []

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        missing = [col for col in BALL_COLS if col not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"Colonnes manquantes: {missing}. "
                f"Colonnes détectées: {reader.fieldnames or []}."
            )
        for row in reader:
            draws.append(sorted(int(row[col]) for col in BALL_COLS))

    return draws


def decade_bucket(number: int) -> str:
    """Retourne la dizaine EuroMillions d'un numéro de 1 à 50."""
    if not 1 <= number <= 50:
        raise ValueError(f"Numéro hors plage EuroMillions: {number}")
    if number < 10:
        return "1-9"
    if number == 50:
        return "50"
    low = 10 * (number // 10)
    return f"{low}-{low + 9}"


def consecutive_lengths(numbers: Iterable[int]) -> tuple[int, ...]:
    """Retourne les longueurs des suites consécutives, en ignorant les singletons."""
    ordered = sorted(numbers)
    if not ordered:
        return ()

    lengths: list[int] = []
    current_length = 1
    for previous, current in zip(ordered, ordered[1:]):
        if current == previous + 1:
            current_length += 1
        else:
            if current_length > 1:
                lengths.append(current_length)
            current_length = 1
    if current_length > 1:
        lengths.append(current_length)
    return tuple(sorted(lengths, reverse=True))


def sum_bucket(numbers: Iterable[int], step: int = 25) -> str:
    """Classe la somme des boules par tranche lisible."""
    total = sum(numbers)
    low = (total // step) * step
    high = low + step - 1
    return f"{low}-{high}"


def gap_profile(numbers: Iterable[int]) -> tuple[str, ...]:
    """Transforme les écarts entre boules triées en classes compactes."""
    ordered = sorted(numbers)
    profile = []
    for gap in (b - a for a, b in zip(ordered, ordered[1:])):
        if gap <= 2:
            profile.append("serré")
        elif gap <= 6:
            profile.append("moyen")
        else:
            profile.append("large")
    return tuple(profile)


def build_structure(numbers: Iterable[int]) -> DrawStructure:
    """Construit la structure type d'une combinaison de 5 boules."""
    sorted_numbers = sorted(numbers)
    if len(sorted_numbers) != 5 or len(set(sorted_numbers)) != 5:
        raise ValueError("Une combinaison doit contenir exactement 5 numéros distincts.")

    decade_counts = Counter(decade_bucket(number) for number in sorted_numbers)
    decades = tuple(f"{decade}:{decade_counts[decade]}" for decade in DECADE_ORDER if decade_counts[decade])

    return DrawStructure(
        decades=decades,
        even_count=sum(number % 2 == 0 for number in sorted_numbers),
        low_count=sum(number <= 25 for number in sorted_numbers),
        sequence_lengths=consecutive_lengths(sorted_numbers),
        sum_bucket=sum_bucket(sorted_numbers),
        gap_profile=gap_profile(sorted_numbers),
    )


def parse_combo(raw_combo: str) -> list[int]:
    """Accepte `1-2-3-4-5`, `1,2,3,4,5` ou des espaces."""
    normalized = raw_combo.replace("-", ",").replace(";", ",").replace(" ", ",")
    numbers = [int(part) for part in normalized.split(",") if part.strip()]
    return sorted(numbers)


def analyze_structures(draws: list[list[int]]) -> dict[str, object]:
    """Agrège les structures et les statistiques applicables à chaque structure."""
    structure_counts: Counter[str] = Counter()
    structure_examples: dict[str, list[int]] = {}
    balls_by_structure: dict[str, Counter[int]] = defaultdict(Counter)
    decades_by_structure: dict[str, Counter[str]] = defaultdict(Counter)

    for numbers in draws:
        structure = build_structure(numbers)
        label = structure.type_label
        structure_counts[label] += 1
        structure_examples.setdefault(label, numbers)
        balls_by_structure[label].update(numbers)
        decades_by_structure[label].update(decade_bucket(number) for number in numbers)

    return {
        "structure_counts": structure_counts,
        "structure_examples": structure_examples,
        "balls_by_structure": balls_by_structure,
        "decades_by_structure": decades_by_structure,
    }


def global_stats(draws: list[list[int]]) -> dict[str, object]:
    """Calcule les statistiques de référence, toutes structures confondues."""
    all_balls = [number for draw in draws for number in draw]
    sums = [sum(draw) for draw in draws]
    return {
        "total_draws": len(draws),
        "ball_counts": Counter(all_balls),
        "decade_counts": Counter(decade_bucket(number) for number in all_balls),
        "average_sum": mean(sums) if sums else 0,
    }


def print_top_structures(draws: list[list[int]], limit: int = 10) -> None:
    """Affiche les structures les plus fréquentes et les stats associées."""
    stats = analyze_structures(draws)
    total_draws = len(draws)
    print("=== Structures types des tirages - boules uniquement ===")
    print(f"Tirages analysés : {total_draws}")
    print()

    for rank, (label, count) in enumerate(stats["structure_counts"].most_common(limit), start=1):
        pct = count / total_draws * 100 if total_draws else 0
        example = "-".join(map(str, stats["structure_examples"][label]))
        top_balls = stats["balls_by_structure"][label].most_common(8)
        top_decades = stats["decades_by_structure"][label].most_common()
        print(f"{rank}. {label}")
        print(f"   Occurrences : {count} ({pct:.2f} %) | exemple : {example}")
        print(f"   Numéros dominants dans cette structure : {top_balls}")
        print(f"   Dizaines dominantes dans cette structure : {top_decades}")
        print()


def print_combo_context(draws: list[list[int]], combo: str) -> None:
    """Compare une combinaison donnée aux structures historiques."""
    numbers = parse_combo(combo)
    structure = build_structure(numbers)
    stats = analyze_structures(draws)
    reference = global_stats(draws)
    count = stats["structure_counts"].get(structure.type_label, 0)
    total_draws = reference["total_draws"]
    pct = count / total_draws * 100 if total_draws else 0

    print("=== Lecture structurelle de la combinaison ===")
    print(f"Combinaison : {'-'.join(map(str, numbers))}")
    print(f"Structure type : {structure.type_label}")
    print(f"Signature complète : {structure.label}")
    print(f"Présence historique de cette structure : {count}/{total_draws} ({pct:.2f} %)")
    print(f"Somme de la combinaison : {sum(numbers)} | moyenne historique : {reference['average_sum']:.1f}")

    if count:
        print("Numéros les plus sortis dans cette même structure :")
        print(stats["balls_by_structure"][structure.type_label].most_common(10))
        print("Dizaines les plus présentes dans cette même structure :")
        print(stats["decades_by_structure"][structure.type_label].most_common())
    else:
        print("Aucun tirage historique ne correspond exactement à cette structure complète.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyse les structures types des tirages EuroMillions, boules uniquement."
    )
    parser.add_argument("--csv", type=Path, default=CSV_PATH, help="Chemin du CSV historique.")
    parser.add_argument("--top", type=int, default=10, help="Nombre de structures à afficher.")
    parser.add_argument(
        "--combo",
        help="Combinaison à comparer, par exemple '1-13-34-36-47'.",
    )
    args = parser.parse_args()

    draws = load_draws(args.csv)
    print_top_structures(draws, args.top)
    if args.combo:
        print_combo_context(draws, args.combo)


if __name__ == "__main__":
    main()
