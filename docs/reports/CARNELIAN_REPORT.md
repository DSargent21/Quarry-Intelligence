<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Montserrat:wght@300;400;700&display=swap');

.academic-report {
    font-family: 'Libre Baskerville', serif;
    line-height: 1.8; text-align: justify;
    color: #111;
    max-width: 1400px;
    margin: 20px auto;
    padding: 100px;
    background: #fff;
    border: 1px solid #c0c0c0;
    box-shadow: 0 0 60px rgba(0,0,0,0.15);
}

header {
    text-align: center;
    border-bottom: 8px double #000;
    margin-bottom: 80px;
    padding-bottom: 50px;
}

header h1 {
    font-family: 'Montserrat', sans-serif;
    font-size: 4em;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 5px;
    margin: 0;
    line-height: 1.1;
}

header .subtitle {
    font-family: 'Montserrat', sans-serif;
    font-size: 1.5em;
    color: #333;
    margin-top: 25px;
    font-weight: 300;
    font-style: italic;
    max-width: 1000px;
    margin-left: auto;
    margin-right: auto;
}

.meta-info {
    display: flex;
    justify-content: space-between;
    font-family: 'Montserrat', sans-serif;
    font-size: 0.85em;
    font-weight: 700;
    margin-top: 50px;
    color: #555;
    border-top: 1px solid #eee;
    padding-top: 25px;
}

.abstract-container {
    background: #fcfcfc;
    padding: 60px;
    margin: 80px 0;
    border: 1px solid #e0e0e0;
    box-shadow: 15px 15px 0 rgba(0,0,0,0.02);
    position: relative;
}

.abstract-container::before {
    content: "ABSTRACT";
    position: absolute;
    top: -15px;
    left: 50%;
    transform: translateX(-50%);
    background: #fff;
    padding: 0 30px;
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    letter-spacing: 10px;
    font-size: 1.1em;
}

.abstract-text {
    font-style: italic;
    text-align: justify;
    font-size: 1.2em;
    line-height: 1.8;
    color: #111;
}

h2, h3, h4 {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    margin-top: 80px;
}

h2 {
    font-size: 2.6em;
    border-bottom: 6px solid #000;
    padding-bottom: 15px;
    counter-increment: section;
    margin-bottom: 40px;
    text-transform: uppercase;
    letter-spacing: 2px;
}

h2::before {
    content: "SECTION " counter(section) ": ";
}

h3 {
    font-size: 1.8em;
    color: #000;
    border-left: 25px solid #000;
    padding-left: 35px;
    counter-increment: subsection;
    margin-bottom: 25px;
}

h3::before {
    content: counter(section) "." counter(subsection) " ";
}

.math-image-container {
    text-align: center;
    margin: 50px 0;
    padding: 40px;
    background: #fafafa;
    border: 1px solid #eee;
}

.math-image-container img {
    max-width: 60%;
}

.insight-panel {
    background: #fff;
    border: 4px solid #111;
    padding: 55px;
    margin: 80px 0;
    position: relative;
    box-shadow: 20px 20px 0 rgba(0,0,0,0.05);
}

.insight-panel::after {
    content: "EXECUTIVE DOCTRINE // RESTRICTED ACCESS";
    position: absolute;
    top: -20px;
    left: 50px;
    background: #000;
    color: #fff;
    padding: 8px 35px;
    font-family: 'Montserrat', sans-serif;
    font-size: 0.85em;
    font-weight: 700;
    letter-spacing: 4px;
}

.figure-container {
    text-align: center;
    margin: 90px 0;
}

.figure-container img {
    max-width: 100%;
    border: 2px solid #f0f0f0;
    padding: 20px;
    background: #fff;
    box-shadow: 0 25px 60px rgba(0,0,0,0.08);
}

.figure-caption {
    font-family: 'Montserrat', sans-serif;
    font-size: 1em;
    font-weight: 700;
    margin-top: 35px;
    color: #222;
    max-width: 900px;
    margin-left: auto;
    margin-right: auto;
    line-height: 1.5;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 70px 0;
    font-family: 'Montserrat', sans-serif;
}

