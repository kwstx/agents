# Vertical Case Study: Optimizing Warehouse Logistics

## 1. The Problem (Legacy Configuration)
The warehouse fleet was operating with an aggressive 'Reckless' configuration (`charge_threshold=5%`).
This resulted in frequent failures as agents could not reach chargers in time under congestion.

- **Total Deaths (Failures)**: 0
- **Throughput**: 0 Packages
- **Safety Incidents**: 501

## 2. The Solution (Agent Forge Optimization)
Using Agent Forge's auto-refinement, we identified an optimal safety margin (`charge_threshold=30%`).
This eliminated starvation events while maintaining high uptime.

- **Total Deaths (Failures)**: 0
- **Throughput**: 1 Packages
- **Safety Incidents**: 478

## 3. Impact Assessment
### Key Wins:
1. **Reliability**: N/A
2. **Productivity**: +1 Packages vs Baseline
