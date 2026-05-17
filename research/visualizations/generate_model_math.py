import os
import matplotlib.pyplot as plt

def render_math(formula, filename):
    # Use a larger figure size to avoid clipping
    fig = plt.figure(figsize=(6, 1.5))
    plt.text(0.5, 0.5, f'${formula}$', size=28, ha='center', va='center', color='#111111')
    plt.axis('off')
    plt.savefig(f'docs/assets/academic_{filename}.png', dpi=300, transparent=True, bbox_inches='tight')
    plt.close()

def generate_model_math():
    print("🎓 Generating Model-Specific Math Assets...")
    os.makedirs('docs/assets', exist_ok=True)
    
    # Sapphire: Conformal Interval
    render_math(r'C(x) = \{y \in \mathcal{Y} : S(x, y) \leq \hat{q}\}', 'sapphire_conformal')
    
    # Diamond: Momentum Velocity
    render_math(r'v_m = \frac{\Delta WR}{\Delta t} \cdot \sigma_{momentum}', 'diamond_velocity')
    
    # Quartz: Drift Analysis
    render_math(r'\Delta_{drift} = P_{consensus} - P_{market}', 'quartz_drift')
    
    # Obsidian: Bayesian Purity
    render_math(r'Purity = \int P( \alpha | D) \, d\alpha', 'obsidian_purity')
    
    # Pyrite: Liquidity Wall
    render_math(r'L_{wall} = \min_{depth} \sum_{i=1}^n \frac{\Delta P_i}{\Delta V_i}', 'pyrite_liquidity')
    
    # Kyanite: Surgical Threshold
    render_math(r'\Theta_{surgical} = \max(0.65, P_{implied} + 0.05)', 'kyanite_threshold')
    
    # Carnelian: Bayesian Yield
    render_math(r'Y_{bayesian} = \mathbb{E}[EV] \cdot \ln(n_{samples})', 'carnelian_yield')

if __name__ == "__main__":
    generate_model_math()
