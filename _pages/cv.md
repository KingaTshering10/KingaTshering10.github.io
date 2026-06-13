---
layout: page
title: CV
permalink: /cv/
nav: true
nav_order: 6
---

<style>
  .cv-hero {
    margin-bottom: 2rem;
    padding: 1.4rem 1.5rem;
    border-left: 4px solid var(--global-theme-color);
    background: var(--global-code-bg-color);
    border-radius: 0.9rem;
  }

  .cv-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.7rem;
    margin-top: 1rem;
  }

  .cv-button {
    display: inline-block;
    padding: 0.55rem 0.9rem;
    border-radius: 999px;
    font-weight: 600;
    text-decoration: none;
    border: 1px solid var(--global-theme-color);
    color: var(--global-theme-color);
    transition: transform 0.2s ease, background 0.2s ease, color 0.2s ease;
  }

  .cv-button:hover {
    transform: translateY(-2px);
    background: var(--global-theme-color);
    color: var(--global-bg-color);
    text-decoration: none;
  }

  .cv-grid {
    display: grid;
    gap: 1.4rem;
    margin-top: 1.5rem;
  }

  .cv-card {
    padding: 1.25rem 1.45rem;
    border: 1px solid var(--global-divider-color);
    border-radius: 1rem;
    background: var(--global-bg-color);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.06);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .cv-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12);
  }

  .cv-card-title {
    margin-bottom: 0.8rem;
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--global-theme-color);
  }

  .cv-meta {
    color: var(--global-text-color-light);
    font-size: 0.95rem;
    margin-bottom: 0.8rem;
  }

  .cv-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin: 0.7rem 0 1rem;
  }

  .cv-badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    background: var(--global-code-bg-color);
    border: 1px solid var(--global-divider-color);
  }

  .cv-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
    gap: 0.8rem;
    margin: 1rem 0;
  }

  .cv-stat {
    padding: 0.85rem;
    border-radius: 0.8rem;
    background: var(--global-code-bg-color);
    border: 1px solid var(--global-divider-color);
    text-align: center;
  }

  .cv-stat-value {
    display: block;
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--global-theme-color);
  }

  .cv-stat-label {
    display: block;
    font-size: 0.82rem;
    color: var(--global-text-color-light);
  }

  details.cv-details {
    margin-top: 0.8rem;
  }

  details.cv-details summary {
    cursor: pointer;
    font-weight: 600;
    color: var(--global-theme-color);
  }

  details.cv-details summary:hover {
    text-decoration: underline;
  }

  .cv-project {
    margin-bottom: 1rem;
    padding: 0.9rem 1rem;
    border-radius: 0.8rem;
    background: var(--global-code-bg-color);
    border: 1px solid var(--global-divider-color);
  }

  .cv-project strong {
    color: var(--global-theme-color);
  }
</style>

<div class="cv-hero" markdown="1">

I am **Kinga Tshering**, a Computer Science and Engineering graduate from
**North South University**, Dhaka, Bangladesh. My academic and research work
focuses on machine learning, computer vision, natural language processing,
medical imaging, hyperspectral image classification, explainable AI, and
trusworthy applied artificial intelligence.

<div class="cv-actions">
  <a class="cv-button" href="/assets/pdf/Kinga_Tshering_CV.pdf">Download Full CV</a>
  <a class="cv-button" href="/publications/">View Publications</a>
  <a class="cv-button" href="/experience/">View Experience</a>
</div>

</div>

<div class="cv-stats">
  <div class="cv-stat">
    <span class="cv-stat-value">3.90 / 4.00</span>
    <span class="cv-stat-label">Undergraduate CGPA</span>
  </div>
  <div class="cv-stat">
    <span class="cv-stat-value">Summa Cum Laude</span>
    <span class="cv-stat-label">Academic Standing</span>
  </div>
  <div class="cv-stat">
    <span class="cv-stat-value">ICML 2026</span>
    <span class="cv-stat-label">Accepted Research</span>
  </div>
  <div class="cv-stat">
    <span class="cv-stat-value">2024–2025</span>
    <span class="cv-stat-label">Teaching Assistant</span>
  </div>
</div>

<div class="cv-grid">

<div class="cv-card" markdown="1">

<div class="cv-card-title">Education</div>

**B.Sc. in Computer Science and Engineering** **North South University**,
Dhaka, Bangladesh *Class of 2026*

<div class="cv-badges">
  <span class="cv-badge">CGPA: 3.90 / 4.00</span>
  <span class="cv-badge">Summa Cum Laude</span>
  <span class="cv-badge">His Majesty's Scholarship</span>
</div>

My undergraduate training focused on computer science, machine learning,
software systems, database systems, and research-oriented artificial
intelligence.

</div>

<div class="cv-card" markdown="1">

<div class="cv-card-title">Research Interests</div>

