"""
Quinielin Training Script - Finds optimal prediction weights via grid search.
Usage:
    python train.py                     (use all matchdays)
    python train.py --jornadas 50       (use last 50 matchdays)
    python train.py --jornadas 100      (use last 100 matchdays)
"""
import os
import csv
import argparse
from datetime import datetime
from itertools import product
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'bin', 'data')

# ============================================================
# 1. DATA LOADING
# ============================================================

def load_all_matches():
    matches = []
    csv_dir = os.path.abspath(DATA_DIR)
    if not os.path.exists(csv_dir):
        print(f"Error: directorio no encontrado: {csv_dir}")
        return matches
    
    for fname in sorted(os.listdir(csv_dir)):
        if not fname.endswith('.csv') or 'quiniela' in fname:
            continue
        fpath = os.path.join(csv_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        date_str = row.get('Date', '').strip()
                        home = row.get('HomeTeam', '').strip()
                        away = row.get('AwayTeam', '').strip()
                        fthg = row.get('FTHG', '').strip()
                        ftag = row.get('FTAG', '').strip()
                        ftr = row.get('FTR', '').strip()
                        if not all([date_str, home, away, fthg, ftag, ftr]):
                            continue
                        try:
                            date = datetime.strptime(date_str, '%d/%m/%Y')
                        except ValueError:
                            try:
                                date = datetime.strptime(date_str, '%d/%m/%y')
                            except ValueError:
                                continue
                        matches.append({
                            'date': date, 'home': home, 'away': away,
                            'hg': int(fthg), 'ag': int(ftag), 'result': ftr
                        })
                    except (ValueError, KeyError):
                        continue
        except Exception as e:
            print(f"Warning: {fname}: {e}")
    
    matches.sort(key=lambda m: m['date'])
    return matches


# ============================================================
# 2. MATCHDAY GROUPING
# ============================================================

def extract_matchdays(matches):
    if not matches:
        return []
    matchdays = []
    current = [matches[0]]
    start = matches[0]['date']
    for m in matches[1:]:
        if (m['date'] - start).days <= 3:
            current.append(m)
        else:
            matchdays.append(current)
            current = [m]
            start = m['date']
    if current:
        matchdays.append(current)
    return matchdays


# ============================================================
# 3. PRE-COMPUTE BUCKET STATS (the optimization)
# ============================================================

def classify_bucket(days_ago):
    """0=month (30d), 1=quarter (90d), 2=season (365d), 3=history (>365d)"""
    if days_ago <= 30: return 0
    if days_ago <= 90: return 1
    if days_ago <= 365: return 2
    return 3

def precompute_matchday_buckets(matches, matchdays):
    """
    For each matchday, pre-compute per-team stats split into 4 time buckets.
    Returns a list of dicts, one per matchday:
      { team_name: { bucket: { 'played', 'gf', 'ga', 'pts' } } }
    This way, during grid search we just do:
      weighted_stat = sum(bucket_stat[b] * weight[b] for b in 0..3)
    """
    print("Pre-calculando estadísticas por periodos temporales...")
    all_buckets = []
    
    for md_idx, matchday in enumerate(matchdays):
        ref_date = matchday[0]['date']
        team_buckets = defaultdict(lambda: {
            b: {'played': 0.0, 'gf': 0.0, 'ga': 0.0, 'pts': 0.0} for b in range(4)
        })
        
        # Only process matches before this matchday
        for m in matches:
            if m['date'] >= ref_date:
                break
            
            days_ago = (ref_date - m['date']).days
            b = classify_bucket(days_ago)
            home, away = m['home'], m['away']
            
            team_buckets[home][b]['played'] += 1
            team_buckets[away][b]['played'] += 1
            team_buckets[home][b]['gf'] += m['hg']
            team_buckets[home][b]['ga'] += m['ag']
            team_buckets[away][b]['gf'] += m['ag']
            team_buckets[away][b]['ga'] += m['hg']
            
            if m['result'] == 'H':
                team_buckets[home][b]['pts'] += 3
            elif m['result'] == 'A':
                team_buckets[away][b]['pts'] += 3
            else:
                team_buckets[home][b]['pts'] += 1
                team_buckets[away][b]['pts'] += 1
        
        all_buckets.append(dict(team_buckets))
        
        if (md_idx + 1) % 100 == 0:
            print(f"  Jornada {md_idx + 1}/{len(matchdays)} pre-calculada...")
    
    print(f"  {len(matchdays)} jornadas pre-calculadas.\n")
    return all_buckets


# ============================================================
# 4. FAST PREDICTION USING PRE-COMPUTED BUCKETS
# ============================================================

def predict_from_buckets(team_buckets, home_name, away_name, weights):
    """Predict 1X2 using pre-computed bucket stats and given weights."""
    h_b = team_buckets.get(home_name)
    a_b = team_buckets.get(away_name)
    if not h_b or not a_b:
        return None
    
    w = weights  # [w_month, w_quarter, w_season, w_history]
    
    # Weighted sums
    h_played = sum(h_b[b]['played'] * w[b] for b in range(4))
    a_played = sum(a_b[b]['played'] * w[b] for b in range(4))
    
    if h_played < 0.01 or a_played < 0.01:
        return None
    
    h_gf = sum(h_b[b]['gf'] * w[b] for b in range(4))
    h_ga = sum(h_b[b]['ga'] * w[b] for b in range(4))
    a_gf = sum(a_b[b]['gf'] * w[b] for b in range(4))
    a_ga = sum(a_b[b]['ga'] * w[b] for b in range(4))
    
    home_atk = h_gf / h_played
    home_def = h_ga / h_played
    away_atk = a_gf / a_played
    away_def = a_ga / a_played
    
    home_strength = home_atk + away_def + 0.3
    away_strength = away_atk + home_def
    total = home_strength + away_strength + 1.2  # 1.2 draw weight
    
    p1 = home_strength / total
    p2 = away_strength / total
    px = 1.0 - p1 - p2
    
    diff = abs(p1 - p2)
    if diff < 0.04:
        return 'D'
    elif p1 > p2:
        return 'H'
    return 'A'


# ============================================================
# 5. GRID SEARCH (now fast!)
# ============================================================

def run_grid_search(matchdays, all_buckets, num_jornadas=None):
    weight_options = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 1.0]
    
    if num_jornadas and num_jornadas < len(matchdays):
        start_idx = len(matchdays) - num_jornadas
    else:
        start_idx = max(20, len(matchdays) // 10)
    
    eval_range = range(start_idx, len(matchdays))
    total_matches_eval = sum(len(matchdays[i]) for i in eval_range)
    total_combos = len(weight_options) ** 4 - 1  # minus all-zeros
    
    print(f"Evaluando {total_combos} combinaciones de pesos")
    print(f"sobre {len(eval_range)} jornadas ({total_matches_eval} partidos)...\n")
    
    best_accuracy = 0.0
    best_weights = None
    top_results = []
    combo_count = 0
    
    for w0, w1, w2, w3 in product(weight_options, repeat=4):
        if w0 == 0 and w1 == 0 and w2 == 0 and w3 == 0:
            continue
        
        combo_count += 1
        if combo_count % 1000 == 0:
            print(f"  {combo_count}/{total_combos} combinaciones... (mejor hasta ahora: {best_accuracy*100:.1f}%)")
        
        weights = [w0, w1, w2, w3]
        correct = 0
        total = 0
        
        for md_idx in eval_range:
            buckets = all_buckets[md_idx]
            for m in matchdays[md_idx]:
                pred = predict_from_buckets(buckets, m['home'], m['away'], weights)
                if pred is not None:
                    total += 1
                    if pred == m['result']:
                        correct += 1
        
        if total > 0:
            accuracy = correct / total
            top_results.append((accuracy, {
                'w_month': w0, 'w_quarter': w1, 'w_season': w2, 'w_history': w3
            }))
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_weights = {'w_month': w0, 'w_quarter': w1, 'w_season': w2, 'w_history': w3}
    
    top_results.sort(key=lambda x: x[0], reverse=True)
    return best_weights, best_accuracy, top_results[:10]


# ============================================================
# 6. MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Quinielin Training')
    parser.add_argument('--jornadas', type=int, default=None,
                        help='Número de jornadas recientes a usar (default: todas)')
    args = parser.parse_args()
    
    print("=" * 60)
    print("  QUINIELIN - ENTRENAMIENTO DE PESOS")
    print("=" * 60)
    
    print("\nCargando partidos históricos...")
    matches = load_all_matches()
    print(f"Total partidos: {len(matches)}")
    
    if len(matches) < 100:
        print("Error: No hay suficientes partidos.")
        return
    
    print(f"Rango: {matches[0]['date'].strftime('%d/%m/%Y')} - {matches[-1]['date'].strftime('%d/%m/%Y')}")
    
    matchdays = extract_matchdays(matches)
    print(f"Jornadas identificadas: {len(matchdays)}")
    
    # Pre-compute bucket stats for each matchday
    all_buckets = precompute_matchday_buckets(matches, matchdays)
    
    if args.jornadas:
        print(f"Usando últimas {args.jornadas} jornadas.\n")
    else:
        print("Usando todo el dataset.\n")
    
    best_weights, best_accuracy, top10 = run_grid_search(matchdays, all_buckets, args.jornadas)
    
    if best_weights is None:
        print("\nNo se encontró ninguna combinación válida.")
        return
    
    print("\n" + "=" * 60)
    print("  RESULTADOS DEL ENTRENAMIENTO")
    print("=" * 60)
    print(f"\n  Mejor precisión: {best_accuracy * 100:.2f}%\n")
    print(f"  Pesos óptimos:")
    print(f"    Mes (últimos 30 días):   {best_weights['w_month']}")
    print(f"    Trimestre (31-90 días):  {best_weights['w_quarter']}")
    print(f"    Temporada (91-365 días): {best_weights['w_season']}")
    print(f"    Histórico (> 365 días):  {best_weights['w_history']}")
    
    print(f"\n  Top 10 combinaciones:")
    print(f"  {'Precisión':>10}  {'Mes':>6}  {'Trim':>6}  {'Temp':>6}  {'Hist':>6}")
    print(f"  {'-'*10}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*6}")
    for acc, w in top10:
        print(f"  {acc*100:>9.2f}%  {w['w_month']:>6.1f}  {w['w_quarter']:>6.1f}  {w['w_season']:>6.1f}  {w['w_history']:>6.1f}")
    
    config_path = os.path.join(os.path.abspath(DATA_DIR), 'weights.cfg')
    with open(config_path, 'w') as f:
        f.write(f"# Quinielin - Pesos óptimos (train.py)\n")
        f.write(f"# Precisión: {best_accuracy * 100:.2f}%\n")
        f.write(f"w_month={best_weights['w_month']}\n")
        f.write(f"w_quarter={best_weights['w_quarter']}\n")
        f.write(f"w_season={best_weights['w_season']}\n")
        f.write(f"w_history={best_weights['w_history']}\n")
    
    print(f"\n  Pesos guardados en: {config_path}")
    print("=" * 60)


if __name__ == '__main__':
    main()
