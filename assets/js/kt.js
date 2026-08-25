/* ==========================================================================
   kt.js — interaction layer for kingatshering10.github.io
   All behaviour is progressive: with JS disabled every page still renders
   its full content, and nothing here is required to read the site.
   ========================================================================== */

(function () {
  "use strict";

  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------------------------------------------------- scroll reveal */

  function initReveal() {
    var targets = document.querySelectorAll(".kt-reveal");
    if (!targets.length) return;

    if (reduceMotion || !("IntersectionObserver" in window)) {
      targets.forEach(function (el) {
        el.classList.add("kt-in");
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          var el = entry.target;
          var delay = parseInt(el.getAttribute("data-kt-delay") || "0", 10);
          window.setTimeout(function () {
            el.classList.add("kt-in");
          }, delay);
          observer.unobserve(el);
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );

    targets.forEach(function (el) {
      observer.observe(el);
    });

    // Safety net: if a callback never flushes (instant jump-scroll, print, an
    // aborted animation frame) show anything that is already on screen anyway.
    window.setTimeout(function () {
      targets.forEach(function (el) {
        if (el.classList.contains("kt-in")) return;
        if (el.getBoundingClientRect().top < window.innerHeight * 1.5) {
          el.classList.add("kt-in");
        }
      });
    }, 2500);

    window.addEventListener("beforeprint", function () {
      targets.forEach(function (el) {
        el.classList.add("kt-in");
      });
    });
  }

  /* -------------------------------------------------------- animated count */

  function animateCount(el) {
    var target = parseFloat(el.getAttribute("data-kt-count"));
    if (isNaN(target)) return;

    var decimals = parseInt(el.getAttribute("data-kt-decimals") || "0", 10);
    var prefix = el.getAttribute("data-kt-prefix") || "";
    var suffix = el.getAttribute("data-kt-suffix") || "";
    var duration = reduceMotion ? 0 : 1100;
    var start = null;

    function frame(now) {
      if (start === null) start = now;
      var progress = duration === 0 ? 1 : Math.min((now - start) / duration, 1);
      // easeOutCubic
      var eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = prefix + (target * eased).toFixed(decimals) + suffix;
      if (progress < 1) window.requestAnimationFrame(frame);
    }

    window.requestAnimationFrame(frame);
  }

  function initCounters() {
    var counters = document.querySelectorAll("[data-kt-count]");
    if (!counters.length) return;

    if (!("IntersectionObserver" in window)) {
      counters.forEach(animateCount);
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          animateCount(entry.target);
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.4 }
    );

    counters.forEach(function (el) {
      observer.observe(el);
    });
  }

  /* -------------------------------------------------------------- rotator */

  function initRotator() {
    var rotators = document.querySelectorAll("[data-kt-rotate]");

    rotators.forEach(function (host) {
      var words = (host.getAttribute("data-kt-rotate") || "")
        .split("|")
        .map(function (w) {
          return w.trim();
        })
        .filter(Boolean);
      if (!words.length) return;

      var index = 0;
      var slot = document.createElement("span");
      slot.textContent = words[0];
      host.textContent = "";
      host.appendChild(slot);

      if (reduceMotion || words.length === 1) return;

      window.setInterval(function () {
        index = (index + 1) % words.length;
        var next = document.createElement("span");
        next.textContent = words[index];
        host.replaceChild(next, slot);
        slot = next;
      }, 2400);
    });
  }

  /* ----------------------------------------------------- reading progress */

  function initProgress() {
    if (!document.querySelector("[data-kt-progress]")) return;

    var bar = document.createElement("div");
    bar.className = "kt-progress";
    document.body.appendChild(bar);

    var ticking = false;

    function update() {
      var doc = document.documentElement;
      var max = doc.scrollHeight - window.innerHeight;
      var pct = max > 0 ? (window.scrollY / max) * 100 : 0;
      bar.style.width = Math.min(Math.max(pct, 0), 100) + "%";
      ticking = false;
    }

    window.addEventListener(
      "scroll",
      function () {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(update);
      },
      { passive: true }
    );

    update();
  }

  /* --------------------------------------------------- card pointer glow */

  function initCardGlow() {
    if (reduceMotion) return;
    var cards = document.querySelectorAll(".kt-card");

    cards.forEach(function (card) {
      card.addEventListener(
        "pointermove",
        function (event) {
          var rect = card.getBoundingClientRect();
          card.style.setProperty("--kt-mx", event.clientX - rect.left + "px");
          card.style.setProperty("--kt-my", event.clientY - rect.top + "px");
        },
        { passive: true }
      );
    });
  }

  /* --------------------------------------------------------- chip filters */

  /**
   * Generic filter group.
   *   <div data-kt-filter="topic"> …chips… </div>
   *   <button class="kt-chip" data-kt-value="vision">
   *   <article data-kt-group="topic" data-kt-tags="vision llm">
   */
  function initFilters() {
    var groups = document.querySelectorAll("[data-kt-filter]");

    groups.forEach(function (group) {
      var name = group.getAttribute("data-kt-filter");
      var chips = group.querySelectorAll(".kt-chip");
      var items = document.querySelectorAll('[data-kt-group="' + name + '"]');
      var empty = document.querySelector('[data-kt-empty="' + name + '"]');
      if (!chips.length || !items.length) return;

      function apply(value) {
        var shown = 0;

        items.forEach(function (item) {
          var tags = (item.getAttribute("data-kt-tags") || "").split(/\s+/);
          var match = value === "all" || tags.indexOf(value) !== -1;
          item.classList.toggle("kt-hidden", !match);
          if (match) shown++;
        });

        chips.forEach(function (chip) {
          chip.setAttribute("aria-pressed", String(chip.getAttribute("data-kt-value") === value));
        });

        if (empty) empty.classList.toggle("kt-hidden", shown !== 0);
      }

      chips.forEach(function (chip) {
        chip.addEventListener("click", function () {
          apply(chip.getAttribute("data-kt-value"));
        });
      });

      apply("all");
    });
  }

  /* ------------------------------------------- publications auto-enhance */

  var VENUE_PATTERNS = [
    { value: "accepted", label: "Accepted", test: /\baccepted\b/i },
    { value: "published", label: "Published", test: /\bpublished\b/i },
    { value: "review", label: "Under review", test: /\bunder\s+review\b/i },
    { value: "preparation", label: "In preparation", test: /\bin\s+preparation\b/i },
  ];

  function statusOf(text) {
    for (var i = 0; i < VENUE_PATTERNS.length; i++) {
      if (VENUE_PATTERNS[i].test.test(text)) return VENUE_PATTERNS[i];
    }
    return null;
  }

  function initBibliography() {
    var root = document.querySelector("[data-kt-bib]");
    if (!root) return;

    var entries = Array.prototype.slice.call(root.querySelectorAll("ol.bibliography > li"));
    if (!entries.length) return;

    var statuses = [];

    entries.forEach(function (li) {
      var text = li.textContent || "";
      var status = statusOf(text);
      li.setAttribute("data-kt-status", status ? status.value : "other");
      if (status && statuses.indexOf(status) === -1) statuses.push(status);
    });

    if (statuses.length < 2) return;

    // Build the chip row.
    var bar = document.createElement("div");
    bar.className = "kt-filters";

    var label = document.createElement("span");
    label.className = "kt-filter-label";
    label.textContent = "Filter";
    bar.appendChild(label);

    function makeChip(value, text, count) {
      var chip = document.createElement("button");
      chip.type = "button";
      chip.className = "kt-chip";
      chip.setAttribute("data-kt-value", value);
      chip.setAttribute("aria-pressed", "false");
      chip.textContent = text;

      var badge = document.createElement("span");
      badge.className = "kt-chip-count";
      badge.textContent = count;
      chip.appendChild(badge);

      return chip;
    }

    var chips = [makeChip("all", "All ", entries.length)];

    statuses.forEach(function (status) {
      var count = entries.filter(function (li) {
        return li.getAttribute("data-kt-status") === status.value;
      }).length;
      chips.push(makeChip(status.value, status.label + " ", count));
    });

    chips.forEach(function (chip) {
      bar.appendChild(chip);
    });

    root.parentNode.insertBefore(bar, root);

    function apply(value) {
      entries.forEach(function (li) {
        var match = value === "all" || li.getAttribute("data-kt-status") === value;
        li.classList.toggle("kt-hidden", !match);
      });

      // Hide year headings whose list has no visible entries left.
      root.querySelectorAll("ol.bibliography").forEach(function (list) {
        var visible = list.querySelectorAll("li:not(.kt-hidden)").length;
        list.classList.toggle("kt-hidden", visible === 0);

        var heading = list.previousElementSibling;
        while (heading && heading.tagName !== "H2") {
          heading = heading.previousElementSibling;
        }
        if (heading) heading.classList.toggle("kt-hidden", visible === 0);
      });

      chips.forEach(function (chip) {
        chip.setAttribute("aria-pressed", String(chip.getAttribute("data-kt-value") === value));
      });
    }

    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        apply(chip.getAttribute("data-kt-value"));
      });
    });

    apply("all");
  }

  /* ------------------------------------------------------------- bootstrap */

  function init() {
    initReveal();
    initCounters();
    initRotator();
    initProgress();
    initCardGlow();
    initFilters();
    initBibliography();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
