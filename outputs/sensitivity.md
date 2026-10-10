# Sensitivity of the top 3 to the weights

Each weight is moved by ±10 points; the other weights are rescaled proportionally so the total stays 100.

Base top 3: **UC-01, UC-02, UC-03**.

The top-3 set is unchanged in **11 of 12** variations.

| Criterion | Change (points) | Weights after change | Top 3 | Top-3 set changed | Top-3 order changed |
|---|---|---|---|---|---|
| business_value | +10 | business_value=40.0, feasibility=17.1, data_maturity=17.1, ai_maturity=8.6, risk=8.6, strategic_fit=8.6 | UC-01, UC-02, UC-03 | no | no |
| business_value | -10 | business_value=20.0, feasibility=22.9, data_maturity=22.9, ai_maturity=11.4, risk=11.4, strategic_fit=11.4 | UC-02, UC-01, UC-03 | no | yes |
| feasibility | +10 | business_value=26.2, feasibility=30.0, data_maturity=17.5, ai_maturity=8.8, risk=8.8, strategic_fit=8.8 | UC-02, UC-01, UC-03 | no | yes |
| feasibility | -10 | business_value=33.8, feasibility=10.0, data_maturity=22.5, ai_maturity=11.2, risk=11.2, strategic_fit=11.2 | UC-01, UC-02, UC-03 | no | no |
| data_maturity | +10 | business_value=26.2, feasibility=17.5, data_maturity=30.0, ai_maturity=8.8, risk=8.8, strategic_fit=8.8 | UC-01, UC-02, UC-05 | **yes** | yes |
| data_maturity | -10 | business_value=33.8, feasibility=22.5, data_maturity=10.0, ai_maturity=11.2, risk=11.2, strategic_fit=11.2 | UC-01, UC-02, UC-03 | no | no |
| ai_maturity | +10 | business_value=26.7, feasibility=17.8, data_maturity=17.8, ai_maturity=20.0, risk=8.9, strategic_fit=8.9 | UC-01, UC-02, UC-03 | no | no |
| ai_maturity | -10 | business_value=33.3, feasibility=22.2, data_maturity=22.2, ai_maturity=0.0, risk=11.1, strategic_fit=11.1 | UC-01, UC-02, UC-03 | no | no |
| risk | +10 | business_value=26.7, feasibility=17.8, data_maturity=17.8, ai_maturity=8.9, risk=20.0, strategic_fit=8.9 | UC-02, UC-01, UC-03 | no | yes |
| risk | -10 | business_value=33.3, feasibility=22.2, data_maturity=22.2, ai_maturity=11.1, risk=0.0, strategic_fit=11.1 | UC-01, UC-02, UC-03 | no | no |
| strategic_fit | +10 | business_value=26.7, feasibility=17.8, data_maturity=17.8, ai_maturity=8.9, risk=8.9, strategic_fit=20.0 | UC-01, UC-02, UC-03 | no | no |
| strategic_fit | -10 | business_value=33.3, feasibility=22.2, data_maturity=22.2, ai_maturity=11.1, risk=11.1, strategic_fit=0.0 | UC-01, UC-02, UC-03 | no | no |
