"""SmartExplorer policy - uczy się z eksperymentów."""
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass
class ActionProposal:
    """Propozycja akcji od agenta."""
    name: str
    reasoning: str
    x: int | None = None
    y: int | None = None


@dataclass
class Snapshot:
    """Uproszczony snapshot stanu gry."""
    grid: tuple[tuple[int, ...], ...]
    available_actions: list[str]
    levels_completed: int
    state: str


class SmartExplorerPolicy:
    """Policy, który uczy się z eksperymentów.
    
    Strategia:
    1. Każda akcja jest eksperymentem - sprawdza, co się zmieniło
    2. Zapamiętuje, które akcje zmieniają grid (są "efektywne")
    3. Priorytetyzuje efektywne akcje (70% szans)
    4. Jeśli utknął (stan się nie zmienia), zmienia strategię
    5. Unika powtarzania tych samych akcji z rzędu
    """
    
    def __init__(self):
        self.last_grid: tuple[tuple[int, ...], ...] | None = None
        self.last_action: str | None = None
        self.action_stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {'total': 0, 'changed': 0, 'unchanged': 0}
        )
        self.recent_actions: list[str] = []
        self.stale_count = 0
        self.level = 0
        self.max_stale = 3
        
    def choose(self, snapshot: Snapshot) -> ActionProposal:
        """Wybierz następną akcję."""
        grid = snapshot.grid
        available = snapshot.available_actions
        
        if not available:
            return ActionProposal("RESET", "Brak dostępnych akcji")
        
        # Sprawdź, czy stan się zmienił od ostatniej akcji
        if self.last_grid is not None:
            if grid == self.last_grid:
                self.stale_count += 1
                if self.last_action:
                    self.action_stats[self.last_action]['unchanged'] += 1
            else:
                self.stale_count = 0
                if self.last_action:
                    self.action_stats[self.last_action]['changed'] += 1
        
        self.last_grid = grid
        
        # Jeśli utknęliśmy, zmień strategię
        if self.stale_count >= self.max_stale:
            self.stale_count = 0
            action = self._choose_novel_action(available)
        else:
            action = self._choose_smart_action(available)
        
        self.last_action = action
        self.action_stats[action]['total'] += 1
        self.recent_actions.append(action)
        if len(self.recent_actions) > 3:
            self.recent_actions.pop(0)
        
        reasoning = f"SmartExplorer: stale={self.stale_count}, changed={self.action_stats[action]['changed']}"
        return ActionProposal(action, reasoning)
    
    def _choose_smart_action(self, available: list[str]) -> str:
        """Wybierz akcję na podstawie statystyk."""
        # Priorytet: akcje, które wcześniej zmieniały stan
        good_actions = [a for a in available 
                       if self.action_stats[a]['changed'] > 0 
                       and a not in self.recent_actions]
        
        if good_actions and random.random() < 0.7:
            # Wybierz najlepszą
            best = max(good_actions, 
                      key=lambda a: self.action_stats[a]['changed'] / max(1, self.action_stats[a]['total']))
            return best
        
        # Nowa akcja, której jeszcze nie używaliśmy
        unused = [a for a in available if self.action_stats[a]['total'] == 0]
        if unused:
            return random.choice(unused)
        
        # Losowa akcja (ale nie ta, którą właśnie użyliśmy)
        candidates = [a for a in available if a != self.last_action]
        return random.choice(candidates) if candidates else available[0]
    
    def _choose_novel_action(self, available: list[str]) -> str:
        """Wybierz całkowicie nową akcję (po utknięciu)."""
        novel = [a for a in available if a not in self.recent_actions]
        if novel:
            return random.choice(novel)
        return random.choice(available)
    
    def reset_level(self) -> None:
        """Reset na nowy poziom."""
        self.last_grid = None
        self.last_action = None
        self.stale_count = 0
        self.recent_actions.clear()
        self.level += 1
    
    def finalize(self, snapshot: Snapshot) -> None:
        """Zakończ - zapisz statystyki."""
        pass
