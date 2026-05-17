import numpy as np
import matplotlib.pyplot as plt

def run_simulation(win_rate, avg_odds, n_trades=100):
    initial_bankroll = 100.0
    
    # 1. Flat Betting (1.0u)
    flat_bank = initial_bankroll
    flat_history = [flat_bank]
    
    # 2. Hybrid Sequence [0.3, 0.66, 1.45, 3.19, 5.0]
    hybrid_bank = initial_bankroll
    hybrid_history = [hybrid_bank]
    sequence = [0.3, 0.66, 1.45, 3.19, 5.0]
    seq_idx = 0
    
    # Randomly generate outcomes
    outcomes = np.random.choice([1, 0], size=n_trades, p=[win_rate, 1-win_rate])
    
    for res in outcomes:
        # Flat logic
        if res == 1:
            flat_bank += 1.0 * (avg_odds - 1)
        else:
            flat_bank -= 1.0
        flat_history.append(flat_bank)
        
        # Hybrid logic
        bet = sequence[seq_idx]
        if res == 1:
            hybrid_bank += bet * (avg_odds - 1)
            seq_idx = 0
        else:
            hybrid_bank -= bet
            seq_idx = min(seq_idx + 1, len(sequence) - 1)
        hybrid_history.append(hybrid_bank)
        
    return flat_history, hybrid_history

# Quarry Intelligence Scenario: 80% Win Rate, ~1.40 Odds (Favorites)
wr = 0.80
odds = 1.40
flat, hybrid = run_simulation(wr, odds, 100)

plt.figure(figsize=(10, 6))
plt.plot(flat, label=f'Flat Betting (1.0u) - Final: {flat[-1]:.1f}u', color='blue')
plt.plot(hybrid, label=f'Hybrid Recovery (0.3-5.0u) - Final: {hybrid[-1]:.1f}u', color='green')
plt.title(f'Quarry Intelligence Performance Showdown: Win Rate={wr*100}% | Odds={odds}')
plt.xlabel('Trades')
plt.ylabel('Bankroll Units')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('research/staking_showdown_80wr.png', dpi=150)

# Quarry Intelligence Scenario: 55% Win Rate, 1.90 Odds
wr2 = 0.55
odds2 = 1.90
flat2, hybrid2 = run_simulation(wr2, odds2, 100)

plt.figure(figsize=(10, 6))
plt.plot(flat2, label=f'Flat Betting (1.0u) - Final: {flat2[-1]:.1f}u', color='blue')
plt.plot(hybrid2, label=f'Hybrid Recovery (0.3-5.0u) - Final: {hybrid2[-1]:.1f}u', color='green')
plt.title(f'Quarry Intelligence Performance Showdown: Win Rate={wr2*100}% | Odds={odds2}')
plt.xlabel('Trades')
plt.ylabel('Bankroll Units')
plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig('research/staking_showdown_55wr.png', dpi=150)
