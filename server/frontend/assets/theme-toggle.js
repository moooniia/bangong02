(function () {
  var ICON_SUN = '<i class="ti ti-sun"></i>';
  var ICON_MOON = '<i class="ti ti-moon"></i>';

  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function applyIcon(btn) {
    btn.innerHTML = currentTheme() === 'dark' ? ICON_SUN : ICON_MOON;
    btn.title = currentTheme() === 'dark' ? '切换到浅色模式' : '切换到深色模式';
  }

  function injectToggle() {
    var nav = document.querySelector('nav');
    if (!nav || document.querySelector('.theme-toggle')) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'theme-toggle';
    applyIcon(btn);
    btn.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
      applyIcon(btn);
    });
    var navLinks = nav.querySelector('.nav-links');
    if (navLinks && navLinks.parentNode === nav) {
      nav.insertBefore(btn, navLinks.nextSibling);
    } else {
      nav.appendChild(btn);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectToggle);
  } else {
    injectToggle();
  }
})();
