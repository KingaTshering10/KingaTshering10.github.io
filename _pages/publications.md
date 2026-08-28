---
layout: page
permalink: /publications/
title: publications
description: Peer-reviewed papers, journal articles, and preprints. Own name in bold.
nav: true
nav_order: 2
---

<link rel="stylesheet" href="{{ '/assets/css/kt.css' | relative_url }}" />
<script>document.documentElement.classList.add("kt-js");</script>

<div class="kt-stats" data-kt-stagger="80">
  <div class="kt-stat kt-tilt kt-reveal">
    <span class="kt-stat-value" data-kt-count="6">6</span>
    <span class="kt-stat-label">Papers &amp; preprints</span>
  </div>
  <div class="kt-stat kt-tilt kt-reveal">
    <span class="kt-stat-value" data-kt-count="2">2</span>
    <span class="kt-stat-label">Accepted at ICML &amp; EMNLP</span>
  </div>
  <div class="kt-stat kt-tilt kt-reveal">
    <span class="kt-stat-value" data-kt-count="3">3</span>
    <span class="kt-stat-label">First or equal first author</span>
  </div>
</div>

<!-- Bibsearch -->

{% include bib_search.liquid %}

<div class="publications" data-kt-bib>

{% bibliography %}

</div>

<script src="{{ '/assets/js/kt.js' | relative_url }}"></script>
