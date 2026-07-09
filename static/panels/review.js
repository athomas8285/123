import { fmt, fmt1, enc } from "./utils.js";
import { apiGet } from "./api.js";

async function loadReview() {
  const r = await fetch("/api/dashboard/review").then(d => d.json());
  document.getElementById("rv-total").textContent = (r.cumulative && r.cumulative.total) || 0;
  document.getElementById("rv-hits").textContent = (r.cumulative && r.cumulative.hits) || 0;
  document.getElementById("rv-hitrate").textContent = ((r.cumulative && r.cumulative.rate) || 0) + "%";
  document.getElementById("rv-ratings").innerHTML = '<div class="rv-num">' + ((r.cumulative && r.cumulative.hits) || 0) + '/' + ((r.cumulative && r.cumulative.total) || 0) + '</div><div class="rv-label">\u547d\u4e2d/\u603b\u8ba1</div>';
  let html = "";
  for (const item of (r.completed || [])) {
    html += '<div class="rv-item ' + (item.hit ? "hit" : "miss") + '"><span class="rv-teams">' + item.match_id + ' ' + fmt(item.home) + ' vs ' + fmt(item.away) + '</span><span>' + fmt(item.actual_score) + '</span>' + dirBadgeHTML("", item.direction) + '<span>' + (item.hit ? "\u2705" : "\u274c") + '</span></div>';
  }
  document.getElementById("rv-list").innerHTML = html || '<div class="empty">\u6682\u65e0\u590d\u76d8\u6570\u636e</div>';
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

export { loadReview };