import { apiGet } from "./api.js";

async function loadSystem() {
  if (!overviewData) overviewData = await fetch("/api/dashboard/overview").then(d => d.json());
  const r = await fetch("/api/dashboard/analysis").then(d => d.json());
  document.getElementById("sys-status").innerHTML =
    '<div><strong>\u6570\u636e\u5e93</strong>: ' + (overviewData.stats ? overviewData.stats.total + ' \u6761\u8bb0\u5f55' : '-') + '</div>' +
    '<div><strong>APP \u6570\u636e</strong>: ' + (r.predicted || 0) + ' \u9884\u6d4b\u4e2d, ' + (r.completed || 0) + ' \u5df2\u5b8c\u8d5b</div>' +
    '<div><strong>\u9500\u552e\u65e5\u671f</strong>: ' + (r.al_keys || []).join(" \u2192 ") + '</div>' +
    '<div style="margin-top:8px;color:#6b7280;font-size:12px">V3.3.3-Core \u00b7 ' + new Date().toLocaleDateString("zh-CN") + '</div>';
  lucide.createIcons();
  // stat-card click to navigate
  var statCards = document.querySelectorAll("#ov-stats .stat-card");
  for (var si = 0; si < statCards.length; si++) {
    (function(card) {
      card.style.cursor = "pointer";
      card.addEventListener("click", function() {
        if (card.dataset.filter) navigateToMatches(card.dataset.filter);
      });
    })(statCards[si]);
  }
}

export { loadSystem };