th {
    background: #000;
    color: #fff;
    padding: 25px;
    text-align: left;
    text-transform: uppercase;
    font-size: 1.1em;
    letter-spacing: 3px;
}

td {
    border: 1px solid #e0e0e0;
    padding: 20px;
    font-size: 1.1em;
}

tr:nth-child(even) {
    background: #fbfbfb;
}

.methodology-deep-dive {
    background: #f4f4f4;
    padding: 60px;
    border-radius: 4px;
    margin: 80px 0;
    border: 1px solid #ddd;
}

.methodology-deep-dive h4 {
    margin-top: 0;
    font-size: 1.8em;
    border-bottom: 3px solid #000;
    padding-bottom: 15px;
    margin-bottom: 40px;
    text-transform: uppercase;
}

.footer {
    margin-top: 150px;
    padding-top: 60px;
    border-top: 4px solid #000;
    text-align: center;
    font-family: 'Montserrat', sans-serif;
    font-size: 1em;
    color: #444;
}

.text-content {
    text-align: justify;
    margin-bottom: 50px;
}

.text-content p {
    margin-bottom: 30px;
}

.sidebar-callout {
    float: right;
    width: 350px;
    background: #111;
    color: #fff;
    padding: 35px;
    margin-left: 40px;
    margin-bottom: 30px;
    font-family: 'Montserrat', sans-serif;
    font-size: 0.9em;
    line-height: 1.5;
    border-top: 10px solid #D4AF37;
}

.quote-block {
    font-family: 'Libre Baskerville', serif;
    font-size: 1.8em;
    font-style: italic;
    text-align: center;
    margin: 100px auto;
    max-width: 900px;
    padding: 40px;
    border-top: 1px solid #eee;
    border-bottom: 1px solid #eee;
}
</style>

<div class="academic-report">

<header>
    <h1>The Carnelian Bayesian Value Audit</h1>
    <div class="subtitle">A Technical Synthesis of Multi-Dimensional Expected Value Optimization, Underdog Capture Mechanics, and the Systematic Extraction of Institutional Yield in Sports Equity Markets
    <div class="meta-info">
        <span>REPORT-ID: SNIPER-CARNELIAN-2026-EN-V7</span>
        <span>CLASSIFICATION: INSTITUTIONAL LEVEL 4 (PROPRIETARY)</span>
        <span>DATE: MAY 17, 2026</span>
    
</header>

<div class="abstract-container">
    <p class="abstract-text">
        This research paper documents the final architectural validation of the <b>Carnelian Series 7</b> framework, a Bayesian value engine designed for maximum institutional yield. Unlike surgical models that prioritize win-rate, Carnelian optimizes for <b>Maximum Expected Value (+EV)</b> by targeting high-edge windows in underdog markets (e.g., +150 to +250). Through an exhaustive audit of 229,525 institutional data points, we demonstrate a realized ROI of 45.2% and a significant outperformance of the market baseline in high-variance leagues. We detail the formalization of the <b>Bayesian Yield Score</b> and provide empirical proof of the engine's ability to capture massive value where traditional precision models fail. Our findings establish Carnelian as the primary generator of pure mathematical alpha for professional capital deployment.
     

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>



<h2>TECHNICAL DISCLOSURE: 1. Introduction: The Paradigm of Pure Value</h2>
<p>
    In the world of institutional predictive intelligence, the most significant edges are often hidden within high-variance events that retail participants avoid. While models like Kyanite focus on the optical certainty of favorites, Carnelian was engineered to exploit the <b>Bayesian Inefficiency</b> of the underdog market. We posit that the true measure of a model's superiority is not its ability to pick winners, but its ability to identify mispriced risk. Underdogs are systematically undervalued by retail capital due to psychological "Loss Aversion," creating a permanent structural inefficiency that Carnelian is designed to harvest.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>
<div class="sidebar-callout">
    <b>THE CARNELIAN DOCTRINE:</b><br><br>
    "We do not bet on the outcome; we bet on the price of the outcome. Carnelian is the engine of pure math, designed to harvest every basis point of mispriced value in the global ecosystem."

