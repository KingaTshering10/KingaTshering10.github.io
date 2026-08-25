---
layout: about
title: about
permalink: /
nav: false
nav_order: 1
subtitle: Research Intern, University of Arizona · B.Sc. Computer Science and Engineering, North South University

profile:
  align: right
  image: prof_pic.png
  image_circular: false
  more_info: >
    <p>Dhaka, Bangladesh</p>
    <p><a href="mailto:kinstsring10@gmail.com">kinstsring10@gmail.com</a></p>
    <p><a href="/assets/pdf/Kinga_Tshering_CV.pdf">Curriculum Vitae</a></p>

selected_papers: true
social: true

announcements:
  enabled: true
  scrollable: true
  limit: 4

latest_posts:
  enabled: false
---

<link rel="stylesheet" href="{{ '/assets/css/kt.css' | relative_url }}" />
<script>document.documentElement.classList.add("kt-js");</script>

<div class="kt-hero kt-reveal" markdown="0">
  <span class="kt-eyebrow">Machine Learning Research</span>
  <p>
    I am <strong>Kinga Tshering</strong>. I work on
    <span class="kt-rotator" data-kt-rotate="evaluating language models|pruning deep networks|interpreting representations|measuring reliability"></span>
  </p>
  <p>
    Currently a research intern at the <strong>University of Arizona</strong>, College of Information Science,
    advised by <strong>Prof. Haw-Shiuan Chang</strong>. I graduated <em>summa cum laude</em> in Computer Science
    and Engineering from <strong>North South University</strong> as a recipient of <strong>His Majesty's Scholarship</strong>.
  </p>
  <div class="kt-actions">
    <a class="kt-btn kt-btn--solid" href="{{ '/publications/' | relative_url }}">Publications</a>
    <a class="kt-btn" href="{{ '/research/' | relative_url }}">Research</a>
    <a class="kt-btn" href="{{ '/cv/' | relative_url }}">CV</a>
    <a class="kt-btn" href="{{ '/assets/pdf/Kinga_Tshering_CV.pdf' | relative_url }}">Download PDF</a>
  </div>
</div>

<div class="kt-stats">
  <div class="kt-stat kt-reveal" data-kt-delay="0">
    <span class="kt-stat-value">3.90</span>
    <span class="kt-stat-label">CGPA / 4.00 · Summa Cum Laude</span>
  </div>
  <div class="kt-stat kt-reveal" data-kt-delay="70">
    <span class="kt-stat-value" data-kt-count="6">6</span>
    <span class="kt-stat-label">Papers and preprints</span>
  </div>
  <div class="kt-stat kt-reveal" data-kt-delay="140">
    <span class="kt-stat-value" data-kt-count="2">2</span>
    <span class="kt-stat-label">Accepted at ICML &amp; EMNLP 2026</span>
  </div>
  <div class="kt-stat kt-reveal" data-kt-delay="210">
    <span class="kt-stat-value" data-kt-count="2">2</span>
    <span class="kt-stat-label">Courses taught as TA</span>
  </div>
</div>

## Research interests

<p markdown="1">
**Evaluation and reliability of large language models.** **Efficient and resource-aware deep learning**,
including network pruning and model compression. **Interpretability of learned representations.**
</p>

<p markdown="1">
The thread running through all three is the distance between a benchmark number and a model you can
actually rely on. A model that scores well by answering a different question than the one it was asked
has not solved the task; a network that survives pruning tells you something about which parameters
mattered in the first place. I like problems where measuring the thing properly is itself the
contribution.
</p>

<div class="kt-grid kt-grid--2">

<div class="kt-card kt-reveal" markdown="1">

<div class="kt-card-title">Language model evaluation</div>

Separating **instruction-following compliance** from **answer correctness** in post-training evaluation
of small language models — a single accuracy number conflates a model that reasons incorrectly with one
that reasoned fine and ignored the output format. Also benchmark construction for formal-language tasks
spanning the Chomsky hierarchy, and geo-temporal grounding in vision–language models.

<div class="kt-badges">
  <span class="kt-badge kt-badge--accent">ICML 2026</span>
  <span class="kt-badge kt-badge--accent">EMNLP 2026</span>
  <span class="kt-badge">Benchmarking</span>
</div>

</div>

<div class="kt-card kt-reveal" data-kt-delay="80" markdown="1">

<div class="kt-card-title">Efficient deep learning</div>

Sparse subnetworks under the **Lottery Ticket Hypothesis**, applied to hyperspectral image
classification. Iterative magnitude pruning across 3D CNN, hybrid 3D–2D CNN, and Mamba backbones on
three benchmark scenes — asking not just how far a network compresses, but which spectral bands
survive and what that says about what the model learned.

<div class="kt-badges">
  <span class="kt-badge">Pruning</span>
  <span class="kt-badge">Model compression</span>
  <span class="kt-badge">Hyperspectral</span>
</div>

</div>

<div class="kt-card kt-reveal" markdown="1">

<div class="kt-card-title">Decoding and inference</div>

Extending **Asymptotic Probability Decoding** from extrapolation across model _scale_ to extrapolation
across _context length_, removing the method's dependence on a family of same-recipe language models at
multiple sizes — and auditing the curve-fitting objective, top-_k_ candidate selection, and numerical
conditioning that make the parametric fit unstable.

<div class="kt-badges">
  <span class="kt-badge kt-badge--accent">University of Arizona</span>
  <span class="kt-badge">Decoding</span>
</div>

</div>

<div class="kt-card kt-reveal" data-kt-delay="80" markdown="1">

<div class="kt-card-title">Applied and medical imaging</div>

**Few-shot open-set recognition** for skin lesion classification, where the realistic failure mode is
not misclassifying a known class but confidently labelling a condition the model has never seen. Plus
explainable ML for pediatric screen-time overuse prediction.

<div class="kt-badges">
  <span class="kt-badge">Medical imaging</span>
  <span class="kt-badge">Open-set</span>
  <span class="kt-badge">Explainable AI</span>
</div>

</div>

</div>

<div class="kt-hero kt-reveal" markdown="0" style="margin-top: 2rem">
  <span class="kt-eyebrow">Open to</span>
  <p>
    I am applying to <strong>graduate programs in machine learning</strong> and am open to research
    collaborations. The fastest way to reach me is
    <a href="mailto:kinstsring10@gmail.com">email</a>.
  </p>
</div>

<script src="{{ '/assets/js/kt.js' | relative_url }}"></script>
