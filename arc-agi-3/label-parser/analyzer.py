#!/usr/bin/env python3
"""
Label Analyzer dla ARC-AGI-3

Analizuje wiele odpowiedzi modelu paralelnie.
Wersja Python z multiprocessing (fallback gdy Rust nie jest dostępny).

Dla najlepszego performance użyj rust/analyzer (100x szybszy).
"""

import json
import sys
import time
from pathlib import Path
from multiprocessing import Pool, cpu_count
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict

from parser import parse_labels, LabelParserError, is_action_valid


@dataclass
class ParseResult:
    response_id: str
    actions_found: int
    actions_valid: int
    actions_invalid: int
    parse_success: bool
    error: str = None


@dataclass
class Statistics:
    total_responses: int
    successful_parses: int
    failed_parses: int
    total_actions: int
    valid_actions: int
    invalid_actions: int
    success_rate: float
    validity_rate: float
    parsing_time_ms: int


def parse_response_worker(model_response: Dict[str, Any]) -> Dict[str, Any]:
    """Worker function dla multiprocessing"""
    try:
        response_id = model_response.get('id', 'unknown')
        response_text = model_response.get('response', '')
        valid_actions = model_response.get('valid_actions', [])
        
        actions = parse_labels(response_text)
        total = len(actions)
        
        # Walidacja akcji
        valid_count = sum(1 for a in actions if is_action_valid(a, valid_actions))
        invalid_count = total - valid_count
        
        return asdict(ParseResult(
            response_id=response_id,
            actions_found=total,
            actions_valid=valid_count,
            actions_invalid=invalid_count,
            parse_success=True
        ))
    except LabelParserError as e:
        return asdict(ParseResult(
            response_id=model_response.get('id', 'unknown'),
            actions_found=0,
            actions_valid=0,
            actions_invalid=0,
            parse_success=False,
            error=str(e)
        ))


def analyze_responses(responses: List[Dict[str, Any]], use_multiprocessing: bool = True) -> Tuple[List[Dict], Statistics]:
    """
    Analizuje wiele odpowiedzi paralelnie
    
    Args:
        responses: Lista odpowiedzi modelu
        use_multiprocessing: Czy używać multiprocessing (dla dużych zbiorów)
        
    Returns:
        (wyniki, statystyki)
    """
    start_time = time.time()
    
    if use_multiprocessing and len(responses) > 10:
        # Multiprocessing dla dużych zbiorów
        num_workers = min(cpu_count(), len(responses))
        print(f"🔧 Używam {num_workers} workerów multiprocessing")
        
        with Pool(num_workers) as pool:
            results = pool.map(parse_response_worker, responses)
    else:
        # Sequentualnie dla małych zbiorów
        results = [parse_response_worker(r) for r in responses]
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    # Oblicz statystyki
    total = len(results)
    successful = sum(1 for r in results if r['parse_success'])
    failed = total - successful
    
    total_actions = sum(r['actions_found'] for r in results)
    valid_actions = sum(r['actions_valid'] for r in results)
    invalid_actions = sum(r['actions_invalid'] for r in results)
    
    success_rate = successful / total if total > 0 else 0.0
    validity_rate = valid_actions / total_actions if total_actions > 0 else 0.0
    
    stats = Statistics(
        total_responses=total,
        successful_parses=successful,
        failed_parses=failed,
        total_actions=total_actions,
        valid_actions=valid_actions,
        invalid_actions=invalid_actions,
        success_rate=success_rate,
        validity_rate=validity_rate,
        parsing_time_ms=elapsed_ms
    )
    
    return results, stats


