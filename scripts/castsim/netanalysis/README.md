# Food-web network analysis (20 Oct 2026)

Compares three directed feeding networks (edge = eater -> eaten) per fort x layer x season, then four cast builders.

- L0: the tool's tier ladder through 16 Oct (v7.6.1), from Food Web Explorer v3 (commit f6d36122).
- L1: today's ladder (the cast builder now, with the user's bars).
- NR: New Rules.

Run (DIR is any scratch folder):

    mkdir -p DIR/v3 DIR/graph
    git show f6d36122:scripts/castsim/foodweb_sim.js > DIR/v3/foodweb_sim.js
    git show f6d36122:data/castsim/foodweb/creatures.json > DIR/v3/creatures.json
    node export.js DIR            # DIR/graph/graphs.json
    python3 analyze.py DIR        # DIR/graph/metrics.json (numpy, scipy)
    node casts.js DIR 200         # builders x forts, 200 years; DIR/graph/holes.json

Report: artifact "New Rules Network Analysis" (DwarfCron .claude/scratch/newrules-network-analysis.html).
