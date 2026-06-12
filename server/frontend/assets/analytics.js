(function () {
  var id = "__UMAMI_WEBSITE_ID__";
  if (!id || id.indexOf("__UMAMI") === 0) return;
  var s = document.createElement("script");
  s.defer = true;
  s.src = "/script.js";
  s.setAttribute("data-website-id", id);
  document.head.appendChild(s);
})();