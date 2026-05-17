import matplotlib.pyplot as plt

def render_latex(formula, name, fontsize=24):
    # Use a larger figure size to avoid clipping
    fig = plt.figure(figsize=(8, 2))
    plt.text(0.5, 0.5, f'${formula}$', size=fontsize, ha='center', va='center')
    plt.axis('off')
    # No tight_layout to avoid the error, just save the figure
    plt.savefig(f'research/{name}.png', dpi=200, transparent=True, bbox_inches='tight')
    plt.close()

# Formulas (avoiding environments like pmatrix)
render_latex(r'\rho = \frac{cov(X_t, X_{t+1})}{\sigma_{X_t} \sigma_{X_{t+1}}}', 'math_rho')
render_latex(r'P_{ruin} = 1 - \frac{1 - (\frac{1-p}{p})}{1 - (\frac{1-p}{p})^N}', 'math_ruin')
render_latex(r'\alpha(t) = \alpha_0 \cdot e^{-\lambda t}', 'math_alpha')
render_latex(r'Edge = (p \cdot W) - ((1-p) \cdot L) + Buff_{mom}', 'math_edge')
render_latex(r'd^2W / dt^2 > 0', 'math_accel')
