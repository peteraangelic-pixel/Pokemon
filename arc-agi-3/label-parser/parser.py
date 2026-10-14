#!/usr/bin/env python3
"""
Label Parser dla ARC-AGI-3

Parsuje etykiety (akcje) z odpowiedzi modelu LLM.
Formaty wejściowe:
- JSON: [{"action": "RIGHT", ...}, ...]
- Markdown: ```json [...] ```
- Tekst swobodny: "I'll move RIGHT then DOWN"

Ten parser obsługuje lekkie operacje (regex, string matching).
Dla ciężkich obliczeń (parsowanie 1000+ odpowiedzi) użyj rust/analyzer.rs
"""

import re
import json
from typing import List, Dict, Any, Optional


class LabelParserError(Exception):
    """Błąd parsowania etykiet"""
    pass


def extract_json_from_markdown(text: str) -> Optional[str]:
    """
    Wyciąga JSON z bloku markdown ```json ... ```
    
    Args:
        text: Tekst z blokiem markdown
        
    Returns:
        String JSON lub None jeśli nie znaleziono
    """
    # Szukamy ```json [...] ``` lub ```json {...} ```
    pattern = r'```json\s*(\[[\s\S]*?\]|\{[\s\S]*?\})\s*```'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    
    # Fallback: szukamy samego [...] lub {...}
    pattern = r'(\[[\s\S]*?\]|\{[\s\S]*?\})'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    
    return None


def parse_json_actions(json_str: str) -> List[Dict[str, Any]]:
    """
    Parsuje JSON z akcjami
    
    Args:
        json_str: String JSON
        
    Returns:
        Lista akcji [{"action": "RIGHT", ...}, ...]
        
    Raises:
        LabelParserError: Jeśli JSON jest nieprawidłowy
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise LabelParserError(f"Nieprawidłowy JSON: {e}")
    
    # Jeśli to pojedynczy obiekt, zamień na listę
    if isinstance(data, dict):
        data = [data]
    
    # Walidacja
    if not isinstance(data, list):
        raise LabelParserError(f"Oczekiwano listy, dostano {type(data)}")
    
    actions = []
    for item in data:
        if not isinstance(item, dict):
            raise LabelParserError(f"Każda akcja musi być obiektem, dostano {type(item)}")
        
        if 'action' not in item:
            raise LabelParserError("Brak pola 'action' w akcji")
        
        actions.append(item)
    
    return actions


def extract_actions_from_text(text: str) -> List[str]:
    """
    Wyciąga akcje z tekstu swobodnego (gdy nie ma JSON)
    
    Szuka wzorców: RIGHT, DOWN, LEFT, UP, MOUSE(x,y)
    
    Args:
        text: Tekst swobodny
        
    Returns:
        Lista nazw akcji
    """
    # Akcje kierunkowe
    direction_pattern = r'\b(RIGHT|LEFT|UP|DOWN)\b'
    directions = re.findall(direction_pattern, text, re.IGNORECASE)
    
    # Akcje MOUSE(x,y)
    mouse_pattern = r'MOUSE\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)'
    mouse_matches = re.findall(mouse_pattern, text, re.IGNORECASE)
    
    actions = []
    actions.extend([d.upper() for d in directions])
    actions.extend([f'MOUSE({x},{y})' for x, y in mouse_matches])
    
    return actions


def parse_labels(response: str) -> List[Dict[str, Any]]:
    """
    Główna funkcja parsowania etykiet
    
    Próbuje w kolejności:
    1. JSON z markdown ```json ... ```
    2. Czysty JSON
    3. Tekst swobodny
    
    Args:
        response: Odpowiedź modelu
        
    Returns:
        Lista akcji [{"action": "RIGHT", ...}, ...]
        
    Raises:
        LabelParserError: Jeśli nie udało się sparsować
    """
    if not response or not response.strip():
        raise LabelParserError("Pusta odpowiedź")
    
    # Próba 1: JSON z markdown
    json_str = extract_json_from_markdown(response)
    if json_str:
        try:
            return parse_json_actions(json_str)
        except LabelParserError:
            pass  # Kontynuuj do następnej próby
    
    # Próba 2: Czysty JSON (jeśli odpowiedź wygląda jak JSON)
    if response.strip().startswith('[') or response.strip().startswith('{'):
        try:
            return parse_json_actions(response)
        except LabelParserError:
            pass
    
    # Próba 3: Tekst swobodny
    actions = extract_actions_from_text(response)
    if actions:
        return [{'action': action, 'extracted_from': 'text'} for action in actions]
    
    raise LabelParserError("Nie udało się wyciągnąć żadnych akcji z odpowiedzi")


def validate_actions(actions: List[Dict[str, Any]], valid_actions: List[str]) -> List[bool]:
    """
    Waliduje czy akcje są poprawne
    
    Args:
        actions: Lista akcji
        valid_actions: Lista poprawnych akcji (np. ["RIGHT", "LEFT", "UP", "DOWN", "MOUSE"])
        
    Returns:
        Lista boolean (True jeśli akcja jest poprawna)
    """
    valid_set = set(a.upper() for a in valid_actions)
    results = []
    
    for action in actions:
        action_name = action.get('action', '').upper()
        
        # Sprawdź czy to poprawna akcja
        is_valid = False
        for valid in valid_set:
            if valid.startswith('MOUSE'):
                # MOUSE(x,y) - sprawdź tylko prefix
                if action_name.startswith('MOUSE'):
                    is_valid = True
                    break
            elif action_name == valid:
                is_valid = True
                break
        
        results.append(is_valid)
    
    return results


def count_invalid_actions(actions: List[Dict[str, Any]], valid_actions: List[str]) -> int:
    """
    Zlicza niepoprawne akcje
    
    Args:
        actions: Lista akcji
        valid_actions: Lista poprawnych akcji
        
    Returns:
        Liczba niepoprawnych akcji
    """
    validations = validate_actions(actions, valid_actions)
    return sum(1 for v in validations if not v)


def is_action_valid(action: Dict[str, Any], valid_actions: List[str]) -> bool:
    """
    Sprawdza czy pojedyncza akcja jest poprawna
    
    Args:
        action: Akcja do sprawdzenia
        valid_actions: Lista poprawnych akcji
        
    Returns:
        True jeśli akcja jest poprawna
    """
    action_name = action.get('action', '').upper()
    
    for valid in valid_actions:
        valid_upper = valid.upper()
        
        if valid_upper.startswith('MOUSE'):
            # MOUSE(x,y) - sprawdź tylko prefix
            if action_name.startswith('MOUSE'):
                return True
        elif action_name == valid_upper:
            return True
    
    return False


if __name__ == '__main__':
    # Testy
    test_cases = [
        # JSON z markdown
        '''Here are the actions:
```json
[{"action": "RIGHT", "reasoning": "explore"}, {"action": "DOWN"}]
```
''',
        # Czysty JSON
        '[{"action": "LEFT"}, {"action": "UP"}]',
        # Tekst swobodny
        "I'll move RIGHT then MOUSE(5,10) then DOWN",
        # Pojedynczy obiekt
        '{"action": "RIGHT"}',
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n=== Test {i} ===")
        print(f"Input: {test[:100]}...")
        try:
            actions = parse_labels(test)
            print(f"✓ Parsed {len(actions)} actions:")
            for action in actions:
                print(f"  - {action.get('action')}")
        except LabelParserError as e:
            print(f"✗ Error: {e}")
