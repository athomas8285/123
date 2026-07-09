import { fmt, fmt1, dirClass, rateClass, dirBadgeHTML, parseWeekday, rowClass, fmtSp, enc } from "./utils.js";
import { apiGet } from "./api.js";

function filterMatches() {
  const q = document.getElementById("match-search").value.toLowerCase();
  const hasFilter = q || currentMatchFilter !== "all";
  let filtered = allMatchesFlat;
  if (q) filtered = filtered.filter(m => (m.match_id && m.match_id.toLowerCase().includes(q)) || (m.home && m.home.includes(q)) || (m.away && m.away.includes(q)));
  if (currentMatchFilter === "done") filtered = filtered.filter(m => m.actual_score);
  else if (currentMatchFilter === "pred") filtered = filtered.filter(m => m.direction && !m.actual_score);
  else if (currentMatchFilter === "wait") filtered = filtered.filter(m => !m.direction);
  else if (currentMatchFilter === "hit") filtered = filtered.filter(m => m.hit === 1 || m.hit === true);
  else if (currentMatchFilter === "miss") filtered = filtered.filter(m => m.hit === 0 || m.hit === false);
  else if (currentMatchFilter === "today") {
    if (overviewData && overviewData.today_matches) {
      var todayIds = overviewData.today_matches.map(function(m){ return m.match_id; });
      filtered = filtered.filter(function(m){ return todayIds.indexOf(m.match_id) >= 0; });
    }
  }
  
  if (hasFilter) {
    const groups = {};
    filtered.forEach(m => {
      const mt = m.match_time || "";
      const key = mt.length >= 10 ? mt.substring(0, 10) : "unknown";
      if (!groups[key]) groups[key] = [];
      groups[key].push(m);
    });
    const g = [];
    Object.keys(groups).sort().reverse().forEach(k => {
      g.push({ sale_date: k === "unknown" ? "未知日期" : k, matches: groups[k] });
    });
    renderMatchGroups(g);
  } else {
    const g = [];
    for (const grp of allMatchGroups) {
      g.push({ sale_date: grp.sale_date === "unknown" ? "未知日期" : grp.sale_date, matches: grp.matches });
    }
    renderMatchGroups(g);
  }
}

function renderMatchGroups(groups) {
  const container = document.getElementById("match-groups");
  let html = "";
  groups.forEach((g, gi) => {
    html += '<div class="match-group"><div class="group-header" data-gi="' + gi + '"><i data-lucide="chevron-right" class="arrow" width="16" height="16"></i>' + g.sale_date + '<span class="count">' + g.matches.length + ' \u573a</span></div><div class="group-body"><table><thead><tr><th>\u7f16\u53f7</th><th>\u4e3b\u961f</th><th>\u5ba2\u961f</th><th>\u65f6\u95f4</th><th>\u4e8b\u4ef6</th><th>\u65b9\u5411</th><th>\u8d5b\u679c</th></tr></thead><tbody>';
    g.matches.forEach(m => {
      const timeStr = m.match_time ? m.match_time.substring(5, 16) : "\u2014";
      html += '<tr class="' + rowClass(m) + '"><td>' + fmt(m.match_id) + '</td><td>' + fmt(m.home) + '</td><td>' + fmt(m.away) + '</td><td>' + timeStr + '</td><td>' + fmt(m.event) + '</td><td>' + dirBadgeHTML("", m.direction) + '</td><td>' + fmt(m.actual_score, "\u2014") + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
  });
  container.innerHTML = html || '<div class="empty">\u65e0\u5339\u914d\u6570\u636e</div>';
  container.querySelectorAll(".group-header").forEach(hdr => {
    hdr.addEventListener("click", () => {
      const body = hdr.nextElementSibling;
      const isOpen = body.classList.contains("open");
      container.querySelectorAll(".group-body.open").forEach(b => b.classList.remove("open"));
      container.querySelectorAll(".group-header.open").forEach(b => b.classList.remove("open"));
      if (!isOpen) { body.classList.add("open"); hdr.classList.add("open"); }
    });
  });
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

async function loadMatches() {
  const r = await fetch("/api/dashboard/matches_grouped").then(d => d.json());
  window.allMatchesFlat = [];
  window.allMatchGroups = [];
  for (const g of (r.groups || [])) {
    const filtered = g.matches.filter(function(m) {
      return (m.direction && m.direction !== "");
    });
    if (filtered.length > 0) {
      allMatchGroups.push({ sale_date: g.sale_date, matches: filtered });
      for (const m of filtered) { allMatchesFlat.push(m); }
    }
  }
  filterMatches();
}

function navigateToMatches(filter) {
  currentMatchFilter = filter || "all";
  var pills = document.querySelectorAll("#match-toolbar .pill");
  for (var i = 0; i < pills.length; i++) pills[i].classList.remove("on");
  var pill = document.querySelector('#match-toolbar .pill[data-filter="' + currentMatchFilter + '"]');
  if (pill) pill.classList.add("on");
  var nav = document.querySelector('.nav-item[data-panel="matches"]');
  if (nav) nav.click();
}

export { loadMatches, navigateToMatches, filterMatches };