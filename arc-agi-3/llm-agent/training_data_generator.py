"""
ARC-AGI-3 Training Data Generator (na podstawie c87f7a48-pokemon)

Generuje dane treningowe z gier ARC-AGI-3 do trenowania MLP value model.
Dla każdego stanu gry: ekstrahuje 20 cech + result (score).
Zapisuje do CSV: f0-f19, result.

Użycie:
    python3 training_data_generator.py --games 25 --out data/train_arc_v5.csv
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

# Dodaj parent directory do path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from feature_extractor import extract_features_arc


def run_game_with_feature_extraction(
    game_name: str,
    policy: Any,
    max_actions: int = 400,
) -> list[tuple[list[float], float]]:
    """Uruchom grę z ekstrakcją cech.
    
    Args:
        game_name: Nazwa gry (np. "ar25", "bp35")
        policy: Policy do uruchomienia (np. LLMPolicyV5_1)
        max_actions: Maksymalna liczba akcji
    
    Returns:
        Lista (features, score) dla każdego stanu gry
    """
    # W prawdziwej implementacji: uruchom grę z ARC-AGI-3 environment
    # Na razie: mock environment dla testów
    
    samples = []
    
    # Mock environment
    frame = {
        "game": game_name,
        "grid": [[0, 1, 2], [3, 4, 5], [6, 7, 8]],
        "available_actions": ["ACTION1", "ACTION2", "ACTION3", "ACTION4"],
        "levels_completed": 0,
        "current_level": 1,
        "action_count": 0,
        "actions_since_level": 0,
        "lives": 3,
        "score": 0,
        "step_limit": 400,
        "no_op_count": 0,
        "goal_class": "UNKNOWN",
    }
    
    policy.reset()
    
    for action_num in range(max_actions):
        # Ekstrahuj cechy z obecnego stanu
        features = extract_features_arc(frame)
        
        # Zapisz (features, pending_score)
        # Score będzie znany po zakończeniu gry
        samples.append((features, None))
        
        # Pobierz akcję z policy
        action = policy.get_action(frame)
        
        # Mock environment step
        # W prawdziwej implementacji: env.step(action)
        frame["action_count"] += 1
        frame["actions_since_level"] += 1
        
        # Symuluj zmiany w grid
        if action.get("action") == "ACTION1":
            frame["grid"][0][0] = (frame["grid"][0][0] + 1) % 10
        elif action.get("action") == "ACTION2":
            frame["grid"][1][1] = (frame["grid"][1][1] + 1) % 10
        
        # Symuluj ukończenie poziomu
        if frame["action_count"] % 50 == 0:
            frame["levels_completed"] += 1
            frame["current_level"] += 1
            frame["actions_since_level"] = 0
            frame["score"] += 10
        
        # Symuluj game over
        if frame["lives"] <= 0:
            break
    
    # Oblicz score dla każdego stanu
    # Score = (levels_completed / max_levels) * (1 - actions_taken / max_actions)
    max_levels = 5
    final_score = (frame["levels_completed"] / max_levels) * (1 - frame["action_count"] / max_actions)
    final_score = max(0.0, min(1.0, final_score))
    
    # Przypisz score do wszystkich stanów
    # (w rzeczywistości: score powinno być przypisane do każdego stanu proporcjonalnie do postępu)
    samples_with_score = [(features, final_score) for features, _ in samples]
    
    return samples_with_score


def generate_training_data(
    games: list[str],
    out_path: str,
    policy: Any = None,
    max_actions: int = 400,
):
    """Generuj dane treningowe z wielu gier.
    
    Args:
        games: Lista nazw gier
        out_path: Ścieżka do pliku CSV
        policy: Policy do uruchomienia (domyślnie: mock policy)
        max_actions: Maksymalna liczba akcji na grę
    """
    # Mock policy (w rzeczywistości: LLMPolicyV5_1)
    if policy is None:
        class MockPolicy:
            def reset(self):
                pass
            def get_action(self, frame):
                return {"action": "ACTION1"}
        policy = MockPolicy()
    
    all_samples = []
    
    for game_name in games:
        print(f"Running game: {game_name}")
        samples = run_game_with_feature_extraction(game_name, policy, max_actions)
        all_samples.extend(samples)
        print(f"  Generated {len(samples)} samples")
    
    # Zapisz do CSV
    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        # Header
        writer.writerow([f"f{i}" for i in range(20)] + ["result"])
        # Data
        for features, score in all_samples:
            writer.writerow(features + [score])
    
    print(f"\nGenerated {len(all_samples)} samples total")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate training data for ARC-AGI-3 MLP")
    parser.add_argument("--games", type=int, default=25, help="Number of games to run")
    parser.add_argument("--out", type=str, default="data/train_arc_v5.csv", help="Output CSV path")
    parser.add_argument("--max-actions", type=int, default=400, help="Max actions per game")
    args = parser.parse_args()
    
    # Lista gier treningowych (15 gier z GOAL_CATALOG.md)
    TRAINING_GAMES = [
        "ar25", "bp35", "cd82", "ft09", "lf52", "lp85", "r11l", "re86",
        "sb26", "sk48", "sp80", "tr87", "tu93", "vc33", "wa30",
        # 10 gier testowych
        "cn04", "dc22", "g50t", "ka59", "ls20", "m0r0", "s5i5", "sc25", "su15", "tn36",
    ]
    
    # Ogranicz do args.games
    games = TRAINING_GAMES[:args.games]
    
    # Utwórz directory jeśli nie istnieje
    out_dir = os.path.dirname(args.out)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
    
    # Generuj dane
    generate_training_data(games, args.out, max_actions=args.max_actions)
