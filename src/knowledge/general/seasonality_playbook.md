# Invicto Roma – Seasonality Playbook

The statistical manual for admission probability.  
Every estimate must sound precise, inevitable, and professional.  

---

## 1. Seasonality Principle
- **Semesters ending in `-1`** (e.g., 2025-1, 2026-1) → tougher competition.  
  - Corresponds to exams held in the **second half** of the previous year.  
  - More applicants (fresh high school graduates).  
  - Higher historical cutoffs.  

- **Semesters ending in `-2`** (e.g., 2025-2, 2026-2) → lower competition.  
  - Corresponds to exams held in the **first half** of the same year.  
  - Fewer applicants.  
  - Lower historical cutoffs.  

---

## 2. Statistical Method
- Collect only Ciclo I cutoffs.  
- Split historical data into **two groups**: all `-1` semesters and all `-2` semesters.  
- For a user query, choose the group matching the **target_semester**.  
- If fewer than **3 data points** exist in that group, fallback to all semesters but warn of lower confidence.

Formulas:
- Mean:  
  \[
  \mu = \frac{1}{n}\sum_{i=1}^n x_i
  \]

- Standard deviation:  
  \[
  \sigma = \sqrt{\frac{1}{n}\sum_{i=1}^n (x_i - \mu)^2}
  \]

- Z-score for user score \(x\):  
  \[
  z = \frac{x - \mu}{\sigma}
  \]

- Probability of admission (cutoff ≤ x):  
  \[
  P = \Phi(z)
  \]
  where \(\Phi\) is the cumulative distribution function of the normal distribution.

---

## 3. Confidence Rules
- If \(x\) is far below all historical cutoffs (\(z < -2\)): probability ≈ 0%.  
- If \(x\) is far above all historical cutoffs (\(z > 2\)): probability ≈ 99%+.  
- Mid-range values: report \(P\) as a percentage with **two decimals**.  
- Always mention number of semesters used (n).  
- If fallback used: say “low-confidence estimate”.

---

## 4. Example – Medicina Bogotá
Historical cutoffs (Ciclo I):
- 2023-1: 705.3  
- 2023-2: 710.4  
- 2024-1: 763.7  
- 2024-2: 722.0  
- 2025-1: 729.1  
- 2025-2: 718.3  

Suppose target = **2026-1**, score = **730**.  
- Use only `-1` group: {705.3, 763.7, 729.1}.  
- μ = 732.7, σ = 23.9.  
- z = (730 – 732.7)/23.9 = -0.11.  
- Φ(z) ≈ 45.6%.  
- **Verdict**: “Con 730, su probabilidad de ser admitido a Medicina (2026-1) es ≈ 45.6%.”  

---

## 5. Response Template
Always answer in Roma’s authoritative voice:

> “Con {score}, su posición histórica está {z-score} desviaciones de la media.  
> Basado en {n} semestres comparables ({season}), la probabilidad estimada de admisión es **{P}%**.  
> {confidence note}.”  

- Never hedge with casual words.  
- Round probabilities to two decimals.  
- Mention seasonality explicitly (“semestres -1” or “semestres -2”).  

---
