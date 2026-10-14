"""
ARC-AGI-3 LLM Agent v5.1 - z MLP Value Model

Integracja LLM + MLP:
- LLM daje rozumowanie (FIELD_GUIDE, LEVEL_NOTES, STUCK_AUDIT)
- MLP daje szybką ocenę akcji (value model)
- Jeśli MLP value < 0.3 → agent jest w złym stanie, zmień strategię

Oczekiwany wynik: ~37-47 pkt (vs v5.0 35-42 pkt)
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

# Dodaj parent directory do path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_policy_v5 import (
    LLMPolicyV5,
    GameState,
    build_system_prompt,
    build_level_notes_request,
    extract_level_notes,
    build_stuck_audit_prompt,
    FIELD_GUIDE,
)
from feature_extractor import extract_features_arc
from mlp_value_model import mlp_predict


# ---------------------------------------------------------------------------
# MLP Value Model (placeholder weights - w rzeczywistości zaimportuj z wytrenowanego modelu)
# ---------------------------------------------------------------------------

def load_mlp_weights(weights_path: str = None) -> Optional[tuple]:
    """Load MLP weights from file.
    
    Args:
        weights_path: Ścieżka do pliku z wagami (np. "mlp_arc_weights.py")
    
    Returns:
        (W0, b0, W1, b1, W2, b2) lub None jeśli plik nie istnieje
    """
    if weights_path is None:
        # Domyślna ścieżka
        weights_path = os.path.join(os.path.dirname(__file__), "mlp_arc_weights.py")
    
    if not os.path.exists(weights_path):
        print(f"MLP weights not found at {weights_path}, using random initialization")
        return None
    
    # Importuj wagi
    import importlib.util
    spec = importlib.util.spec_from_file_location("mlp_weights", weights_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Ekstrahuj wagi
    W0 = module._W0_coef
    b0 = module._W0_bias
    W1 = module._W1_coef
    b1 = module._W1_bias
    W2 = module._W2_coef
    b2 = module._W2_bias
    
    return (W0, b0, W1, b1, W2, b2)


# ---------------------------------------------------------------------------
# Policy v5.1 - LLM + MLP
# ---------------------------------------------------------------------------

class LLMPolicyV5_1(LLMPolicyV5):
    """LLM Agent v5.1 z MLP value model.
    
    Ulepszenia vs v5.0:
    - MLP value model (20->128->64->1) daje szybką ocenę stanu
    - Jeśli value < 0.3 → agent jest w złym stanie, zmień strategię
    - Jeśli value > 0.7 → agent jest w dobrym stanie, kontynuuj
    - 0.16ms/decision (vs ~2s LLM call)
    """
    
    def __init__(self, llm_client: Any, mlp_weights: Optional[tuple] = None):
        super().__init__(llm_client)
        self.mlp_weights = mlp_weights
        
    def get_action(self, frame: dict[str, Any]) -> dict[str, Any]:
        """Zwróć akcję dla danego frame'a z MLP value model."""
        self.state.action_count += 1
        self.state.actions_since_level += 1
        
        # Ekstrahuj cechy z stanu gry
        features = extract_features_arc(frame)
        
        # MLP value prediction
        if self.mlp_weights is not None:
            ml_value = mlp_predict(features, self.mlp_weights)
            self.state.ml_value = ml_value
        else:
            ml_value = 0.5  # Neutral
            self.state.ml_value = ml_value
        
        # Sprawdź czy poziom został ukończony
        if frame.get("levels_completed", 0) > self.state.current_level - 1:
            self.state.current_level = frame["levels_completed"] + 1
            self.state.actions_since_level = 0
            self.state.stuck_count = 0
            # Poproś o LEVEL NOTES
            self.messages.append({
                "role": "system",
                "content": build_level_notes_request(frame["levels_completed"])
            })
        
        # Sprawdź czy utknął (40 akcji bez ukończenia poziomu)
        if self.state.actions_since_level >= 40:
            self.state.stuck_count += 1
            if self.state.stuck_count % 15 == 0:  # Co 15 akcji po utknięciu
                self.messages.append({
                    "role": "system",
                    "content": build_stuck_audit_prompt(
                        self.state.current_level,
                        self.state.actions_since_level
                    )
                })
        
        # Sprawdź no-op (akcja nie zmieniła grid)
        current_grid_hash = str(frame.get("grid", ""))
        if current_grid_hash == self.state.last_grid_hash:
            self.state.no_op_count += 1
        else:
            self.state.no_op_count = max(0, self.state.no_op_count - 1)
        self.state.last_grid_hash = current_grid_hash
        
        # Dodaj frame do messages
        user_msg = self._build_user_message(frame, ml_value)
        self.messages.append({"role": "user", "content": user_msg})
        
        # Wywołaj LLM
        response = self.client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "qwen2.5-7b"),
            messages=self.messages,
            temperature=0.6,
            max_tokens=2000,
        )
        
        assistant_msg = response.choices[0].message
        self.messages.append(assistant_msg)
        
        # Wydobądź akcje
        actions = self._parse_actions(assistant_msg.content)
        
        # Zapisz notatki
        if actions and actions[0].get("notes"):
            self.state.notes.append(actions[0]["notes"])
            # Ogranicz do ostatnich 4 notatek
            if len(self.state.notes) > 4:
                self.state.notes = self.state.notes[-4:]
        
        # Zaktualizuj level_notes z odpowiedzi modelu
        new_notes = extract_level_notes(self.messages[-2:])
        if new_notes:
            self.state.level_notes.update(new_notes)
            # Zaktualizuj system prompt z nowymi notatkami
            self.messages[0]["content"] = build_system_prompt(self.state.level_notes)
        
        # Zwróć pierwszą akcję
        return actions[0] if actions else {"action": "RESET", "reasoning": "fallback"}
    
    def _build_user_message(self, frame: dict[str, Any], ml_value: float = 0.5) -> str:
        """Zbuduj wiadomość użytkownika z frame'em i MLP value."""
        grid = frame.get("grid", [])
        available_actions = frame.get("available_actions", [])
        
        # ASCII reprezentacja grid
        grid_str = "\n".join("".join(str(cell) for cell in row) for row in grid)
        
        # Dodaj MLP value warning/info
        ml_warning = ""
        if ml_value < 0.3:
            ml_warning = f"\n\n⚠️ WARNING: ML model predicts low success probability ({ml_value:.2f}). Consider changing strategy."
        elif ml_value > 0.7:
            ml_warning = f"\n\n✓ ML model predicts good state ({ml_value:.2f}). Continue current approach."
        
        # Dodaj no-op warning
        no_op_warning = ""
        if self.state.no_op_count >= 3:
            no_op_warning = f"\n\nWARNING: Last {self.state.no_op_count} actions didn't change grid. Try different action."
        
        # Dodaj game over history
        game_over_history = ""
        if self.state.game_overs:
            game_over_history = f"\n\nGAME OVER HISTORY: {'; '.join(self.state.game_overs[-3:])}"
        
        return f"""Level: {self.state.current_level}
Action: {self.state.action_count}
Actions since level complete: {self.state.actions_since_level}
Available actions: {', '.join(available_actions)}

Grid:
{grid_str}

Recent notes: {'; '.join(self.state.notes[-4:]) if self.state.notes else 'none'}
{ml_warning}{no_op_warning}{game_over_history}

What action do you take?"""


