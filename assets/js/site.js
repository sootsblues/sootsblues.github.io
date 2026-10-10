// SOOTS site behaviour: menu, scroll effects, hero slideshow, players, filters, lightbox, form.
(function () {
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var root = document.documentElement;
  var header = document.querySelector(".site-header");

  // Header height (for mega menu / mobile menu positioning)
  function setHdr() {
    if (header) root.style.setProperty("--hdr", header.getBoundingClientRect().bottom + "px");
  }

  // Scroll: progress bar, compact header, back-to-top ring
  var toTop = document.querySelector(".to-top");
  var ticking = false;
  function onScroll() {
    var h = document.documentElement.scrollHeight - innerHeight;
    var p = h > 0 ? Math.min(1, scrollY / h) : 0;
    root.style.setProperty("--p", p.toFixed(4));
    document.body.classList.toggle("scrolled", scrollY > 60);
    if (toTop) toTop.classList.toggle("show", scrollY > 700);
    setHdr();
    ticking = false;
  }
  addEventListener("scroll", function () { if (!ticking) { requestAnimationFrame(onScroll); ticking = true; } }, { passive: true });
  addEventListener("resize", setHdr);
  onScroll();
  if (toTop) toTop.addEventListener("click", function () { scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" }); });

  // Mobile menu
  var toggle = document.querySelector(".menu-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      setHdr();
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open);
      document.body.style.overflow = open ? "hidden" : "";
    });
  }
  document.querySelectorAll(".sub-toggle").forEach(function (b) {
    b.addEventListener("click", function () {
      var open = b.parentElement.classList.toggle("open");
      b.setAttribute("aria-expanded", open);
    });
  });

  // Reveal on scroll
  var reveals = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    reveals.forEach(function (el, i) {
      // stagger siblings in grids
      var idx = Array.prototype.indexOf.call(el.parentElement.children, el);
      el.style.transitionDelay = Math.min(idx, 5) * 90 + "ms";
      io.observe(el);
    });
  } else {
    reveals.forEach(function (el) { el.classList.add("in"); });
  }

  // Count-up stats
  var counters = document.querySelectorAll("[data-count]");
  if (counters.length && "IntersectionObserver" in window && !reduce) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        cio.unobserve(e.target);
        var el = e.target, end = +el.dataset.count, start = end > 1000 ? end - 60 : 0, t0 = null;
        function step(t) {
          if (!t0) t0 = t;
          var k = Math.min(1, (t - t0) / 1600), ease = 1 - Math.pow(1 - k, 3);
          el.textContent = Math.round(start + (end - start) * ease);
          if (k < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    }, { threshold: 0.6 });
    counters.forEach(function (c) { cio.observe(c); });
  }

  // Home hero crossfade with dots
  var slides = document.querySelectorAll(".hero-slides img");
  if (slides.length) {
    var si = 0, timer, dots = document.querySelector(".hero-dots"), cap = document.querySelector(".hero-cap");
    function go(n) {
      slides[si].classList.remove("on");
      if (dots) dots.children[si].classList.remove("on");
      si = (n + slides.length) % slides.length;
      slides[si].classList.add("on");
      if (dots) dots.children[si].classList.add("on");
      if (cap) cap.textContent = slides[si].dataset.cap || "";
    }
    if (dots) {
      slides.forEach(function (_, i) {
        var b = document.createElement("button");
        b.setAttribute("aria-label", "Show photo " + (i + 1));
        b.addEventListener("click", function () { go(i); restart(); });
        dots.appendChild(b);
      });
      dots.removeAttribute("aria-hidden");
    }
    function restart() { clearInterval(timer); if (!reduce) timer = setInterval(function () { go(si + 1); }, 6500); }
    slides[0].classList.add("on");
    if (dots) dots.children[0].classList.add("on");
    if (cap) cap.textContent = slides[0].dataset.cap || "";
    restart();
  }

  // 3D tilt + spotlight on cards (pointer devices only)
  if (matchMedia("(hover: hover)").matches && !reduce) {
    document.querySelectorAll(".tilt").forEach(function (el) {
      el.addEventListener("mousemove", function (e) {
        var r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        el.style.transform = "perspective(900px) rotateX(" + ((0.5 - y) * 5).toFixed(2) + "deg) rotateY(" + ((x - 0.5) * 6).toFixed(2) + "deg) translateY(-4px)";
        el.style.setProperty("--mx", x * 100 + "%");
        el.style.setProperty("--my", y * 100 + "%");
      });
      el.addEventListener("mouseleave", function () { el.style.transform = ""; });
    });
  }

  // Horizontal timeline buttons + drag to scroll
  var tl = document.querySelector(".h-timeline");
  if (tl) {
    document.querySelectorAll(".tl-btn").forEach(function (b) {
      b.addEventListener("click", function () { tl.scrollBy({ left: +b.dataset.dir * 320, behavior: "smooth" }); });
    });
    var down = false, sx = 0, sl = 0, moved = false;
    tl.addEventListener("pointerdown", function (e) { if (e.pointerType !== "mouse") return; down = true; moved = false; sx = e.clientX; sl = tl.scrollLeft; tl.style.scrollSnapType = "none"; });
    addEventListener("pointermove", function (e) { if (!down) return; var dx = e.clientX - sx; if (Math.abs(dx) > 4) moved = true; tl.scrollLeft = sl - dx; });
    addEventListener("pointerup", function () { if (down) { down = false; tl.style.scrollSnapType = ""; } });
    tl.addEventListener("click", function (e) { if (moved) { e.preventDefault(); moved = false; } }, true);
  }

  // Filter chips (archive, cake bake years)
  document.querySelectorAll(".filterable").forEach(function (box) {
    var chips = box.querySelectorAll(".chip"), items = box.querySelectorAll(".g-item"), more = box.querySelector(".show-more");
    function expand() { box.classList.remove("collapsed"); if (more) more.parentElement.remove(); more = null; }
    if (more) more.addEventListener("click", expand);
    chips.forEach(function (c) {
      c.addEventListener("click", function () {
        chips.forEach(function (x) { x.classList.toggle("on", x === c); x.setAttribute("aria-pressed", x === c); });
        var f = c.dataset.filter;
        items.forEach(function (it) { it.classList.toggle("hide", f !== "all" && it.dataset.tag !== f); });
        if (f !== "all") expand();
      });
    });
  });

  // Vinyl audio players
  var players = document.querySelectorAll(".player");
  function fmt(s) { if (!isFinite(s)) return "0:00"; var m = Math.floor(s / 60), r = Math.floor(s % 60); return m + ":" + (r < 10 ? "0" : "") + r; }
  players.forEach(function (pl) {
    var a = pl.querySelector("audio"), btn = pl.querySelector(".pl-disc"), seek = pl.querySelector(".pl-seek"), time = pl.querySelector(".pl-time");
    btn.addEventListener("click", function () {
      if (a.paused) {
        players.forEach(function (o) { if (o !== pl) o.querySelector("audio").pause(); });
        a.play();
      } else a.pause();
    });
    a.addEventListener("play", function () { pl.classList.add("playing"); btn.setAttribute("aria-label", "Pause"); });
    a.addEventListener("pause", function () { pl.classList.remove("playing"); btn.setAttribute("aria-label", "Play"); });
    a.addEventListener("timeupdate", function () {
      if (!a.duration) return;
      var v = (a.currentTime / a.duration) * 1000;
      seek.value = v; seek.style.setProperty("--v", v / 10 + "%");
      time.textContent = fmt(a.currentTime) + " / " + fmt(a.duration);
    });
    a.addEventListener("loadedmetadata", function () { time.textContent = "0:00 / " + fmt(a.duration); });
    seek.addEventListener("input", function () {
      seek.style.setProperty("--v", seek.value / 10 + "%");
      if (a.duration) a.currentTime = (seek.value / 1000) * a.duration;
      else { a.preload = "metadata"; a.load(); }
    });
  });

  // Lightbox
  var lb = document.getElementById("lightbox");
  var links = Array.prototype.slice.call(document.querySelectorAll("a.lb"));
  if (lb && links.length) {
    var lbImg = lb.querySelector("img"), lbCap = lb.querySelector("figcaption"), lbCount = lb.querySelector(".lb-count"), cur = 0, lastFocus, list = links;
    function visible() { return links.filter(function (a) { return !a.closest(".hide"); }); }
    function show(n) {
      cur = (n + list.length) % list.length;
      var a = list[cur];
      lbImg.src = a.getAttribute("href");
      lbImg.alt = a.dataset.cap || "";
      lbCap.textContent = a.dataset.cap || "";
      lbCount.textContent = (cur + 1) + " / " + list.length;
    }
    function close() { lb.hidden = true; document.body.style.overflow = ""; lbImg.src = ""; if (lastFocus) lastFocus.focus(); }
    links.forEach(function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault(); lastFocus = a; list = visible(); show(list.indexOf(a)); lb.hidden = false;
        document.body.style.overflow = "hidden"; lb.querySelector(".lb-close").focus();
      });
    });
    lb.querySelector(".lb-close").onclick = close;
    lb.querySelector(".lb-prev").onclick = function () { show(cur - 1); };
    lb.querySelector(".lb-next").onclick = function () { show(cur + 1); };
    lb.addEventListener("click", function (e) { if (e.target === lb || e.target.tagName === "FIGURE") close(); });
    document.addEventListener("keydown", function (e) {
      if (lb.hidden) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") show(cur - 1);
      if (e.key === "ArrowRight") show(cur + 1);
    });
    var tx = null;
    lb.addEventListener("touchstart", function (e) { tx = e.touches[0].clientX; }, { passive: true });
    lb.addEventListener("touchend", function (e) { if (tx === null) return; var dx = e.changedTouches[0].clientX - tx; if (Math.abs(dx) > 50) show(cur + (dx < 0 ? 1 : -1)); tx = null; });
  }

  // Contact form -> opens the visitor's mail app (no third-party service)
  var form = document.getElementById("contact-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!form.reportValidity()) return;
      var f = form.elements, name = (f.first.value + " " + f.last.value).trim();
      var body = f.message.value + "\n\n- " + name + " (" + f.email.value + ")";
      location.href = "mailto:sootsblues@gmail.com?subject=" + encodeURIComponent("Website message from " + name) + "&body=" + encodeURIComponent(body);
    });
  }
})();
