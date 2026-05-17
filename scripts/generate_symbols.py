import matplotlib.pyplot as plt

def render_symbol(formula, name, fontsize=20):
    fig = plt.figure(figsize=(1, 0.5))
    plt.text(0.5, 0.5, f'${formula}$', size=fontsize, ha='center', va='center')
    plt.axis('off')
    plt.savefig(f'research/symbol_{name}.png', dpi=200, transparent=True, bbox_inches='tight')
    plt.close()

# Symbols for inline use
render_symbol(r'\rho', 'rho')
render_symbol(r'\mathcal{F}', 'fatigue')
render_symbol(r'P', 'precision')
render_symbol(r'C', 'capacity')
render_symbol(r'\lambda', 'lambda')
render_symbol(r'\alpha', 'alpha')
render_symbol(r'\Delta', 'delta')
