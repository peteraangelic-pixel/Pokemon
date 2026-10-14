"""
ARC-AGI-3 Ewolucja Parametrów Heurystyki (CEM/ES)

Inspiracja: c87f7a48-pokemon (Pokemon TCG) - ewolucja 26 parametrów heurystyki
100 mutantów, mutacja rate 0.5, factor 0.2, best comb 0.879

Cel: ewoluować parametry heurystyki ARC-AGI-3 (nie ML na stanach)
- EXPLORE_WEIGHT, EXPLOIT_WEIGHT, NOOP_PENALTY
- LEVEL_PROGRESS_WEIGHT, GAME_OVER_PENALTY
- AFFORDANCE_WEIGHT, PATTERN_WEIGHT
- STUCK_THRESHOLD, AUDIT_ESCALATION_STEP
- TEMP_BASE, TEMP_STUCK, TEMP_CONFIDENT
- BATCH_SIZE_BASE, BATCH_SIZE_CONFIDENT, BATCH_SIZE_UNCERTAIN

Expected gain: +0.5-1.5 pkt (jak w c87f7a48: +0.9pp)

Usage:
    python3 evolve_parameters.py --population 100 --generations 10 --elite-ratio 0.2
"""

import json
import os
import sys
import random
import math
from dataclasses import dataclass, field
from typing import Any, Callable
from pathlib import Path


# ---------------------------------------------------------------------------
# Parametry heurystyki ARC-AGI-3 (do ewolucji)
# ---------------------------------------------------------------------------