def generate_test_data(num_responses: int = 100) -> List[Dict[str, Any]]:
    """Generuje testowe dane"""
    test_responses = []
    
    # Szablony odpowiedzi
    templates = [
        # JSON z markdown
        lambda i: {
            'id': f'response_{i}',
            'response': f'Here are actions:\n```json\n[{{"action": "RIGHT"}}, {{"action": "DOWN"}}]\n```',
            'valid_actions': ['RIGHT', 'LEFT', 'UP', 'DOWN', 'MOUSE']
        },
        # Czysty JSON
        lambda i: {
            'id': f'response_{i}',
            'response': '[{"action": "LEFT"}, {"action": "UP"}]',
            'valid_actions': ['RIGHT', 'LEFT', 'UP', 'DOWN', 'MOUSE']
        },
        # Tekst swobodny
        lambda i: {
            'id': f'response_{i}',
            'response': f'I\'ll move RIGHT then MOUSE({i},{i}) then DOWN',
            'valid_actions': ['RIGHT', 'LEFT', 'UP', 'DOWN', 'MOUSE']
        },
        # Niepoprawna akcja
        lambda i: {
            'id': f'response_{i}',
            'response': '[{"action": "JUMP"}, {"action": "RIGHT"}]',
            'valid_actions': ['RIGHT', 'LEFT', 'UP', 'DOWN', 'MOUSE']
        },
        # Pusta odpowiedź
        lambda i: {
            'id': f'response_{i}',
            'response': '',
            'valid_actions': ['RIGHT', 'LEFT', 'UP', 'DOWN', 'MOUSE']
        },
    ]
    
    for i in range(num_responses):
        template_idx = i % len(templates)
        test_responses.append(templates[template_idx](i))
    
    return test_responses


def main():
    if len(sys.argv) < 2:
        print("Użycie: python analyzer.py <plik_z_odpowiedziami.json> [--test]")
        print("\nOpcje:")
        print("  --test    Generuje testowe dane (100 odpowiedzi)")
        print("\nFormat pliku JSON:")
        print('[')
        print('  {')
        print('    "id": "response_1",')
        print('    "response": "```json\\n[{\\\"action\\\": \\\"RIGHT\\\"}]\\n```",')
        print('    "valid_actions": ["RIGHT", "LEFT", "UP", "DOWN", "MOUSE"]')
        print('  },')
        print('  ...')
        print(']')
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Tryb testowy
    if '--test' in sys.argv:
        print("🧪 Generowanie testowych danych (100 odpowiedzi)...")
        responses = generate_test_data(100)
        
        # Zapisz do pliku
        test_file = input_file
        with open(test_file, 'w') as f:
            json.dump(responses, f, indent=2)
        print(f"💾 Testowe dane zapisano do {test_file}\n")
    else:
        # Wczytaj z pliku
        print(f"📖 Wczytywanie odpowiedzi z {input_file}")
        with open(input_file, 'r') as f:
            responses = json.load(f)
    
    print(f"📊 Znaleziono {len(responses)} odpowiedzi")
    print("🔍 Analiza paralelna z multiprocessing...\n")
    
    # Analizuj
    results, stats = analyze_responses(responses, use_multiprocessing=True)
    
    # Wydrukuj wyniki
    print("=== Wyniki parsowania ===\n")
    
    for result in results[:20]:  # Pokaż pierwsze 20
        if result['parse_success']:
            print(f"✓ {result['response_id']} - {result['actions_found']} akcji "
                  f"({result['actions_valid']} poprawnych, {result['actions_invalid']} niepoprawnych)")
        else:
            print(f"✗ {result['response_id']} - BŁĄD: {result['error']}")
    
    if len(results) > 20:
        print(f"... i {len(results) - 20} więcej\n")
    
    # Wydrukuj statystyki
    print("=== Statystyki ===\n")
    print(f"Łączna liczba odpowiedzi: {stats.total_responses}")
    print(f"Udane parsowania: {stats.successful_parses} ({stats.success_rate*100:.1f}%)")
    print(f"Nieudane parsowania: {stats.failed_parses}")
    print(f"Łączna liczba akcji: {stats.total_actions}")
    print(f"Poprawne akcje: {stats.valid_actions} ({stats.validity_rate*100:.1f}%)")
    print(f"Niepoprawne akcje: {stats.invalid_actions}")
    print(f"Czas parsowania: {stats.parsing_time_ms} ms")
    
    if stats.parsing_time_ms > 0 and stats.total_responses > 0:
        per_response = stats.parsing_time_ms / stats.total_responses
        print(f"Średni czas na odpowiedź: {per_response:.2f} ms")
    
    # Zapisz statystyki
    stats_dict = asdict(stats)
    output_file = f"{input_file.rsplit('.', 1)[0]}.stats.json"
    with open(output_file, 'w') as f:
        json.dump(stats_dict, f, indent=2)
    print(f"\n💾 Statystyki zapisano do {output_file}")


if __name__ == '__main__':
    main()
