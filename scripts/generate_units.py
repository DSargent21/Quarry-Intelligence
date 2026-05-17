import matplotlib.pyplot as plt

def render_symbol(formula, name, fontsize=20):
    fig = plt.figure(figsize=(0.6, 0.4))
    plt.text(0.5, 0.5, f'${formula}$', size=fontsize, ha='center', va='center')
    plt.axis('off')
    plt.savefig(f'research/symbol_{name}.png', dpi=200, transparent=True, bbox_inches='tight')
    plt.close()

render_symbol(r'u', 'units')
