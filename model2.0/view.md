# Phase 2: Daily Model – Mathematical Formulation

---

## Variables Reference

| Symbol | Description |
|:-------|:-------------|
| **x₍c₎** | Number of shelves assigned to configuration *c* |
| **I₍m,d,s,f₎** | Inventory of SKU *s* at facility *f* on day *d* of month *m* |
| **Y₍m,d,s,f₎** | Daily shipments (units shipped out) of SKU *s* from facility *f* |
| **R₍m,d,s,f₎** | Daily deliveries (units received) of SKU *s* to facility *f* |
| **u₍m,d,s₎** | Unmet demand slack (units of SKU *s* unmet on day *d* of month *m*) |
| **h₍m,d,s,f₎** | Days-on-hand slack (extra inventory buffer allowed for SKU *s* at *f*) |
| **e₍k₎⁽ˢᵃᶜ⁾** | Shelf expansion slack for Sacramento, storage type *k* |
| **e₍k₎⁽ᵃᵘˢ⁾** | Shelf expansion slack for Austin, storage type *k* |
| **Z** | Total objective function value (weighted penalty of all slacks) |

---

## Mathematical Model
\[
\begin{aligned}
&\textbf{Sets}\\
&\mathcal{S}:\text{ SKUs},\quad
\mathcal{F}=\{\mathrm{COL},\mathrm{SAC},\mathrm{AUS}\},\quad
\mathcal{K}=\{\mathrm{Bins},\mathrm{Racking},\mathrm{Pallet},\mathrm{Hazmat}\},\\
&\mathcal{M}=\{1,\dots,120\}\ (\text{months}),\quad
\mathcal{D}=\{1,\dots,21\}\ (\text{business days per month}),\quad
\mathcal{C}:\text{ shelf configurations}.\\[2mm]
&\textbf{Parameters}\\
&d_{m,d,s}\ge 0\ \ (\text{daily demand}),\quad
\mathrm{DoH}_{s,f}\ge 0,\quad
D=21,\\
&\mathrm{units}_{c,s}\ge 0,\quad
\mathrm{fac}_{c,f}\in\{0,1\},\quad
\mathrm{stype}_{c,k}\in\{0,1\},\quad
\mathrm{cap}^{\mathrm{shelf}}_{f,k}\ge 0.\\[2mm]
&\textbf{Decision Variables}\\
&x_c\ge 0\ (\text{shelves per config}),\\
&I_{m,d,s,f}\ge 0\ (\text{inventory}),\quad
Y_{m,d,s,f}\ge 0\ (\text{shipments}),\quad
R_{m,d,s,f}\ge 0\ (\text{deliveries}),\\
&u_{m,d,s}\ge 0\ (\text{unmet demand slack}),\quad
h_{m,d,s,f}\ge 0\ (\text{DoH slack}),\\
&e^{\mathrm{SAC}}_{k}\ge 0,\quad
e^{\mathrm{AUS}}_{k}\ge 0,\quad
Z\in\mathbb{R}.\\[3mm]
&\textbf{Objective: minimize penalized slack}\\
&\min\ Z\\
&\text{s.t. } Z=
\sum_{m,d,s} 1000\,u_{m,d,s}
+\sum_{m,d,s,f} 10\,h_{m,d,s,f}
+\sum_{k} 100\,e^{\mathrm{SAC}}_{k}
+\sum_{k} 100\,e^{\mathrm{AUS}}_{k}.\\[2mm]
&\textbf{Daily Demand Fulfillment}\\
&\sum_{f} Y_{m,d,s,f} + u_{m,d,s} \;\ge\; d_{m,d,s}
\qquad \forall\, m,d,s.\\[2mm]
&\textbf{Inventory Balance with Carryover}\\
&I_{1,1,s,f}= R_{1,1,s,f}-Y_{1,1,s,f}
\qquad \forall\, s,f.\\
&I_{m,d,s,f}= I_{m,d-1,s,f}+R_{m,d,s,f}-Y_{m,d,s,f}
\qquad \forall\, m,\, d=2,\dots,21,\, s,f.\\
&I_{m,1,s,f}= I_{m-1,21,s,f}+R_{m,1,s,f}-Y_{m,1,s,f}
\qquad \forall\, m=2,\dots,120,\, s,f.\\[2mm]
&\textbf{Days-on-Hand Constraint}\\
&I_{m,d,s,f}+h_{m,d,s,f}\ \ge\ d_{m,d,s}\,\mathrm{DoH}_{s,f}
\qquad \forall\, m,d,s,f.\\[2mm]
&\textbf{Capacity Link (Shelf Fit)}\\
&I_{m,d,s,f}\ \le\ \sum_{c} x_c\,\mathrm{units}_{c,s}\,\mathrm{fac}_{c,f}
\qquad \forall\, m,d,s,f.\\[2mm]
&\textbf{Shelf Limits}\\
&\sum_{c} x_c\,\mathrm{fac}_{c,\mathrm{SAC}}\,\mathrm{stype}_{c,k}
\ \le\ \mathrm{cap}^{\mathrm{shelf}}_{\mathrm{SAC},k}+e^{\mathrm{SAC}}_{k}
\qquad \forall\, k.\\
&\sum_{c} x_c\,\mathrm{fac}_{c,\mathrm{AUS}}\,\mathrm{stype}_{c,k}
\ \le\ \mathrm{cap}^{\mathrm{shelf}}_{\mathrm{AUS},k}+e^{\mathrm{AUS}}_{k}
\qquad \forall\, k.\\
&\sum_{c} x_c\,\mathrm{fac}_{c,\mathrm{COL}}\,\mathrm{stype}_{c,k}
\ \le\ \mathrm{cap}^{\mathrm{shelf}}_{\mathrm{COL},k}
\qquad \forall\, k.\\[2mm]
&\textbf{Utilization Gating (99\% if Expansion)}\\
&E\;:=\;\sum_{k}e^{\mathrm{SAC}}_{k}+\sum_{k}e^{\mathrm{AUS}}_{k},\quad M\gg 0,\\
&\sum_{c} x_c\,\mathrm{fac}_{c,f}\,\mathrm{stype}_{c,\mathrm{Pallet}}
\ \ge\ 0.99\,\mathrm{cap}^{\mathrm{shelf}}_{f,\mathrm{Pallet}} - M\!\left(1-\frac{E}{M}\right)
\qquad \forall\, f\in\{\mathrm{COL},\mathrm{SAC},\mathrm{AUS}\}.\\
\end{aligned}
\]
