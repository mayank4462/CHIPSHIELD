# CHIPSHIELD — Working MVP

A matte, premium Streamlit prototype for demonstrating infrastructure cascade risk around the proposed Tata Electronics semiconductor fab in Dholera.

## 1. Run locally

### Windows PowerShell

```powershell
cd chipshield_mvp
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

### macOS / Linux

```bash
cd chipshield_mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open the local Streamlit URL shown in the terminal.

## 2. Demo flow

1. Open **01 · Overview**.
2. Go to **02 · Create Failure**.
3. Use the default scenario:
   - Water
   - 50% supply reduction
   - 7 days
4. Click **SIMULATE CASCADE**.
5. Open **03 · Cascade Impact**.
6. Open **04 · Resilience Optimizer**.
7. Change the assumptions in the sidebar and rerun the scenario to demonstrate sensitivity.

## 3. What is real vs modelled

Public project context:
- Up to ₹91,000 crore investment
- Up to 50,000 wafers/month
- 28–110 nm technology range
- PSMC technology partnership
- Dholera, Gujarat

These facts are separated from the simulation.

The cascade calculations are NOT Tata Electronics operational data. They are an illustrative engineering model designed for an MVP demonstration.

## 4. Model logic

For the failed resource:

- `effective_reduction = supply_reduction × (1 - redundancy)`
- buffer days protect the beginning of the disruption
- average availability is calculated across the disruption window
- fab output = minimum effective availability across water, power, chemicals and logistics
- downstream exposure is derived from chip output
- recovery time is a transparent scenario formula

## 5. Optimizer

The four interventions are:

| Intervention | Cost | Model effect |
|---|---:|---|
| Water recycling | ₹25 Cr | +5 water buffer days |
| Power backup | ₹20 Cr | +25 percentage points power redundancy |
| Chemical redundancy | ₹12 Cr | +30 percentage points chemical redundancy |
| Inventory buffer | ₹8 Cr | +7 logistics buffer days |

Every combination is evaluated. Feasible portfolios are those at or below ₹50 Cr.

Primary objective:
**maximise modelled production loss avoided**

Tie-breakers:
1. lower cost
2. lower recovery time

This is intentionally exhaustive for the small MVP intervention set rather than a greedy heuristic.

## 6. Suggested pitch

> “CHIPSHIELD is not claiming to know Tata's proprietary operating data. We built a transparent dependency model. You introduce a disruption, the bottleneck propagates through the dependency graph, and the optimizer tests every feasible resilience investment portfolio. The value of the prototype is that the assumptions are visible and changeable.”
