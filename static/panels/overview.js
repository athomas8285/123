import { fmt, fmt1 } from "./utils.js";
import { apiGet } from "./api.js";

async function overview() {
  const r = await fetch("/api/dashboard/overview").then(d => d.json());
  var overviewData = r;
  const s = r.stats;
  document.getElementById("ov-stats").innerHTML =
    '<div class="stat-card" data-filter="all"><div class="num">' + s.total + '</div><div class="label">总比赛</div></div>' +
    '<div class="stat-card" data-filter="done"><div class="num green">' + s.scored + '</div><div class="label">已有赛果</div></div>' +
    '<div class="stat-card" data-filter="pred"><div class="num yellow">' + s.predicted + '</div><div class="label">已预测</div></div>' +
    '<div class="stat-card" data-filter="hit"><div class="num green">' + s.hit + '</div><div class="label">命中</div></div>' +
    '<div class="stat-card" data-filter="miss"><div class="num red">' + s.miss + '</div><div class="label">未命中</div></div>' +
    '<div class="stat-card" data-filter="all"><div class="num">' + s.hitrate + '%</div><div class="label">命中率</div></div>' +
    '<div class="stat-card" data-filter="today"><div class="num yellow">' + (r.today_matches ? r.today_matches.length : 0) + '</div><div class="label">今日比赛</div></div>';
  document.getElementById("ov-health").innerHTML =
    '<span class="ok">竞彩网 API ✓</span>' +
    '<span class="' + (r.health.sp_missing > 0 ? "warn" : "ok") + '">赔率缺失 ' + r.health.sp_missing + '/' + r.health.total + '</span>' +
    '<span class="warn">SofaScore ○</span>' +
    '<span>伤停信息 —</span>';

  // Render flow steps
  var steps = r.flow_steps || [];
  var navMap = {fetch:"console", data:"console", predict:"console", results:"console", plan:"plans"};
  var flowHtml = steps.map(function(st) {
    var iconClass = st.done ? "done" : (st.action ? "pending" : "idle");
    var badgeClass = st.action ? "action" : "done";
    var badgeText = st.action ? "去操作" : (st.done ? "已完成" : "无需操作");
    var iconChar = st.done ? "✓" : (st.action ? "○" : "—");
    return '<div class="flow-step" data-nav="' + (navMap[st.id] || "console") + '">' +
      '<div class="fs-icon ' + iconClass + '">' + iconChar + '</div>' +
      '<div class="fs-body">' +
      '<div class="fs-title">' + st.label + '</div>' +
      '<div class="fs-desc">' + st.desc + '</div>' +
      '</div>' +
      '<span class="fs-badge ' + badgeClass + '">' + badgeText + '</span>' +
      '</div>';
  }).join("");
  document.getElementById("ov-flow").innerHTML = flowHtml;

  // Click handling: navigate to panel
  document.querySelectorAll("#ov-flow .flow-step").forEach(function(card) {
    card.addEventListener("click", function() {
      var nav = document.querySelector('.nav-item[data-panel="' + card.dataset.nav + '"]');
      if (nav) nav.click();
    });
  });

  document.getElementById("sidebar-update").textContent = "最后更新: " + new Date().toLocaleTimeString("zh-CN");
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

export { overview };