# ---------------------------------------------------------------------------
# Extended GameState z ml_value
# ---------------------------------------------------------------------------

@dataclass
class GameStateV5_1(GameState):
    """GameState z MLP value."""
    ml_value: float = 0.5  # MLP prediction [0, 1]


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: test policy z mock LLM client i MLP
    class MockLLMClient:
        class Chat:
            class Completions:
                def create(self, **kwargs):
                    class Response:
                        class Choice:
                            class Message:
                                content = '[{"action": "RIGHT", "reasoning": "explore", "notes": "test"}]'
                            message = Message()
                        choices = [Choice()]
                    return Response()
            completions = Completions()
        chat = Chat()
    
    # Load MLP weights (placeholder)
    mlp_weights = load_mlp_weights()
    
    # Create policy
    policy = LLMPolicyV5_1(MockLLMClient(), mlp_weights)
    policy.reset()
    
    # Test frame
    frame = {
        "grid": [[0, 1, 2], [3, 4, 5], [6, 7, 8]],
        "available_actions": ["RIGHT", "LEFT", "UP", "DOWN"],
        "levels_completed": 0,
        "current_level": 1,
        "action_count": 0,
        "actions_since_level": 0,
        "lives": 3,
        "score": 0,
        "step_limit": 400,
        "no_op_count": 0,
        "goal_class": "COPY",
    }
    
    # Get action
    action = policy.get_action(frame)
    print(f"Action: {action}")
    print(f"MLP value: {policy.state.ml_value:.3f}")
