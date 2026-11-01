# Battery research status — numerical model v0.2.0

**Unvalidated model. No physical cells, safety certification or manufacturing-cost validation.**

CC charging at 2C, discharge at 1C, currents referenced to initial capacity. No CV phase. SOC is continuous between cycles. Qualification requires at least 80% of remaining capacity delivered and a measured 10–80% SOC interval no longer than 30 minutes. A counter value is not equivalent to full cycles: see EFC.

Nominal OCV energy is not delivered energy. Wh/L remains a dry-stack estimate, and material costs cover only selected materials, excluding manufacturing and yield. Pack energy uses an assumed fixed factor, not a designed pack. Overcharge chemistry beyond full SOC is missing, so absence of a simulated thermal event cannot produce a complete safety pass. Degradation constants have NOT been recalibrated after fixes.

| configuration / konfiguracja | nominal Wh/kg | delivered Wh/kg, cycle 1 | raw cycles | qualified cycles | EFC | 10–80% min, cycle 1 | EOL | abuse coverage | physical validation |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| NMC811/LIFREE/GEL load=35 N/P=1.05 T=-10°C | 366.6 | 107.1 | 1 | 0 | 0.3 | NA | rate-limited | incomplete | unvalidated |
| NMC811/SIC/GEL load=30 N/P=1.10 T=25°C | 286.6 | 213.2 | 824 | 824 | 599.8 | 21.00 | fade80 | incomplete | unvalidated |
| NMC811/LIFREE/SOLID load=30 N/P=1.05 T=25°C | 355.6 | 165.5 | 1 | 0 | 0.5 | NA | rate-limited | incomplete | unvalidated |
| LFP/LIFREE/LP57 load=35 N/P=1.05 T=25°C | 278.1 | 256.7 | 615 | 615 | 532.6 | 21.00 | fade80 | incomplete | unvalidated |
| LFP/GRAPHITE/LP57 load=20 N/P=1.10 T=25°C | 189.6 | 180.4 | 1168 | 1168 | 1027.8 | 21.00 | fade80 | incomplete | unvalidated |
| DRX/SIC/GEL load=35 N/P=1.05 T=-10°C | 363.7 | 121.4 | 1 | 0 | 0.4 | NA | rate-limited | incomplete | unvalidated |
| NA_PW/HC/LP57 load=30 N/P=1.10 T=25°C | 188.9 | 170.4 | 271 | 271 | 224.9 | 21.00 | fade80 | incomplete | unvalidated |
| NA_NFPP/HC/SOLID load=25 N/P=1.10 T=25°C | 158.1 | 141.4 | 541 | 540 | 428.9 | 21.00 | rate-limited | incomplete | unvalidated |
| LIO2/LIMETAL/IONIC load=10 N/P=1.05 T=25°C | 437.0 | 336.3 | 32 | 1 | 24.4 | 21.00 | fade80 | incomplete | unvalidated |
| KPB/GRAPHITE/LP57 load=30 N/P=1.10 T=25°C | 169.6 | 161.9 | 407 | 407 | 364.3 | 21.00 | fade80 | incomplete | unvalidated |

No candidate is established as superior to commercial cells. No production date or production cost is established.

## Separate calendar-aging diagnostic (uncalibrated)

This phenomenological storage model is NOT coupled to cycling, pressure, gas generation or lithium-metal corrosion. Its projected years are not established shelf life.

| kandydat | shelf life @25 °C/50% SOC | shelf life @45 °C/100% SOC | retencja 10 lat @45 °C/100% |
|---|---|---|---|
| NMC811/LIFREE/GEL load=35 | 16.5 lat | 3.5 lat | 39% |
| NMC811/SIC/GEL load=30 | 17.0 lat | 3.5 lat | 39% |
| NMC811/LIFREE/SOLID load=30 | 17.5 lat | 3.5 lat | 39% |
| LFP/LIFREE/LP57 load=35 | >20 lat | 15.0 lat | 85% |
| LFP/GRAPHITE/LP57 load=20 | >20 lat | 17.5 lat | 88% |
| DRX/SIC/GEL load=35 | 7.0 lat | 1.5 lat | 0% |
| NA_PW/HC/LP57 load=30 | 7.0 lat | 4.0 lat | 52% |
| NA_NFPP/HC/SOLID load=25 | >20 lat | >20 lat | 90% |
| LIO2/LIMETAL/IONIC load=10 | 0.5 lat | 0.5 lat | 0% |
| KPB/GRAPHITE/LP57 load=30 | 11.5 lat | 7.0 lat | 70% |
Remaining gaps: silicon mechanics and formation loss; real anode-free lithium inventory and volume; electrolyte-specific mass, volume and salt compatibility; calibrated thermal geometry and reactions; combined calendar/cycling aging; independent validation datasets.

Historical audit and evidence: [audyt-2026-11-01](../audyt-2026-11-01/README.md). Release changes: [ZMIANY_V02.md](ZMIANY_V02.md). Python prototype is historical and is no longer a 1:1 reference.