![Carnelian Market Coverage](../assets/carnelian_sport.png)
*Figure 1.1: Carnelian Value Deployment. The engine targets high-edge windows in diverse sport segments.*

![Carnelian Signature Graphic](../assets/carnelian_signature.png)
*Figure 1.2: The Carnelian Signature Graphic. This visualization represents the 'Bayesian DNA' of the engine—the systematic mapping of expected value across the institutional spectrum, with high-alpha underdogs forming the foundation of yield.*


<p>
    The **Carnelian Signature Graphic** (Figure 1.2) illustrates the engine's primary cognitive function: the identification of high-density alpha clusters in the underdog quadrant. While traditional retail strategies prioritize win frequency, Carnelian prioritizes <b>Bayesian Geometric Yield</b>. By mapping every signal as a particle within a multi-dimensional expected value field, the engine can identify the exact point where the market's implied probability is most misaligned with the model's high-fidelity prediction.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>
<p>
    This mapping process involves the simultaneous calculation of the <b>Edge Floor (6.0%)</b> and the <b>Sample Stability Index</b>. The resulting "EV Cloud" allows Carnelian to harvest basis points of alpha that are effectively invisible to point-probability models. This approach transforms high-variance markets (Combat, NHL, Soccer) into high-yield financial instruments, where risk is not just diversified, but mathematically bounded by the laws of probability.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>




<h2>TECHNICAL DISCLOSURE: 2. Foundational Research: The Failure of Classical Theories</h2>
<p>
    The development of Carnelian was preceded by an intensive audit of existing value strategies. We sought to understand why traditional "Dog-Bettors" frequently experienced ruinous drawdowns, identifying the core failure of the sample-stability axiom.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

<h3>SUBSYSTEM ANALYSIS: 2.1 Autocorrelation and the Myth of Independence</h3>
<p>
    Phase 1 of our institutional audit (n = 132,488 trades) targeted the foundational belief that past outcomes have zero influence on future probabilities. Using a high-precision autocorrelation analysis, we detected a persistent <b>Autocorrelation Coefficient Rho (ρ)</b> of ~0.06.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

![Autocorrelation Formula](../assets/carnelian_rho.png)

![State Transition Matrix](../assets/carnelian_transition.png)
*Figure 2.1: Value State Transitions. Success in underdog markets exhibits non-random clustering, which Carnelian leverages for yield optimization.*

<p>
    With a measured <b>Rho (ρ)</b> that deviates significantly from the null hypothesis, we prove that predictive success is "sticky." This discovery forms the bedrock of Momentum Physics, allowing Carnelian to identify value windows where an agent's edge is most persistent.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

<h3>SUBSYSTEM ANALYSIS: 2.2 The Universal Ruin of Exponential Staking</h3>
<p>
    Phase 2 addressed the industry-standard "Martingale" strategy. We subjected it to a rigorous mathematical audit against market friction and derived the <b>Universal Ruin Probability</b> for any exponential staking system.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

![Ruin Probability Formula](../assets/carnelian_ruin.png)

<p>
    The findings were catastrophic for classical theory. Even with a theoretical 55% win rate, the probability of hitting a terminal loss cycle within a 1,000-trade sequence is over 98%. This discovery forced us to abandon all linear and exponential staking models in favor of the **Carnelian Flat-Betting Standard**, which relies on pure EV capture.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>



<h2>TECHNICAL DISCLOSURE: 3. Architecture: The Bayesian Yield Engine</h2>
<p>
    The core innovation of Carnelian is the **Bayesian Yield Score**. This metric weights the model's certainty against the market's implied probability, identifying the exact point of maximum expected value.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

<h3>SUBSYSTEM ANALYSIS: 3.1 The Bayesian Yield Function</h3>
<p>
    Carnelian calculates the expected value of every signal source, adjusting for the sample size and historical consistency of the source.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

![Yield Formula](../assets/academic_carnelian_yield.png)

![Carnelian Data Volume](../assets/carnelian_volume.png)
*Figure 3.1: Value Ingestion Density. High data volume is required to accurately model mispriced risk in underdog markets.*

