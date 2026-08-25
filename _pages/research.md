---
layout: page
title: research
permalink: /research/
nav: true
nav_order: 3
description: Research positions, ongoing work, and the software I have built.
---

<link rel="stylesheet" href="{{ '/assets/css/kt.css' | relative_url }}" />
<script>document.documentElement.classList.add("kt-js");</script>

<div data-kt-progress></div>

<div class="kt-hero kt-reveal" markdown="0">
  <span class="kt-eyebrow">Research</span>
  <p>
    My work sits at the intersection of <strong>language model evaluation</strong>,
    <strong>efficient deep learning</strong>, and <strong>interpretability</strong> — three angles on the
    same question of whether a reported number reflects a capability you can depend on.
  </p>
</div>

## Research positions

<div class="kt-timeline">

<div class="kt-tl-item kt-card kt-reveal" markdown="1">

<div class="kt-tl-head">
  <span class="kt-tl-title">Research Intern</span>
  <span class="kt-tl-date">2026 — present</span>
</div>

<div class="kt-tl-org">University of Arizona · College of Information Science</div>
<div class="kt-tl-sub">Advisor: Prof. Haw-Shiuan Chang · Remote</div>

<div class="kt-badges">
  <span class="kt-badge kt-badge--accent">Decoding</span>
  <span class="kt-badge">Language models</span>
  <span class="kt-badge">Numerical stability</span>
</div>

Extending **Asymptotic Probability Decoding** (Chang et al., 2024) from extrapolation across model
_scale_ to extrapolation across _context length_.

<details class="kt-details" markdown="1" open>
<summary>What the work involves</summary>

- Removing the method's reliance on a family of same-recipe language models at multiple sizes — the
  requirement that makes it impractical for most model families in the wild.
- Auditing the training pipeline against the original formulation to isolate sources of training
  instability: the curve-fitting objective, top-_k_ candidate selection, and the numerical conditioning
  of the parametric decay fit.

</details>

</div>

<div class="kt-tl-item kt-card kt-reveal" data-kt-delay="80" markdown="1">

<div class="kt-tl-head">
  <span class="kt-tl-title">Undergraduate Researcher</span>
  <span class="kt-tl-date">2024 — 2026</span>
</div>

<div class="kt-tl-org">North South University · Department of ECE</div>
<div class="kt-tl-sub">Advisor: Prof. Shafin Rahman · Dhaka, Bangladesh</div>

<div class="kt-badges">
  <span class="kt-badge">Lottery Ticket Hypothesis</span>
  <span class="kt-badge">Hyperspectral</span>
  <span class="kt-badge">Evaluation protocols</span>
  <span class="kt-badge">Formal languages</span>
</div>

Three lines of work across pruning, evaluation, and benchmark construction.

<details class="kt-details" markdown="1" open>
<summary>Project detail</summary>

- **Sparse subnetworks in hyperspectral image classification** under the Lottery Ticket Hypothesis.
  Iterative magnitude pruning across 3D CNN, hybrid 3D–2D CNN, and Mamba backbones, evaluated on three
  benchmark scenes.
- **Evaluation protocols for post-training language model assessment**, separating instruction-following
  compliance from answer correctness across arithmetic, logical, and code-generation benchmarks.
- **Benchmark construction and automated evaluation pipelines** for formal-language tasks spanning the
  Chomsky hierarchy.

</details>

</div>

</div>

## Selected software

<div class="kt-filters" data-kt-filter="software">
  <span class="kt-filter-label">Stack</span>
  <button type="button" class="kt-chip" data-kt-value="all" aria-pressed="true">All</button>
  <button type="button" class="kt-chip" data-kt-value="web" aria-pressed="false">Web</button>
  <button type="button" class="kt-chip" data-kt-value="ml" aria-pressed="false">Machine learning</button>
</div>

<div class="kt-grid">

<div class="kt-card kt-reveal" data-kt-group="software" data-kt-tags="web ml" markdown="1">

<div class="kt-card-title">DrukAgriLink</div>
<div class="kt-card-meta">2025 · Agricultural coordination platform for Bhutanese smallholder farmers</div>

A multi-role platform — farmers, buyers, coordinators, transporters — implementing a staged workflow
from harvest listing through demand matching to fulfillment, with role-based access enforced by
**PostgreSQL row-level security**. Integrates the 1,051-record Bhutanese administrative hierarchy
(Dzongkhag–Gewog–Chiwog) into a cascading selector for standardized geographic entry.

<div class="kt-badges">
  <span class="kt-badge">Next.js</span>
  <span class="kt-badge">TypeScript</span>
  <span class="kt-badge">Supabase</span>
  <span class="kt-badge">PostgreSQL</span>
  <span class="kt-badge">Tailwind CSS</span>
</div>

<div class="kt-actions">
  <a class="kt-btn" href="https://druk-agri-link.vercel.app" target="_blank" rel="noopener">Live site</a>
</div>

</div>

<div class="kt-card kt-reveal" data-kt-delay="80" data-kt-group="software" data-kt-tags="ml" markdown="1">

<div class="kt-card-title">IntelliExpense</div>
<div class="kt-card-meta">2024 · Machine learning system for personal expenditure analysis · Course project</div>

Expense classification, budget forecasting, and spending-pattern analysis over user transaction
histories.

<div class="kt-badges">
  <span class="kt-badge">Django</span>
  <span class="kt-badge">scikit-learn</span>
  <span class="kt-badge">Pandas</span>
  <span class="kt-badge">NLTK</span>
</div>

</div>

</div>

<div class="kt-empty kt-hidden" data-kt-empty="software">Nothing matches that filter.</div>

## Technical skills

<div class="kt-skills">

<div class="kt-skill-row kt-reveal">
  <span class="kt-skill-name">Languages</span>
  <div class="kt-badges" style="margin: 0">
    <span class="kt-badge">Python</span><span class="kt-badge">C</span><span class="kt-badge">C++</span><span class="kt-badge">Java</span><span class="kt-badge">TypeScript</span><span class="kt-badge">SQL</span>
  </div>
</div>

<div class="kt-skill-row kt-reveal">
  <span class="kt-skill-name">ML stack</span>
  <div class="kt-badges" style="margin: 0">
    <span class="kt-badge">PyTorch</span><span class="kt-badge">Hugging Face Transformers</span><span class="kt-badge">NumPy</span><span class="kt-badge">Pandas</span><span class="kt-badge">scikit-learn</span><span class="kt-badge">Matplotlib</span>
  </div>
</div>

<div class="kt-skill-row kt-reveal">
  <span class="kt-skill-name">Research infra</span>
  <div class="kt-badges" style="margin: 0">
    <span class="kt-badge">SLURM / HPC</span><span class="kt-badge">Git</span><span class="kt-badge">LaTeX</span><span class="kt-badge">Weights &amp; Biases</span>
  </div>
</div>

<div class="kt-skill-row kt-reveal">
  <span class="kt-skill-name">Web</span>
  <div class="kt-badges" style="margin: 0">
    <span class="kt-badge">Next.js</span><span class="kt-badge">Django</span><span class="kt-badge">Supabase / PostgreSQL</span>
  </div>
</div>

</div>

<script src="{{ '/assets/js/kt.js' | relative_url }}"></script>
