(function () {
  'use strict';

  /* ---------- Theme toggle ---------- */
  var root = document.documentElement;
  var themeBtn = document.getElementById('themeToggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
      var icon = themeBtn.querySelector('i');
      if (icon) icon.className = next === 'dark' ? 'ti ti-sun' : 'ti ti-moon';
    });
    try {
      var saved = localStorage.getItem('theme');
      if (saved) {
        root.setAttribute('data-theme', saved);
        var ic = themeBtn.querySelector('i');
        if (ic) ic.className = saved === 'dark' ? 'ti ti-sun' : 'ti ti-moon';
      }
    } catch (e) {}
  }

  /* ---------- Showcase carousel ---------- */
  var track = document.getElementById('track');
  var dotsWrap = document.getElementById('dots');
  var thumbsWrap = document.getElementById('thumbs');
  var prevBtn = document.getElementById('prev');
  var nextBtn = document.getElementById('next');
  if (track) {
    var shots = Array.prototype.slice.call(track.querySelectorAll('.shot'));
    var index = 0;
    var timer = null;
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // build dots + thumbnails
    shots.forEach(function (shot, i) {
      var dot = document.createElement('button');
      dot.className = 'dot-btn' + (i === 0 ? ' active' : '');
      dot.type = 'button';
      dot.setAttribute('aria-label', '第 ' + (i + 1) + ' 张');
      dot.addEventListener('click', function () { go(i, true); });
      dotsWrap.appendChild(dot);

      var thumb = document.createElement('button');
      thumb.className = 'thumb' + (i === 0 ? ' active' : '');
      thumb.type = 'button';
      var img = shot.querySelector('img');
      if (img) {
        var t = document.createElement('img');
        t.src = img.getAttribute('src');
        t.alt = img.getAttribute('alt') || '';
        thumb.appendChild(t);
      }
      thumb.addEventListener('click', function () { go(i, true); });
      thumbsWrap.appendChild(thumb);
    });

    var dots = Array.prototype.slice.call(dotsWrap.children);
    var thumbs = Array.prototype.slice.call(thumbsWrap.children);

    function go(i, manual) {
      index = (i + shots.length) % shots.length;
      shots.forEach(function (s, k) { s.classList.toggle('is-active', k === index); });
      dots.forEach(function (d, k) { d.classList.toggle('active', k === index); });
      thumbs.forEach(function (t, k) { t.classList.toggle('active', k === index); });
      if (manual) restart();
    }

    function next() { go(index + 1); }
    function prev() { go(index - 1); }

    if (nextBtn) nextBtn.addEventListener('click', function () { next(); });
    if (prevBtn) prevBtn.addEventListener('click', function () { prev(); });

    // keyboard
    document.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') next();
      else if (e.key === 'ArrowLeft') prev();
    });

    // autoplay (pause on hover / hidden tab)
    function start() {
      if (reduce) return;
      timer = setInterval(next, 5200);
    }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function restart() { stop(); start(); }

    var gallery = document.getElementById('gallery');
    if (gallery) {
      gallery.addEventListener('mouseenter', stop);
      gallery.addEventListener('mouseleave', start);
    }
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stop(); else start();
    });

    start();
  }

  /* ---------- Reveal on scroll ---------- */
  var revealEls = document.querySelectorAll('.hero, .showcase, .features, .version');
  revealEls.forEach(function (el) { el.classList.add('reveal'); });
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0.12 });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add('in'); });
  }
})();