My research interests lie at the intersection of machine learning and
real-world applications.

<div class="cv-badges">
  <span class="cv-badge">Machine Learning</span>
  <span class="cv-badge">Deep Learning</span>
  <span class="cv-badge">Computer Vision</span>
  <span class="cv-badge">Vision-Language Models</span>
  <span class="cv-badge">NLP</span>
  <span class="cv-badge">Medical Imaging</span>
  <span class="cv-badge">Hyperspectral Imaging</span>
  <span class="cv-badge">Explainable AI</span>
  <span class="cv-badge">Trustworthy AI</span>
</div>

<details class="cv-details" open>
<summary>Research direction</summary>

I am particularly interested in building AI systems that are accurate,
interpretable, robust, and useful in practical domains such as healthcare,
remote sensing, reasoning, and multimodal understanding.

</details>

</div>

<div class="cv-card" markdown="1">

<div class="cv-card-title">Publications and Research</div>

I have contributed to accepted, published, and under-review research associated
with venues and journals such as **ICML 2026**, **TMLR**, **Neurocomputing**,
**EMNLP**, and **Zorig Melong Journal**.

<div class="cv-badges">
  <span class="cv-badge">ICML 2026</span>
  <span class="cv-badge">TMLR</span>
  <span class="cv-badge">Neurocomputing</span>
  <span class="cv-badge">EMNLP</span>
  <span class="cv-badge">Zorig Melong Journal</span>
</div>

<details class="cv-details" open>
<summary>Research focus areas</summary>

- Vision-language model evaluation and benchmarking.
- Sparse subnetworks for hyperspectral image classification.
- Few-shot open-set skin lesion recognition.
- LLM-based computational reasoning.
- Explainable machine learning for pediatric screen-time overuse prediction.

</details>

</div>

<div class="cv-card" markdown="1">

<div class="cv-card-title">Teaching Experience</div>

**Teaching Assistant** **North South University**, Dhaka, Bangladesh *2024–2025*

<div class="cv-badges">
  <span class="cv-badge">CSE215: Java</span>
  <span class="cv-badge">CSE332: Computer Architecture</span>
  <span class="cv-badge">Student Mentoring</span>
  <span class="cv-badge">Grading Support</span>
</div>

I supported undergraduate Computer Science and Engineering courses by assisting
students with course concepts, programming, problem-solving, assignments, and
exam preparation.

<details class="cv-details">
<summary>Responsibilities</summary>

- Facilitated TA hours and academic support sessions.
- Assisted students with Java programming and object-oriented programming.
- Supported computer architecture and core CSE concept clarification.
- Helped with assignment grading and examination-related activities.
- Coordinated with course instructors to support student learning.

</details>

</div>

<div class="cv-card" markdown="1">

<div class="cv-card-title">Leadership and Service</div>

**Bhutanese Student Coordinator** **North South University**, Dhaka, Bangladesh
*2022–Present*

**Volunteer President** **CSO Nazhoen Lamtoen**, Bhutan *2020–2021*

<details class="cv-details" open>
<summary>Selected initiatives</summary>

- Supported Bhutanese students through academic, administrative, and community
  coordination.
- Organized a community cleaning campaign in Phuentsholing on World Mental
  Health Day.
- Advocated for the HeForShe campaign in educational institutions in Bhutan.
- Supported children in conflict with the law alongside the Regional Case
  Management Officer of Nazhoen Lamtoen.

</details>

</div>

<div class="cv-card" markdown="1">

<div class="cv-card-title">Selected Projects</div>

<div class="cv-project" markdown="1">

**IntelliExpense** An ML-powered financial budgeting web application designed to
support smarter personal finance management and intelligent expense tracking.

</div>

<div class="cv-project" markdown="1">

**FindMySpot** A smart parking reservation system that helps users discover and
reserve parking spaces efficiently, reducing search time and parking frustration.

</div>

</div>

<div class="cv-card" markdown="1">

<div class="cv-card-title">Technical Skills</div>

<div class="cv-badges">
  <span class="cv-badge">Python</span>
  <span class="cv-badge">Java</span>
  <span class="cv-badge">C</span>
  <span class="cv-badge">C++</span>
  <span class="cv-badge">SQL</span>
  <span class="cv-badge">Deep Learning</span>
  <span class="cv-badge">Computer Vision</span>
  <span class="cv-badge">NLP</span>
  <span class="cv-badge">Explainable AI</span>
  <span class="cv-badge">LaTeX</span>
  <span class="cv-badge">Overleaf</span>
  <span class="cv-badge">Git</span>
  <span class="cv-badge">GitHub</span>
  <span class="cv-badge">HTML</span>
  <span class="cv-badge">CSS</span>
  <span class="cv-badge">JavaScript</span>
</div>

</div>

</div>
