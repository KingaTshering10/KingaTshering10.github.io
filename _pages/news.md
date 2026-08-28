---
layout: page
title: news
permalink: /news/
nav: true
nav_order: 7
description: Paper acceptances, research positions, and other updates.
---

<link rel="stylesheet" href="{{ '/assets/css/kt.css' | relative_url }}" />
<script>
  document.documentElement.classList.add("kt-js");
</script>

<div class="kt-hero kt-enter" markdown="0" data-kt-constellation>
  <span class="kt-eyebrow">Updates</span>
  <p>
    Paper acceptances, research positions, and other milestones — newest first.
  </p>
  <div class="kt-actions kt-enter">
    <a class="kt-btn kt-btn--solid" href="{{ '/publications/' | relative_url }}">Publications</a>
    <a class="kt-btn" href="{{ '/research/' | relative_url }}">Research</a>
  </div>
</div>

{% include news.liquid %}

<script src="{{ '/assets/js/kt.js' | relative_url }}"></script>
