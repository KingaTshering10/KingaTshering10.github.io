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

  /* ------------------------------------------------------ theme colour */

  function themeRGB() {
    var raw = getComputedStyle(document.documentElement).getPropertyValue("--global-theme-color").trim();
    var m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(raw);
    if (m) return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)];
    m = /rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/i.exec(raw);
    if (m) return [+m[1], +m[2], +m[3]];
    return [181, 9, 172];
  }

  /* --------------------------------------------- hero constellation */

  function initConstellation() {
    var hero = document.querySelector("[data-kt-constellation]");
    if (!hero || reduceMotion) return;

    var canvas = document.createElement("canvas");
    canvas.className = "kt-constellation";
    canvas.setAttribute("aria-hidden", "true");
    hero.appendChild(canvas);

    var ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var w = 0;
    var h = 0;
    var nodes = [];
    var rgb = themeRGB();
    var pointer = { x: -9999, y: -9999 };
    var running = false;
    var frame = null;

    var LINK = 128; // px within which two nodes are joined
    var PULL = 170; // px within which the cursor tugs a node

    function resize() {
      var rect = hero.getBoundingClientRect();
      w = Math.max(rect.width, 1);
      h = Math.max(rect.height, 1);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Density scales with area but stays bounded on large screens.
      var target = Math.min(Math.round((w * h) / 13000), 46);
      nodes = [];
      for (var i = 0; i < target; i++) {
        nodes.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.22,
          vy: (Math.random() - 0.5) * 0.22,
          r: 1 + Math.random() * 1.4,
        });
      }
    }

    function step() {
      ctx.clearRect(0, 0, w, h);

      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        n.x += n.vx;
        n.y += n.vy;

        if (n.x < 0 || n.x > w) n.vx *= -1;
        if (n.y < 0 || n.y > h) n.vy *= -1;
        n.x = Math.max(0, Math.min(w, n.x));
        n.y = Math.max(0, Math.min(h, n.y));

        // Cursor tug — eased, never enough to fling a node across the box.
        var dxp = pointer.x - n.x;
        var dyp = pointer.y - n.y;
        var dp = Math.sqrt(dxp * dxp + dyp * dyp);
        if (dp < PULL && dp > 0.5) {
          var force = (1 - dp / PULL) * 0.35;
          n.x += (dxp / dp) * force;
          n.y += (dyp / dp) * force;
        }

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + ",0.55)";
        ctx.fill();
      }

      for (var a = 0; a < nodes.length; a++) {
        for (var b = a + 1; b < nodes.length; b++) {
          var dx = nodes[a].x - nodes[b].x;
          var dy = nodes[a].y - nodes[b].y;
          var d = Math.sqrt(dx * dx + dy * dy);
          if (d > LINK) continue;
          ctx.beginPath();
          ctx.moveTo(nodes[a].x, nodes[a].y);
          ctx.lineTo(nodes[b].x, nodes[b].y);
          ctx.strokeStyle = "rgba(" + rgb[0] + "," + rgb[1] + "," + rgb[2] + "," + (0.3 * (1 - d / LINK)).toFixed(3) + ")";
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }

      frame = window.requestAnimationFrame(step);
    }

    function start() {
      if (running) return;
      running = true;
      frame = window.requestAnimationFrame(step);
    }

    function stop() {
      running = false;
      if (frame) window.cancelAnimationFrame(frame);
      frame = null;
    }

    hero.addEventListener(
      "pointermove",
      function (e) {
        var rect = hero.getBoundingClientRect();
        pointer.x = e.clientX - rect.left;
        pointer.y = e.clientY - rect.top;
      },
      { passive: true }
    );

    hero.addEventListener("pointerleave", function () {
      pointer.x = -9999;
      pointer.y = -9999;
    });

    // Only burn frames while the hero is actually on screen.
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        entries[0].isIntersecting ? start() : stop();
      }).observe(hero);
    } else {
      start();
    }

    document.addEventListener("visibilitychange", function () {
      document.hidden ? stop() : start();
    });

    var resizeTimer = null;
    window.addEventListener("resize", function () {
      window.clearTimeout(resizeTimer);
      resizeTimer = window.setTimeout(resize, 180);
    });

    // al-folio swaps the palette on theme change; re-read it when that happens.
    new MutationObserver(function () {
      rgb = themeRGB();
    }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "class"] });

    resize();
    window.setTimeout(function () {
      canvas.classList.add("kt-in");
    }, 120);
  }

  /* ------------------------------------------------- hero entrance */

  function initEnter() {
    var items = document.querySelectorAll(".kt-enter");
    items.forEach(function (el, i) {
      var delay = reduceMotion ? 0 : 90 * i;
      window.setTimeout(function () {
        el.classList.add("kt-in");
      }, delay);
    });
  }

  /* --------------------------------------------------------- tilt */

  function initTilt() {
    if (reduceMotion || !window.matchMedia("(hover: hover)").matches) return;

    document.querySelectorAll(".kt-tilt").forEach(function (el) {
      var raf = null;

      el.addEventListener(
        "pointermove",
        function (e) {
          if (raf) return;
          raf = window.requestAnimationFrame(function () {
            raf = null;
            var r = el.getBoundingClientRect();
            var px = (e.clientX - r.left) / r.width - 0.5;
            var py = (e.clientY - r.top) / r.height - 0.5;
            el.style.transform =
              "perspective(700px) rotateX(" + (-py * 7).toFixed(2) + "deg) rotateY(" + (px * 7).toFixed(2) + "deg) translateY(-4px)";
          });
        },
        { passive: true }
      );

      el.addEventListener("pointerleave", function () {
        el.style.transform = "";
      });
    });
  }

  /* ---------------------------------------------- magnetic buttons */

  function initMagnetic() {
    if (reduceMotion || !window.matchMedia("(hover: hover)").matches) return;

    document.querySelectorAll(".kt-btn").forEach(function (btn) {
      btn.addEventListener(
        "pointermove",
        function (e) {
          var r = btn.getBoundingClientRect();
          var dx = e.clientX - (r.left + r.width / 2);
          var dy = e.clientY - (r.top + r.height / 2);
          btn.style.transform = "translate(" + (dx * 0.16).toFixed(2) + "px," + (dy * 0.22 - 2).toFixed(2) + "px)";
        },
        { passive: true }
      );

      btn.addEventListener("pointerleave", function () {
        btn.style.transform = "";
      });
    });
  }

  /* ------------------------------------------------------ stagger */

  function initStagger() {
    document.querySelectorAll("[data-kt-stagger]").forEach(function (group) {
      var step = parseInt(group.getAttribute("data-kt-stagger") || "70", 10);
      var i = 0;
      group.querySelectorAll(".kt-reveal").forEach(function (el) {
        if (!el.hasAttribute("data-kt-delay")) el.setAttribute("data-kt-delay", String(i * step));
        i++;
      });
    });
  }

  /* ------------------------------------------ scroll-drawn timeline */

  function initTimelines() {
    var lines = document.querySelectorAll(".kt-timeline");
    if (!lines.length || reduceMotion) return;

    var ticking = false;

    function update() {
      ticking = false;
      lines.forEach(function (line) {
        var r = line.getBoundingClientRect();
        var anchor = window.innerHeight * 0.72;
        var progress = (anchor - r.top) / Math.max(r.height, 1);
        line.style.setProperty("--kt-tl-progress", Math.max(0, Math.min(1, progress)).toFixed(3));

        line.querySelectorAll(".kt-tl-item").forEach(function (item) {
          var ir = item.getBoundingClientRect();
          item.classList.toggle("kt-tl-lit", ir.top < anchor);
        });
      });
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

    lines.forEach(function (l) {
      l.style.setProperty("--kt-tl-progress", "0");
    });
    update();
  }

  /* --------------------------------------------- heading underlines */

  function initHeadings() {
    var scope = document.querySelector(".post-content, .page-content, article, main") || document.body;
    var headings = scope.querySelectorAll("h2");
    if (!headings.length) return;

    headings.forEach(function (h) {
      if (h.querySelector(".kt-uline") || !h.textContent.trim()) return;
      var span = document.createElement("span");
      span.className = "kt-uline kt-reveal";
      while (h.firstChild) span.appendChild(h.firstChild);
      h.appendChild(span);
    });
  }

  /* --------------------------------------------- smooth anchor jump */

  function initAnchors() {
    if (reduceMotion) return;
    document.querySelectorAll('a[href^="#"]').forEach(function (a) {
      a.addEventListener("click", function (e) {
        var id = a.getAttribute("href");
        if (!id || id === "#") return;
        var target = document.querySelector(id);
        if (!target) return;
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  /* ------------------------------------------------------------- bootstrap */

  function init() {
    // Headings and stagger delays must be set up before the reveal observer
    // starts watching, since both add or annotate .kt-reveal elements.
    initHeadings();
    initStagger();
    initReveal();
    initCounters();
    initRotator();
    initProgress();
    initCardGlow();
    initFilters();
    initBibliography();
    initConstellation();
    initEnter();
    initTilt();
    initMagnetic();
    initTimelines();
    initAnchors();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