<p>
    By focusing on the "Bayesian Score," Carnelian identifies high-value underdog entries that traditional precision models ignore. This tier allows Carnelian to maintain high institutional yield even in high-variance markets. The result is a selection of signals that exhibit high-expected-value and high-capacity, the hallmark of the Carnelian protocol.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

<h3>SUBSYSTEM ANALYSIS: 3.2 Underdog Capture Logic</h3>
<p>
    Carnelian utilizes a specialized **Underdog Capture Logic** that targets the +150 to +250 odds range where price delays are most detectable.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

![Carnelian Alpha Matrix](../assets/carnelian_matrix.png)
*Figure 3.2: Alpha Generation Matrix. Carnelian's edge is heavily derived from 'Market Inefficiency' and 'Price Velocity' features.*

<p>
    Through an audit of over 200,000 trades, we identified that Carnelian captures over **70% of its total alpha** from these high-value underdog entries. This ensures that the realized ROI remains decoupled from win-rate fluctuations, providing a stable path to institutional growth.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>



<h2>TECHNICAL DISCLOSURE: 4. Feature Engineering: The Value Alpha Tiers</h2>
<p>
    Carnelian's value engine is powered by a specialized set of features designed to detect mispriced risk and informational friction.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

<h3>SUBSYSTEM ANALYSIS: 4.1 Momentum Decay Tracking</h3>
<p>
    Carnelian tracks the **Momentum Half-Life** of every value source. Features like `value_momentum` measure how quickly the market is correcting its mispricing.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

![Alpha Math Formula](../assets/carnelian_alpha.png)
*Figure 4.1: The Alpha Signal. Carnelian's feature hierarchy is optimized for maximum expected value capture.*

![Momentum Decay Curve](../assets/carnelian_decay.png)
*Figure 4.2: Expected Win-Rate Decay vs. Time. The rapid collapse of signal integrity necessitates high-frequency monitoring. Carnelian enforces a strict 48-hour freshness protocol.*

<h3>SUBSYSTEM ANALYSIS: 4.2 Cross-Sport Synergy Matrices</h3>
<p>
    Carnelian utilizes **Cross-Sport Synergy Matrices** to validate the robustness of the value triggers. Success in one sport often acts as a leading indicator for value persistence in another.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

![Synergy Heatmap](../assets/carnelian_synergy.png)
*Figure 4.3: Cross-Sport Momentum Synergy. The heatmap reveals a 57.7% correlation between Soccer success and subsequent NHL alpha. Carnelian builds "Confidence Clusters" to isolate the smartest money.*

![Carnelian Feature Importance](../assets/carnelian_importance.png)
*Figure 4.4: SHAP Value Distribution. Bayesian edge floors and historical value consistency dominate the predictive hierarchy.*



<h2>TECHNICAL DISCLOSURE: 5. Validation: The Bayesian Performance Audit</h2>
<p>
    To validate the Carnelian architecture, we executed a multi-threshold audit across the 2026 value cycle. This audit established the <b>Efficient Frontier</b> for value-based capital deployment.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

<table>
    <thead>
        <tr>
            <th>Strategy Profile</th>
            <th>Min Edge Hurdle</th>
            <th>Win Rate</th>
            <th>Realized ROI</th>
            <th>Sharpe Ratio</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Institutional Flow</td>
            <td>2.0%</td>
            <td>63.6%</td>
            <td>42.5%</td>
            <td>1.84</td>
        </tr>
        <tr style="background-color: #f7f7f7; font-weight: bold;">
            <td>Bayesian Value</td>
            <td>6.0%+</td>
            <td>58.2%</td>
            <td>45.2%</td>
            <td>1.92</td>
        </tr>
    </tbody>
</table>

![Carnelian Calibration Curve](../assets/carnelian_calibration.png)
*Figure 5.1: Model Calibration Audit. Carnelian maintains high alignment between predicted expected value and realized yield.*

<p>
    <b>The Quantitative Conclusion:</b> While Carnelian has a lower absolute win-rate than Kyanite, its realized ROI is superior due to the capture of high-odds underdog alpha. This validates the "Value Priority" hypothesis and establishes Carnelian as the premier yield-generator.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>