@dataclass
class HeuristicParams:
    """Parametry heurystyki ARC-AGI-3."""
    
    # Wagi akcji
    explore_weight: float = 1.0          # Waga eksploracji (nowe akcje)
    exploit_weight: float = 2.0          # Waga eksploatacji (akcje które zmieniły grid)
    noop_penalty: float = -1.0           # Kara za no-op (akcja nie zmieniła grid)
    level_progress_weight: float = 5.0   # Waga postępu poziomu
    game_over_penalty: float = -10.0     # Kara za game-over
    affordance_weight: float = 1.5       # Waga klikalnych obiektów
    pattern_weight: float = 2.0          # Waga wzorców (COPY)
    
    # Progi
    stuck_threshold: int = 40            # Po ilu akcjach audyt
    audit_escalation_step: int = 15      # Co ile akcji eskalacja
    
    # Temperatura LLM
    temp_base: float = 0.6               # Bazowa temperatura
    temp_stuck: float = 0.9              # Temperatura gdy stuck
    temp_confident: float = 0.3          # Temperatura gdy confident
    
    # Batch size
    batch_size_base: int = 4             # Bazowy batch
    batch_size_confident: int = 8        # Batch gdy confident
    batch_size_uncertain: int = 2        # Batch gdy niepewny
    
    def to_dict(self) -> dict:
        """Konwersja do dict (do serializacji)."""
        return {
            "explore_weight": self.explore_weight,
            "exploit_weight": self.exploit_weight,
            "noop_penalty": self.noop_penalty,
            "level_progress_weight": self.level_progress_weight,
            "game_over_penalty": self.game_over_penalty,
            "affordance_weight": self.affordance_weight,
            "pattern_weight": self.pattern_weight,
            "stuck_threshold": self.stuck_threshold,
            "audit_escalation_step": self.audit_escalation_step,
            "temp_base": self.temp_base,
            "temp_stuck": self.temp_stuck,
            "temp_confident": self.temp_confident,
            "batch_size_base": self.batch_size_base,
            "batch_size_confident": self.batch_size_confident,
            "batch_size_uncertain": self.batch_size_uncertain,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "HeuristicParams":
        """Konwersja z dict."""
        return cls(**d)


# ---------------------------------------------------------------------------
# CEM Evolution
# ---------------------------------------------------------------------------

def initialize_population(population_size: int) -> list[HeuristicParams]:
    """Inicjalizacja populacji z random perturbacjami bazowych parametrów."""
    base = HeuristicParams()
    population = []
    
    for _ in range(population_size):
        # Random perturbacja ±30%
        params = HeuristicParams(
            explore_weight=base.explore_weight * (1 + random.uniform(-0.3, 0.3)),
            exploit_weight=base.exploit_weight * (1 + random.uniform(-0.3, 0.3)),
            noop_penalty=base.noop_penalty * (1 + random.uniform(-0.3, 0.3)),
            level_progress_weight=base.level_progress_weight * (1 + random.uniform(-0.3, 0.3)),
            game_over_penalty=base.game_over_penalty * (1 + random.uniform(-0.3, 0.3)),
            affordance_weight=base.affordance_weight * (1 + random.uniform(-0.3, 0.3)),
            pattern_weight=base.pattern_weight * (1 + random.uniform(-0.3, 0.3)),
            stuck_threshold=int(base.stuck_threshold * (1 + random.uniform(-0.3, 0.3))),
            audit_escalation_step=int(base.audit_escalation_step * (1 + random.uniform(-0.3, 0.3))),
            temp_base=max(0.1, min(1.0, base.temp_base + random.uniform(-0.2, 0.2))),
            temp_stuck=max(0.1, min(1.5, base.temp_stuck + random.uniform(-0.2, 0.2))),
            temp_confident=max(0.1, min(0.8, base.temp_confident + random.uniform(-0.1, 0.1))),
            batch_size_base=max(1, int(base.batch_size_base + random.randint(-2, 2))),
            batch_size_confident=max(1, int(base.batch_size_confident + random.randint(-2, 2))),
            batch_size_uncertain=max(1, int(base.batch_size_uncertain + random.randint(-1, 1))),
        )
        population.append(params)
    
    return population


def mutate(params: HeuristicParams, mutation_rate: float = 0.5, factor: float = 0.2) -> HeuristicParams:
    """Mutacja parametrów z CEM."""
    def maybe_mutate(value: float, is_int: bool = False):
        if random.random() < mutation_rate:
            if is_int:
                return max(1, int(value * (1 + random.uniform(-factor, factor))))
            else:
                return value * (1 + random.uniform(-factor, factor))
        return value
    
    mutated = HeuristicParams(
        explore_weight=maybe_mutate(params.explore_weight),
        exploit_weight=maybe_mutate(params.exploit_weight),
        noop_penalty=maybe_mutate(params.noop_penalty),
        level_progress_weight=maybe_mutate(params.level_progress_weight),
        game_over_penalty=maybe_mutate(params.game_over_penalty),
        affordance_weight=maybe_mutate(params.affordance_weight),
        pattern_weight=maybe_mutate(params.pattern_weight),
        stuck_threshold=maybe_mutate(params.stuck_threshold, is_int=True),
        audit_escalation_step=maybe_mutate(params.audit_escalation_step, is_int=True),
        temp_base=max(0.1, min(1.0, maybe_mutate(params.temp_base))),
        temp_stuck=max(0.1, min(1.5, maybe_mutate(params.temp_stuck))),
        temp_confident=max(0.1, min(0.8, maybe_mutate(params.temp_confident))),
        batch_size_base=max(1, maybe_mutate(params.batch_size_base, is_int=True)),
        batch_size_confident=max(1, maybe_mutate(params.batch_size_confident, is_int=True)),
        batch_size_uncertain=max(1, maybe_mutate(params.batch_size_uncertain, is_int=True)),
    )
    
    return mutated


def evaluate(params: HeuristicParams, games: list[str], evaluator: Callable) -> float:
    """Evaluacja parametrów na grach.
    
    Args:
        params: Parametry heurystyki
        games: Lista gier do evaluacji
        evaluator: Funkcja która uruchamia grę z parametrami i zwraca score
    
    Returns:
        Średni score na grach (0-1)
    """
    scores = []
    for game in games:
        score = evaluator(params, game)
        scores.append(score)
    return sum(scores) / len(scores) if scores else 0.0


def select_elite(population: list[HeuristicParams], fitness: list[float], elite_ratio: float = 0.2) -> list[HeuristicParams]:
    """Selekcja elity (top elite_ratio)."""
    paired = list(zip(population, fitness))
    paired.sort(key=lambda x: x[1], reverse=True)
    elite_size = max(1, int(len(population) * elite_ratio))
    return [p for p, _ in paired[:elite_size]]


def sample_from_elite(elite: list[HeuristicParams], population_size: int) -> list[HeuristicParams]:
    """Sampling nowych mutantów z elity."""
    new_population = []
    for _ in range(population_size):
        # Wybierz losowego osobnika z elity
        parent = random.choice(elite)
        # Mutuj
        child = mutate(parent)
        new_population.append(child)
    return new_population


def evolve_parameters(
    games: list[str],
    evaluator: Callable,
    population_size: int = 100,
    generations: int = 10,
    elite_ratio: float = 0.2,
    mutation_rate: float = 0.5,
    factor: float = 0.2,
) -> tuple[HeuristicParams, list[float]]:
    """Ewolucja parametrów heurystyki z CEM.
    
    Args:
        games: Lista gier do evaluacji
        evaluator: Funkcja która uruchamia grę z parametrami i zwraca score
        population_size: Rozmiar populacji (domyślnie 100)
        generations: Liczba generacji (domyślnie 10)
        elite_ratio: Ratio elity (domyślnie 0.2 = 20%)
        mutation_rate: Mutation rate (domyślnie 0.5)
        factor: Mutation factor (domyślnie 0.2)
    
    Returns:
        (best_params, fitness_history)
    """
    print(f"Evolving parameters: pop={population_size}, gen={generations}, elite={elite_ratio}")
    print(f"Mutation: rate={mutation_rate}, factor={factor}")
    print(f"Games: {len(games)}")
    
    # Inicjalizacja
    population = initialize_population(population_size)
    fitness_history = []
    
    for gen in range(generations):
        # Evaluacja każdego mutanta
        print(f"\nGeneration {gen+1}/{generations}")
        fitness = []
        for i, params in enumerate(population):
            score = evaluate(params, games, evaluator)
            fitness.append(score)
            if (i + 1) % 10 == 0:
                print(f"  Evaluated {i+1}/{population_size} mutants")
        
        # Statystyki
        best_idx = fitness.index(max(fitness))
        best_score = fitness[best_idx]
        avg_score = sum(fitness) / len(fitness)
        fitness_history.append(best_score)
        
        print(f"  Best: {best_score:.3f}, Avg: {avg_score:.3f}")
        
        # Selekcja elity
        elite = select_elite(population, fitness, elite_ratio)
        print(f"  Elite size: {len(elite)}")
        
        # Sampling nowych mutantów
        population = sample_from_elite(elite, population_size)
    
    # Zwróć best
    final_fitness = [evaluate(p, games, evaluator) for p in population]
    best_idx = final_fitness.index(max(final_fitness))
    best_params = population[best_idx]
    
    return best_params, fitness_history


# ---------------------------------------------------------------------------
# Evaluator (placeholder - w rzeczywistości: uruchamia grę z parametrami)
# ---------------------------------------------------------------------------

def mock_evaluator(params: HeuristicParams, game: str) -> float:
    """Mock evaluator (placeholder).
    
    W rzeczywistości: uruchamia grę z parametrami i zwraca score.
    Na razie: random score z tendencją do parametrów.
    """
    # Prosty scoring: im wyższe wagi, tym wyższy score (z szumem)
    score = (
        params.exploit_weight * 0.1 +
        params.level_progress_weight * 0.05 +
        params.affordance_weight * 0.08 +
        params.pattern_weight * 0.07 -
        abs(params.noop_penalty) * 0.03 -
        abs(params.game_over_penalty) * 0.02 +
        random.uniform(-0.1, 0.1)  # Szum
    )
    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Evolve heuristic parameters for ARC-AGI-3")
    parser.add_argument("--population", type=int, default=100, help="Population size")
    parser.add_argument("--generations", type=int, default=10, help="Number of generations")
    parser.add_argument("--elite-ratio", type=float, default=0.2, help="Elite ratio")
    parser.add_argument("--mutation-rate", type=float, default=0.5, help="Mutation rate")
    parser.add_argument("--factor", type=float, default=0.2, help="Mutation factor")
    parser.add_argument("--out", type=str, default="evolved_params.json", help="Output JSON path")
    args = parser.parse_args()
    
    # Gry do evaluacji
    GAMES = [
        "ar25", "bp35", "cd82", "ft09", "lf52", "lp85", "r11l", "re86",
        "sb26", "sk48", "sp80", "tr87", "tu93", "vc33", "wa30",
        "cn04", "dc22", "g50t", "ka59", "ls20", "m0r0", "s5i5", "sc25", "su15", "tn36",
    ]
    
    # Ewolucja
    best_params, fitness_history = evolve_parameters(
        games=GAMES,
        evaluator=mock_evaluator,
        population_size=args.population,
        generations=args.generations,
        elite_ratio=args.elite_ratio,
        mutation_rate=args.mutation_rate,
        factor=args.factor,
    )
    
    # Zapisz best params
    result = {
        "best_params": best_params.to_dict(),
        "fitness_history": fitness_history,
        "config": {
            "population_size": args.population,
            "generations": args.generations,
            "elite_ratio": args.elite_ratio,
            "mutation_rate": args.mutation_rate,
            "factor": args.factor,
        },
    }
    
    with open(args.out, "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"\nBest params saved to {args.out}")
    print(f"Fitness history: {fitness_history}")


if __name__ == "__main__":
    main()