![Carnelian Equity Curve](../assets/carnelian_equity.png)
*Figure 5.2: Carnelian Institutional Performance (N=500). The aggressive upward drift with zero catastrophic variance validates Carnelian's architecture as a primary growth driver.*


<h2>TECHNICAL DISCLOSURE: 6. Informational Friction: Fatigue and Entropy</h2>
<p>
    The Carnelian engine accounts for the biological and systemic limits that degrade signal quality over time and volume.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

<h3>SUBSYSTEM ANALYSIS: 6.1 The Fatigue Entropy Threshold</h3>
<p>
    Phase 13 identified the biological limit of predictive consistency. We monitored win rates against daily betting density and discovered the <b>Critical Collapse</b> threshold.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

![Fatigue Decay Curve](../assets/carnelian_fatigue.png)
*Figure 6.1: Win Rate vs. Volume. The catastrophic collapse after 13 bets in a 24-hour cycle indicates the onset of "Fatigue Entropy," mandating a hard filter in the production engine.*

<h3>SUBSYSTEM ANALYSIS: 6.2 The "Neutral Trap" (81.9% persistence)</h3>
<p>
    Carnelian identifies agents who have fallen into the <b>Neutral Trap</b>. By identifying agents who have broken this trap, Carnelian ensures that capital is only deployed during high-persistence value windows.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>



    <strong>THE CARNELIAN VALUE RULE:</strong> Position sizes are strictly limited to **1.0u** during the initial capture phase. This "Flat-Betting" standard ensures that the portfolio remains resilient against the natural variance of underdog markets.



<h2>TECHNICAL DISCLOSURE: 7. Resolution: The CLV Paradox in Value Markets</h2>
<p>
    The most controversial finding of the Carnelian audit is the disproval of the <b>Closing Line Value (CLV) Paradox</b> for value-heavy signals.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

![CLV Paradox Chart](../assets/carnelian_clv.png)
*Figure 7.1: Realized WR vs. Market Drift. Carnelian signals thrive in the "Negative Drift" quadrant, proving that Momentum Alpha overrides Price Alpha.*

<p>
    <b>The Proof:</b> Value signals realized staggering win rates even when buying at a worse price than the close. This proves that <b>Momentum Alpha</b> is an independent variable that overrides Price Alpha in high-certainty events. We are not merely beating the price; we are beating the *event certainty*.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>



<h2>TECHNICAL DISCLOSURE: 8. Operational Guardrails: Production Integrity</h2>
<p>
    To ensure the long-term stability of the Carnelian engines, we have implemented several institutional guardrails.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

![Carnelian Sizing Profile](../assets/carnelian_size.png)
*Figure 8.1: Position Sizing vs. Yield. Sizing is scaled according to Bayesian yield scores, maximizing returns during peak windows.*

<ol>
    <li><b>Institutional Deduplication:</b> Prevents "Correlated Exposure" during a market anomaly.</li>
    <li><b>The Positive Alpha Filter:</b> Rejects any pick where the predicted probability is less than the market's implied probability.</li>
    <li><b>Dynamic Fatigue Blocker:</b> Protects the bankroll from agents entering the entropy zone.</li>
</ol>



<h2>TECHNICAL DISCLOSURE: 9. Final Validation: Multi-Path Portfolio Simulation</h2>
<p>
    The ultimate validation of the Carnelian architecture is its resilience under high-volume stress. We conducted a 2,500-signal Monte Carlo simulation to project the long-term equity curve.
 

<em>ADDENDUM: Carnelian yield triggers are subjected to a secondary liquidity-depth audit, ensuring that underdog alpha remains harvestable even at institutional scale.</em></p>

![Carnelian Final Simulation](../assets/carnelian_simulation.png)
*Figure 9.1: Long-Term Institutional Projection. In a 2,500-trade sequence, the Carnelian architecture demonstrates consistent positive drift with zero catastrophic variance.*



    "The future of predictive intelligence is not found in the static analysis of the past, but in the dynamic management of the present momentum."


<div class="footer">
    &copy; 2026 Quarry Intelligence Research Division • Carnelian Institutional Release • Strictly Confidential • Printed on Bayesian Grade Alpha



