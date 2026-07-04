// ==================== GLOBALS ====================
const WEEKDAYS = ["周一","周二","周三","周四","周五","周六","周日"];
let overviewData = null;
let allMatchesFlat = [];
let allMatchGroups = [];
let currentMatchFilter = "all";
const panelLoaded = {};
// ==================== UTILS ====================
function fmt(v, d) { return (v === null || v === undefined || v === "") ? (d || "-") : v; }
function fmt1(v, d) { if (v === null || v === undefined || v === "") return d || "-"; var n = Number(v); return isNaN(n) ? (d || "-") : n.toFixed(1); }
function rowClass(m) {
  if (m.actual_score) return "row-done";
  if (m.direction) return "row-pred";
  return "row-wait";
}
function dirClass(direction) {
  if (direction === "\u8d1f" || direction === "\u8ba9\u8d1f") return "lose";
  return "dir";
}
function rateClass(rating) {
  if (rating === "C") return "C";
  return "B";
}
function dirBadgeHTML(rating, direction) {
  return '<span class="dir-badge ' + (rating || "") + '">' + fmt(direction, "\u2014") + '</span>';
}
function parseWeekday(mid) {
  for (const wd of WEEKDAYS) { if (mid && mid.startsWith(wd)) return wd; }
  return null;
}
// ==================== SIDEBAR NAV ====================
document.querySelectorAll(".nav-item").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    document.getElementById("panel-" + btn.dataset.panel).classList.add("active");
    loadPanel(btn.dataset.panel);
  });
});
// Auto-load default active panel on page load
(function(){
  var active = document.querySelector(".nav-item.active");
  if (active) active.click();
})();
document.getElementById("collapse-btn").addEventListener("click", () => {
  document.getElementById("sidebar").classList.toggle("collapsed");
  const icon = document.querySelector("#collapse-btn i");
  icon.setAttribute("data-lucide", document.getElementById("sidebar").classList.contains("collapsed") ? "panel-left-open" : "panel-left-close");
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
});
function updateSidebarTime() {
  document.getElementById("sidebar-time").textContent = new Date().toLocaleString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
setInterval(updateSidebarTime, 1000);
updateSidebarTime();
// ==================== PANEL LOADERS ====================
async function loadPanel(name) {
  if (panelLoaded[name]) return;
  panelLoaded[name] = true;
  const loaders = { overview, console: loadConsole, matches: loadMatches, prediction: loadPrediction, fundamental: loadFundamental, plans: loadPlans, featured: function(){}, review: loadReview, system: loadSystem };
  if (loaders[name]) {
    try { await loaders[name](); }
    catch(e) { console.error("Panel '" + name + "' error:", e); }
  }
}
// ==================== CHART ====================
function drawTrendChart(canvasId, trend) {
  const canvas = document.getElementById(canvasId);
  if (!canvas || !trend || !trend.length) return;
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.parentElement.clientWidth - 32;
  const h = 140;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = w + "px";
  canvas.style.height = h + "px";
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  const pad = { top: 16, right: 24, bottom: 28, left: 40 };
  const pw = w - pad.left - pad.right;
  const ph = h - pad.top - pad.bottom;
  const stepX = trend.length > 1 ? pw / (trend.length - 1) : pw;
  ctx.strokeStyle = "#e5e7eb";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, pad.top + ph);
  ctx.lineTo(pad.left + pw, pad.top + ph);
  ctx.stroke();
  ctx.fillStyle = "#9ca3af";
  ctx.font = "10px -apple-system,BlinkMacSystemFont,sans-serif";
  ctx.textAlign = "right";
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + ph * (1 - i / 4);
    ctx.fillText(i * 25 + "%", pad.left - 6, y + 3);
  }
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 2;
  ctx.beginPath();
  trend.forEach((t, i) => {
    const x = pad.left + i * stepX;
    const y = pad.top + ph * (1 - t.rate / 100);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.fillStyle = "#2563eb";
  ctx.textAlign = "center";
  ctx.font = "10px -apple-system,BlinkMacSystemFont,sans-serif";
  trend.forEach((t, i) => {
    const x = pad.left + i * stepX;
    const y = pad.top + ph * (1 - t.rate / 100);
    ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#9ca3af";
    ctx.fillText(t.label, x, pad.top + ph + 16);
    ctx.fillStyle = "#2563eb";
  });
}
// ==================== NAVIGATE TO MATCHES WITH FILTER ====================
function navigateToMatches(filter) {
  currentMatchFilter = filter || "all";
  var pills = document.querySelectorAll("#match-toolbar .pill");
  for (var i = 0; i < pills.length; i++) pills[i].classList.remove("on");
  var pill = document.querySelector('#match-toolbar .pill[data-filter="' + currentMatchFilter + '"]');
  if (pill) pill.classList.add("on");
  var nav = document.querySelector('.nav-item[data-panel="matches"]');
  if (nav) nav.click();
}

// ==================== 1. OVERVIEW ====================
async function overview() {
  const r = await fetch("/api/dashboard/overview").then(d => d.json());
  overviewData = r;
  const s = r.stats;
  document.getElementById("ov-stats").innerHTML =
    '<div class="stat-card" data-filter="all"><div class="num">' + s.total + '</div><div class="label">\u603b\u6bd4\u8d5b</div></div>' +
    '<div class="stat-card" data-filter="done"><div class="num green">' + s.scored + '</div><div class="label">\u5df2\u6709\u8d5b\u679c</div></div>' +
    '<div class="stat-card" data-filter="pred"><div class="num yellow">' + s.predicted + '</div><div class="label">\u5df2\u9884\u6d4b</div></div>' +
    '<div class="stat-card" data-filter="hit"><div class="num green">' + s.hit + '</div><div class="label">\u547d\u4e2d</div></div>' +
    '<div class="stat-card" data-filter="miss"><div class="num red">' + s.miss + '</div><div class="label">\u672a\u547d\u4e2d</div></div>' +
    '<div class="stat-card" data-filter="all"><div class="num">' + s.hitrate + '%</div><div class="label">\u547d\u4e2d\u7387</div></div>' +
    '<div class="stat-card" data-filter="today"><div class="num yellow">' + (r.today_matches ? r.today_matches.length : 0) + '</div><div class="label">\u4eca\u65e5\u6bd4\u8d5b</div></div>';
  document.getElementById("ov-health").innerHTML =
    '<span class="ok">\u7ade\u5f69\u7f51 API \u2713</span>' +
    '<span class="' + (r.health.sp_missing > 0 ? "warn" : "ok") + '">\u8d54\u7387\u7f3a\u5931 ' + r.health.sp_missing + '/' + r.health.total + '</span>' +
    '<span class="warn">SofaScore \u25cb</span>' +
    '<span>\u4f24\u505c\u4fe1\u606f \u2014</span>';
  drawTrendChart("ov-chart", r.hit_trend || []);
  document.getElementById("sidebar-update").textContent = "\u6700\u540e\u66f4\u65b0: " + new Date().toLocaleTimeString("zh-CN");
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
// ==================== CONSOLE ====================
async function loadConsole() {
  try {
    overviewData = await fetch("/api/dashboard/overview").then(d => d.json());
  } catch(e) {
    console.error("loadConsole: overview fetch failed", e);
    document.getElementById("console-tasks").innerHTML = '<div class="cp-empty">加载失败，请刷新页面重试</div>';
    return;
  }
  const r = overviewData;
  const s = r.stats;
  document.getElementById("console-tasks").innerHTML =
    '<div class="task-card" data-nav="matches" data-filter="pred"><div class="task-num red">' + r.missing_results + '</div><div class="task-label">\u9700\u8865\u8d5b\u679c</div></div>' +
    '<div class="task-card" data-nav="matches" data-filter="wait"><div class="task-num yellow">' + (s.total - s.predicted) + '</div><div class="task-label">\u5f85\u9884\u6d4b</div></div>' +
    '<div class="task-card" data-nav="matches" data-filter="done"><div class="task-num green">' + s.scored + '</div><div class="task-label">\u53ef\u590d\u76d8</div></div>' +
    '<div class="task-card" data-nav="plans"><div class="task-num gray">' + (r.plan_info ? r.plan_info.plan_count : "\u2014") + '</div><div class="task-label">\u8ba1\u5212\u5355</div></div>';
  document.querySelectorAll("#console-tasks .task-card").forEach(card => {
    card.addEventListener("click", () => {
      if (card.dataset.filter) {
        navigateToMatches(card.dataset.filter);
      } else {
        var navItem = document.querySelector('.nav-item[data-panel="' + card.dataset.nav + '"]');
        if (navItem) navItem.click();
      }
    });
  });

  // Preview: data to operate on -- all matches needing action (not just today)
  window._consoleNeedR = []; window._consoleNeedP = [];
  try {
    var previewData = await fetch("/api/dashboard/matches_grouped").then(function(d) { return d.json(); });
    for (var gi=0; gi<(previewData.groups||[]).length; gi++) {
      var gms = previewData.groups[gi].matches;
      for (var mi=0; mi<gms.length; mi++) {
        var m = gms[mi];
        if (m.actual_score) continue;
        if (!m.direction) { window._consoleNeedP.push(m); }
        else if (m.match_time) { window._consoleNeedR.push(m); }
      }
    }
  } catch(e) { console.log("preview error:",e); }

  // Render function (reusable after manual save)
  window._renderPreview = function() {
    var nr = window._consoleNeedR, np = window._consoleNeedP;
    var manualOn = document.getElementById("console-preview").classList.contains("manual-mode");
    var ph = '<div class="cp-col cp-col-wide"><h4>\u9700\u8865\u8d5b\u679c ('+nr.length+')</h4>';
    if (nr.length===0) ph += '<div class="cp-empty">\u65e0</div>';
    else for (var j=0;j<nr.length;j++) {
      var mr=nr[j]; var t=mr.match_time?mr.match_time.substring(5,16):"";
      var hasDir = mr.direction && mr.direction !== "";
      var badge = hasDir ? '<span class="cp-status done">\u5df2\u9884\u6d4b</span>' : '<span class="cp-status wait">\u7b49\u5f85\u9884\u6d4b</span>';
      ph += '<div class="cp-row cp-row-card" data-mid="'+mr.match_id+'" style="cursor:pointer">';
      ph += '<span class="cp-mid">'+fmt(mr.match_id)+'</span>';
      ph += '<span class="cp-teams">'+fmt(mr.home)+' vs '+fmt(mr.away)+'</span>';
      ph += '<span class="cp-time">'+t+'</span>';
      ph += badge;
      if (manualOn) {
        ph += '<span class="cp-inputs"><input class="cp-inp-score" data-mid="'+mr.match_id+'" placeholder="\u6bd4\u5206 \u59823:1" size="8"> <input class="cp-inp-hf" data-mid="'+mr.match_id+'" placeholder="\u534a\u5168\u5982\u80dc\u80dc" size="6"> <button class="cp-btn-save" data-mid="'+mr.match_id+'">Save</button></span>';
      }
      ph += '</div>';
    }
    ph += '</div><div class="cp-col cp-col-wide"><h4>\u5f85\u9884\u6d4b ('+np.length+') <label class="cp-sel-all" style="font-weight:normal;font-size:12px;margin-left:8px;cursor:pointer"><input type="checkbox" class="cp-chk-all" onchange="var c=this.checked;document.querySelectorAll(\'.cp-chk-pend\').forEach(function(cb){cb.checked=c})"> \u5168\u9009</label></h4>';
    if (np.length===0) ph += '<div class="cp-empty">\u65e0</div>';
    else for (var k=0;k<np.length;k++) {
      var p=np[k];
      ph += '<div class="cp-row cp-row-card" data-mid="'+p.match_id+'" style="cursor:pointer">';
      ph += '<input type="checkbox" class="cp-chk-pend" data-mid="'+p.match_id+'" style="margin-right:6px;cursor:pointer" onclick="event.stopPropagation()"' + (window._dataCollectedIds && window._dataCollectedIds[p.match_id] ? ' checked' : '') + '>';
      ph += '<span class="cp-mid">'+fmt(p.match_id)+'</span>';
      ph += '<span class="cp-teams">'+fmt(p.home)+' vs '+fmt(p.away)+'</span>';
      var _hasData = window._dataCollectedIds && window._dataCollectedIds[p.match_id];
      ph += '<span class="cp-status ' + (_hasData ? 'done' : 'wait') + '" style="' + (_hasData ? 'background:#dbeafe;color:#2563eb' : '') + '" data-mid="'+p.match_id+'">' + (_hasData ? '\u2713 \u5df2\u91c7\u96c6' : '\u7b49\u5f85\u9884\u6d4b') + '</span>';
      ph += '</div>';
    }
    ph += '</div>';
    document.getElementById("console-preview").innerHTML = ph;

    // Bind save buttons
    var saveBtns = document.querySelectorAll(".cp-btn-save");
    for (var si=0; si<saveBtns.length; si++) {
      saveBtns[si].onclick = async function() {
        var mid = this.dataset.mid;
        var inpScore = document.querySelector('.cp-inp-score[data-mid="'+mid+'"]');
        var inpHf = document.querySelector('.cp-inp-hf[data-mid="'+mid+'"]');
        var score = inpScore ? inpScore.value.trim() : "";
        var hf = inpHf ? inpHf.value.trim() : "";
        if (!score) { alert("\u8bf7\u8f93\u5165\u6bd4\u5206"); return; }
        this.disabled = true; this.textContent = "...";
        try {
          var rr = await fetch("/api/dashboard/action/save_manual_result", {
            method: "POST", headers: {"Content-Type": "application/json"},
            body: JSON.stringify({match_id: mid, actual_score: score, half_full: hf})
          }).then(function(d){return d.json();});
          logMsg(rr.msg || (rr.ok ? "Saved" : "Failed"), rr.ok ? "#16a34a" : "#dc2626");
          if (rr.ok) {
            window._consoleNeedR = window._consoleNeedR.filter(function(m){return m.match_id !== mid;});
            window._renderPreview();

    var needResultRows = document.querySelectorAll(".cp-row-card[data-mid]");
    for (var ri=0; ri<needResultRows.length; ri++) {
      needResultRows[ri].onclick = function() {
        var mid = this.dataset.mid;
        var fundNav = document.querySelector('.nav-item[data-panel="fundamental"]');
        if (fundNav) fundNav.click();
        setTimeout(function() {
          var card = document.querySelector('.fund-card[data-mid="'+mid+'"]');
          if (card) card.scrollIntoView({behavior: "smooth", block: "center"});
        }, 500);
      };
    }
          }
        } catch(e) { logMsg("Save error: " + e, "#dc2626"); }
        this.disabled = false; this.textContent = "Save";
      };
    }

    // Bind "Wait predict" clickable badges
    var badges = document.querySelectorAll(".cp-status.wait.clickable");
    for (var bi=0; bi<badges.length; bi++) {
      badges[bi].onclick = function() {
        var mid = this.dataset.mid;
        logMsg("Prediction for " + mid + " will run via pipeline", "#d97706");
        document.querySelector('.nav-item[data-panel="prediction"]').click();
      };
    }
  };
  window._renderPreview();

  const clog = document.getElementById("console-log");
  function logMsg(msg, color) {
    clog.style.display = "block";
    clog.innerHTML += '<div style="color:' + (color || "#6b7280") + '">[' + new Date().toLocaleTimeString("zh-CN") + '] ' + msg + '</div>';
    clog.scrollTop = clog.scrollHeight;
  }
  // Load persistent log history
  try {
    var logResp = await fetch("/api/dashboard/console_log").then(function(r){return r.json();});
    if (logResp.log) {
      clog.style.display = "block";
      clog.innerHTML = logResp.log.split("\n").filter(function(l){return l.trim();}).map(function(l){
        return '<div style="color:#64748b;font-size:11px">' + l + '</div>';
      }).join("") + clog.innerHTML;
      clog.scrollTop = clog.scrollHeight;
    }
  } catch(e) {}
  document.getElementById("btn-fetch-results").onclick = async function() {
    var btn = this;
    var origHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader-2" width="16" height="16"></i> 查询中...';
    logMsg("正在查询赛果...", "#2563eb");
    try {
      const d = await fetch("/api/dashboard/action/fetch_results").then(r => r.json());
      if (d.logs && d.logs.length) {
        d.logs.forEach(function(l) { logMsg(l, l.indexOf("需手动")>=0 ? "#dc2626" : l.indexOf("OK:")>=0 ? "#16a34a" : l.indexOf("===")>=0 ? "#2563eb" : "#6b7280"); });
      }
      logMsg("完成: " + (d.updated||0) + "/" + (d.total_pending||0) + " 场", (d.updated||0) > 0 ? "#16a34a" : "#d97706");
      if (d.results && d.results.length > 0) {
        showResultModal(d.results, d.updated);
      }
      // Refresh console preview after fetch
      if (d.updated > 0) {
        logMsg("正在刷新控制台预览...", "#2563eb");
        prevData = await fetch("/api/dashboard/matches_grouped").then(function(rr){return rr.json();});
        window._consoleNeedR = []; window._consoleNeedP = [];
        for (var gi=0; gi<(prevData.groups||[]).length; gi++) {
          var gms = prevData.groups[gi].matches;
          for (var mi=0; mi<gms.length; mi++) {
            var mm = gms[mi];
            if (mm.actual_score) continue;
            if (!mm.direction) { window._consoleNeedP.push(mm); }
            else if (mm.match_time) { window._consoleNeedR.push(mm); }
          }
        }
        if (window._renderPreview) window._renderPreview();
        // Also refresh overviewData and task cards
        overviewData = await fetch("/api/dashboard/overview").then(function(rr){return rr.json();});
        var r = overviewData;
        var s = r.stats;
        document.getElementById("console-tasks").innerHTML =
          '<div class="task-card" data-nav="matches" data-filter="pred"><div class="task-num red">' + r.missing_results + '</div><div class="task-label">需补赛果</div></div>' +
          '<div class="task-card" data-nav="matches" data-filter="wait"><div class="task-num yellow">' + (s.total - s.predicted) + '</div><div class="task-label">待预测</div></div>' +
          '<div class="task-card" data-nav="matches" data-filter="done"><div class="task-num green">' + s.scored + '</div><div class="task-label">可复盘</div></div>' +
          '<div class="task-card" data-nav="plans"><div class="task-num gray">' + (r.plan_info ? r.plan_info.plan_count : "—") + '</div><div class="task-label">计划单</div></div>';
        document.querySelectorAll("#console-tasks .task-card").forEach(function(card) {
          card.addEventListener("click", function() {
            if (card.dataset.filter) { navigateToMatches(card.dataset.filter); }
            else { var ni = document.querySelector('.nav-item[data-panel="' + card.dataset.nav + '"]'); if (ni) ni.click(); }
          });
        });
      }
    } catch(e) { logMsg("查询失败: " + e.message, "#dc2626"); }
    btn.disabled = false;
    btn.innerHTML = origHTML;
    lucide.createIcons();
  };
document.getElementById("btn-manual-entry").onclick = () => {
    var preview = document.getElementById("console-preview");
    var isOn = preview.classList.toggle("manual-mode");
    this.innerHTML = isOn ? '<i data-lucide="check" width="16" height="16"></i> Exit manual' : '<i data-lucide="edit-3" width="16" height="16"></i> Manual entry';
    logMsg(isOn ? "\u624b\u52a8\u5f55\u5165\u6a21\u5f0f ON" : "\u624b\u52a8\u5f55\u5165\u6a21\u5f0f OFF", isOn ? "#2563eb" : "#6b7280");
    if (window._renderPreview) window._renderPreview();
    lucide.createIcons();
  }
  document.getElementById("btn-fetch-jczq").onclick = async () => {
    logMsg("正在从竞彩网获取比赛...", "#2563eb");
    try {
      const d = await fetch("/api/dashboard/action/fetch_jczq").then(r => r.json());
      if (d.logs && d.logs.length) d.logs.forEach(function(l) { logMsg(l, l.indexOf("ERROR")>=0 ? "#dc2626" : l.indexOf("\u65b0\u589e")>=0 ? "#16a34a" : "#6b7280"); });
      else logMsg(d.msg || "\u83b7\u53d6\u5b8c\u6210", "#16a34a");
      if (d.ok && d.new_matches && d.new_matches.length > 0) {
        showFetchJczqModal(d.new_matches, d.new_count);
        window._modalAfterClose = "fundamental";
      } else {
        logMsg(d.msg || "\u65e0\u65b0\u589e\u6bd4\u8d5b", "#6b7280");
      }
    } catch(e) { logMsg("\u83b7\u53d6\u5931\u8d25: " + e.message, "#dc2626"); }
  };
  document.getElementById("btn-select-predict").onclick = async function() {
    var btn = this;
    // Collect selected pending match IDs
    var checked = document.querySelectorAll(".cp-chk-pend:checked");
    var selectedIds = [];
    for (var ci = 0; ci < checked.length; ci++) {
      selectedIds.push(checked[ci].dataset.mid);
    }
    if (selectedIds.length === 0) {
      logMsg("请先在待预测列表中勾选比赛", "#dc2626");
      return;
    }
    btn.disabled = true;
    var origText = btn.textContent;
    btn.textContent = "预测中...";
    logMsg("正在启动预测管道 (" + selectedIds.length + " 场)...", "#2563eb");
    try {
      const d = await fetch("/api/dashboard/action/run_predict", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({match_ids: selectedIds})
      }).then(r => r.json());
      logMsg(d.msg || "预测已启动", "#16a34a");
      if (d.ok) {
        logMsg("正在监控进度...", "#d97706");
        var shownLines = {};
        var pollTimer = setInterval(async function() {
          try {
            var pr = await fetch("/api/dashboard/pipeline_progress").then(function(r){return r.json();});
            if (pr.log) {
              var plines = pr.log.split("\n").filter(function(l){return l.trim();});
              for (var i = 0; i < plines.length; i++) {
                var line = plines[i].trim();
                if (!line || shownLines[line]) continue;
                shownLines[line] = true;
                if (line.indexOf("[OK]") >= 0 || line.indexOf("All steps") >= 0) {
                  logMsg(line, "#16a34a");
                } else if (line.indexOf("[ERROR]") >= 0) {
                  logMsg(line, "#ef4444");
                } else if (line.indexOf("[DB]") >= 0 || line.indexOf("DDI") >= 0 || line.indexOf("Fit") >= 0 || line.indexOf("Rating") >= 0 || line.indexOf("History") >= 0 || line.indexOf("saved") >= 0) {
                  logMsg(line, "#94a3b8");
                }
              }
            }
            if (pr.done) {
              clearInterval(pollTimer);
              if (!shownLines["__done__"]) {
                shownLines["__done__"] = true;
                logMsg("预测完成！请刷新页面查看结果", "#16a34a");
              }
              btn.disabled = false;
              btn.textContent = origText;
              lucide.createIcons();
            }
          } catch(e2) {}
        }, 3000);
      }
    }
    catch(e) { logMsg("预测失败: " + e.message, "#dc2626"); btn.disabled = false; btn.textContent = origText; }
  };
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
// ==================== 2. MATCHES ====================
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
    html += '<div class="match-group"><div class="group-header" data-gi="' + gi + '"><i data-lucide="chevron-right" class="arrow" width="16" height="16"></i>' + g.sale_date + '<span class="count">' + g.matches.length + ' \u573a</span></div><div class="group-body"><table><thead><tr><th>\u7f16\u53f7</th><th>\u4e3b\u961f</th><th>\u5ba2\u961f</th><th>\u65f6\u95f4</th><th>\u4e8b\u4ef6</th><th>\u65b9\u5411</th><th>\u8bc4\u7ea7</th><th>\u8d34\u5408\u5ea6</th><th>\u8d5b\u679c</th></tr></thead><tbody>';
    g.matches.forEach(m => {
      const timeStr = m.match_time ? m.match_time.substring(5, 16) : "\u2014";
      html += '<tr class="' + rowClass(m) + '"><td>' + fmt(m.match_id) + '</td><td>' + fmt(m.home) + '</td><td>' + fmt(m.away) + '</td><td>' + timeStr + '</td><td>' + fmt(m.event) + '</td><td>' + dirBadgeHTML(m.rating, m.direction) + '</td><td>' + fmt(m.rating) + '</td><td>' + fmt1(m.fit_score, "\u2014") + '</td><td>' + fmt(m.actual_score, "\u2014") + '</td></tr>';
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
  allMatchesFlat = [];
  allMatchGroups = r.groups || [];
  for (const g of allMatchGroups) {
    for (const m of g.matches) { allMatchesFlat.push(m); }
  }
  filterMatches();
}
// Pill click handler for match toolbar
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("#match-toolbar .pill").forEach(pill => {
    pill.addEventListener("click", function() {
      document.querySelectorAll("#match-toolbar .pill").forEach(p => p.classList.remove("on"));
      this.classList.add("on");
    });
  });
});
// ==================== 3. PREDICTION ====================
async function loadPrediction() {
  const r = await fetch("/api/dashboard/matches_grouped").then(d => d.json());
  let html = "";
  for (const g of (r.groups || [])) {
    for (const m of g.matches) {
      if (!m.direction) continue;
      html += '<div class="pred-card"><div class="pc-header"><div class="pc-teams">' + fmt(m.home) + ' vs ' + fmt(m.away) + '</div>' + dirBadgeHTML(m.rating, m.direction) + '</div>';
      html += '<div class="pc-info"><span>' + fmt(m.match_id) + '</span><span>\u8d34\u5408: ' + fmt1(m.fit_score, "-") + '</span></div>';
      if (m.actual_score) html += '<div class="pc-score">\u8d5b\u679c: ' + m.actual_score + '</div>';
      html += '</div>';
    }
  }
  document.getElementById("pred-cards").innerHTML = html || '<div class="empty">\u6682\u65e0\u9884\u6d4b\u6570\u636e</div>';
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
// ==================== FUNDAMENTAL ====================
function toggleFaDateGroup(el) {
  var group = el.closest(".fa-date-group");
  if (!group) return;
  var label = group.querySelector(".fa-date-label");
  label.classList.toggle("collapsed");
}

function toggleFaCard(el) {
  var card = el.closest(".fa-card");
  if (!card) return;
  var wasExpanded = card.classList.contains("expanded");
  // Collapse all others
  document.querySelectorAll(".fa-card.expanded").forEach(function(c) {
    if (c !== card) c.classList.remove("expanded");
  });
  if (wasExpanded) card.classList.remove("expanded");
  else card.classList.add("expanded");
}

function fmtSp(v) {
  if (v === null || v === undefined || v === "" || v === 0) return "-";
  var n = Number(v);
  return isNaN(n) ? String(v) : n.toFixed(2);
}


function renderNarrativeCapsules(narrative) {
  if (!narrative) return "";
  var sections = narrative.split(/\n● /);
  var h = "";
  for (var i = 0; i < sections.length; i++) {
    var section = sections[i].trim();
    if (!section) continue;
    var lines = section.split("\n").map(function(l) { return l.trim(); }).filter(function(l) { return l; });
    if (lines.length === 0) continue;
    var title = lines[0].replace(/^● /, "");
    if (title === "竞彩赔率" || title === "系统预测") continue;
    var contentLines = lines.slice(1);
    h += '<div class="narr-section">';
    h += '<div class="narr-title">' + enc(title) + '</div>';
    if (title === "战意背景") {
      var combined = contentLines.join(" | ");
      if (combined) h += '<div class="narr-pills"><span class="narr-pill narr-pill-wide">' + enc(combined) + '</span></div>';
    } else {
      h += '<div class="narr-pills">';
      for (var j = 0; j < contentLines.length; j++) {
        var line = contentLines[j];
        if (!line) continue;
        var items = [];
        if (line.indexOf(" | ") !== -1) {
          items = line.split(" | ");
        } else if (line.indexOf(" / ") !== -1) {
          items = line.split(" / ");
        } else {
          items = [line];
        }
        for (var k = 0; k < items.length; k++) {
          var item = items[k].trim();
          if (item) h += '<span class="narr-pill">' + enc(item) + '</span>';
        }
      }
      h += '</div>';
    }
    h += '</div>';
  }
  return h;
}


function parseNarrativeSection(narrative, sectionName) {
  if (!narrative || !sectionName) return "";
  var idx = narrative.indexOf("\u25cf " + sectionName);
  if (idx < 0) return "";
  var start = idx + sectionName.length + 2;
  var end = narrative.indexOf("\u25cf ", start);
  if (end < 0) end = narrative.length;
  return narrative.substring(start, end).trim();
}

function enc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function faDirBadge(dir, rating) {
  if (!dir) return '<span class="fa-c-wait">等待预测</span>';
  var cls = "win";
  if (dir === "负" || dir === "让负") cls = "loss";
  return '<span class="fa-dir-badge ' + cls + '">' + dir + '</span>';
}

function faBarHTML(physProb, mktProb, lambdaDiff, ddi) {
  var hasPhys = physProb && typeof physProb === 'object' && Object.keys(physProb).length > 0;
  var hw = physProb && physProb.home_win || 0;
  var dr = physProb && physProb.draw || 0;
  var aw = physProb && physProb.away_win || 0;
  var mhw = mktProb && mktProb.home_win || 0;
  var mdr = mktProb && mktProb.draw || 0;
  var maw = mktProb && mktProb.away_win || 0;
  var maxP = Math.max(hw, dr, aw, 0.01);
  var scale = 60 / maxP;
  var maxM = Math.max(mhw, mdr, maw, 0.01);
  var mScale = 60 / maxM;
  var h = '';
  h += '<div class="fa-exp-chart"><div class="ch-title">lambda vs p_market</div>';
  if (hasPhys) {
    h += '<div style="display:flex;gap:6px;justify-content:center;align-items:flex-end;height:68px">';
    var labels = ['主胜','平','客胜'];
    var keys = ['home_win','draw','away_win'];
    for (var i=0;i<3;i++) {
      var pv = physProb[keys[i]] || 0;
      var mv = mktProb && mktProb[keys[i]] || 0;
      h += '<div style="text-align:center;width:44px">';
      h += '<div style="font-size:9px;font-weight:600;color:#374151">'+(pv*100).toFixed(1)+'/'+(mv*100).toFixed(1)+'</div>';
      h += '<div style="display:flex;gap:3px;justify-content:center;align-items:flex-end;height:48px">';
      h += '<div class="fa-bar-fill phy" style="height:'+Math.max(pv*scale,2)+'px;width:16px"></div>';
      h += '<div class="fa-bar-fill mkt" style="height:'+Math.max(mv*mScale,2)+'px;width:16px"></div>';
      h += '</div>';
      h += '<div style="font-size:9px;color:#6b7280">'+labels[i]+'</div>';
      h += '</div>';
    }
    h += '</div>';
    if (lambdaDiff !== null && lambdaDiff !== undefined) {
      h += '<div class="ch-sub"><span>lambda差: '+(lambdaDiff>=0?'+':'')+lambdaDiff.toFixed(4)+'</span></div>';
    }
  } else {
    h += '<div style="font-size:11px;color:#9ca3af;text-align:center;padding:14px 0">无物理概率数据</div>';
  }
  h += '</div>';
  h += '<div class="fa-exp-chart"><div class="ch-title">竞彩让球概率</div>';
  var jp = ddi && ddi.jc_hcp_prob;
  if (jp) {
    var jlabels = ['让胜','平','让负'];
    var jkeys = ['win','draw','lose'];
    var jvals = [(jp.win||0),(jp.draw||0),(jp.lose||0)];
    var jmax = Math.max(jvals[0],jvals[1],jvals[2],0.01);
    var jscale = 60 / jmax;
    h += '<div style="display:flex;gap:6px;justify-content:center;align-items:flex-end;height:68px">';
    for (var i=0;i<3;i++) {
      h += '<div style="text-align:center;width:44px">';
      h += '<div style="font-size:9px;font-weight:600;color:#374151">'+(jvals[i]*100).toFixed(1)+'%</div>';
      h += '<div class="fa-bar-fill phy" style="height:'+Math.max(jvals[i]*jscale,2)+'px;width:22px;margin:0 auto"></div>';
      h += '<div style="font-size:9px;color:#6b7280;margin-top:2px">'+jlabels[i]+'</div>';
      h += '</div>';
    }
    h += '</div>';
  } else {
    h += '<div style="font-size:11px;color:#9ca3af;text-align:center;padding:14px 0">无让球概率数据</div>';
  }
  h += '</div>';
  h += '<div class="fa-exp-chart"><div class="ch-title">关键指标</div><div class="fa-exp-analysis">';
  if (lambdaDiff !== null && lambdaDiff !== undefined) {
    h += '<div class="fa-analysis-item"><div class="ai-head"><span class="ai-icon">lambda</span><span class="ai-label">lambda差值</span></div><div class="ai-body">'+(lambdaDiff>=0?'+':'')+lambdaDiff.toFixed(4)+'</div></div>';
  }
  if (ddi && ddi.protection_triggered) {
    h += '<div class="fa-analysis-item" style="border-color:#f59e0b"><div class="ai-head"><span class="ai-icon">!</span><span class="ai-label">保护触发</span></div><div class="ai-body-muted">信号已被保护性过滤</div></div>';
  }
  if (ddi && ddi.sp_missing) {
    h += '<div class="fa-analysis-item" style="border-color:#6b7280"><div class="ai-head"><span class="ai-icon">!</span><span class="ai-label">SP未开售</span></div><div class="ai-body-muted">竞彩未开售胜平负</div></div>';
  }
  h += '</div></div>';
  return h;
}


async function loadFundamental() {
  var data = await fetch("/api/dashboard/fundamental").then(function(r) { return r.json(); });
  if (!data || !data.length) {
    document.getElementById("fundamental-content").innerHTML = '<div class="empty">暂无基本面分析数据</div>';
    return;
  }
  var groups = {};
  for (var i = 0; i < data.length; i++) {
    var m = data[i];
    var t = m.time || "";
    var key = t.length >= 10 ? t.substring(0, 10) : "unknown";
    if (!groups[key]) groups[key] = [];
    groups[key].push(m);
  }
  var h = "";
  var keys = Object.keys(groups).sort().reverse();
  for (var gi = 0; gi < keys.length; gi++) {
    var dk = keys[gi];
    var ml = groups[dk];
    var labelText = dk === "unknown" ? "未知日期" : dk;
    h += '<div class="fa-date-group">';
    h += '<div class="fa-date-label" onclick="toggleFaDateGroup(this)">';
    h += '<span class="fa-date-arrow">\u25bc</span> 📅 ' + labelText;
    h += '<span class="fa-date-count">' + ml.length + ' 场</span></div>';
    h += '<div class="fa-date-body">';
    for (var mi = 0; mi < ml.length; mi++) {
      var a = ml[mi];
      var timeStr = a.time ? (a.time.length >= 16 ? a.time.substring(5, 16) : a.time.substring(5, 10)) : "-";
      var hasScore = a.actual_score && a.actual_score !== "";
      var hasDir = a.direction && a.direction !== "";
      var hitClass = "";
      var hitLabel = "";
      var hitBadgeClass = "";
      if (hasScore) {
        if (a.hit === 1 || a.hit === true) { hitClass = " hit"; hitLabel = "命中"; hitBadgeClass = "hit"; }
        else if (a.hit === 0 || a.hit === false) { hitClass = " miss"; hitLabel = "偏离"; hitBadgeClass = "miss"; }
        else { hitClass = ""; }
      }
      var narrative = a.narrative || "";
      var groupText = "世界杯";
      var nsIdx = narrative.indexOf("\u25cf 小组形势");
      if (nsIdx >= 0) {
        var groupLine = narrative.substring(nsIdx + 7).split("\n")[0].trim();
        var gMatch = groupLine.match(/([A-Z\u4e00-\u9fff])\u7ec4/);
        if (gMatch) groupText = gMatch[1] + "组";
      }
      h += '<div class="fa-card' + hitClass + '" onclick="toggleFaCard(this)" data-mid="' + a.id + '">';
      if (hasScore) {
        h += '<div class="fa-card-row has-result">';
        h += '<div class="fa-c-num">' + fmt(a.id) + '</div>';
        h += '<div class="fa-c-time">' + timeStr + '</div>';
        h += '<div class="fa-c-event">' + groupText + '</div>';
        h += '<div class="fa-c-teams"><span class="t-h">' + fmt(a.home) + '</span><span class="t-vs">VS</span><span class="t-a">' + fmt(a.away) + '</span></div>';
        var hcpVal = a.handicap || "";
        var hcpS = hcpVal !== "" ? hcpVal : "-";
        h += '<div class="fa-c-odds">';
        h += '<div class="odds-group"><span class="og-item og-sp-h">' + fmtSp(a.sp_home) + '</span><span class="og-item og-sp-d">' + fmtSp(a.sp_draw) + '</span><span class="og-item og-sp-a">' + fmtSp(a.sp_away) + '</span></div>';
        h += '<div class="odds-group"><span class="hcp-line">' + hcpS + '</span><span class="og-item og-sp-h">' + fmtSp(a.hh_win) + '</span><span class="og-item og-sp-d">' + fmtSp(a.hh_draw) + '</span><span class="og-item og-sp-a">' + fmtSp(a.hh_lose) + '</span></div>';
        h += '</div>';
        h += '<div class="fa-c-dir">' + faDirBadge(a.direction, a.rating) + '</div>';
        h += '<div style="text-align:center">';
        h += '<div class="fa-c-score">' + fmt(a.actual_score, "-") + '</div>';
        h += '<div class="fa-c-half">' + fmt(a.half_full, "-") + '</div>';
        h += '</div>';
        h += '<div><span class="fa-c-hit ' + hitBadgeClass + '">' + (hitLabel || "待确认") + '</span></div>';
        h += '</div>';
      } else {
        h += '<div class="fa-card-row no-result">';
        h += '<div class="fa-c-num">' + fmt(a.id) + '</div>';
        h += '<div class="fa-c-time">' + timeStr + '</div>';
        h += '<div class="fa-c-event">' + groupText + '</div>';
        h += '<div class="fa-c-teams"><span class="t-h">' + fmt(a.home) + '</span><span class="t-vs">VS</span><span class="t-a">' + fmt(a.away) + '</span></div>';
        var spAllMissing = a.sp_home == null && a.sp_draw == null && a.sp_away == null;
        h += '<div class="fa-c-odds">';
        if (spAllMissing) {
          h += '<span class="fa-c-sp-missing">⚠未开售</span>';
        } else {
          h += '<div class="odds-group"><span class="og-item og-sp-h">' + fmtSp(a.sp_home) + '</span><span class="og-item og-sp-d">' + fmtSp(a.sp_draw) + '</span><span class="og-item og-sp-a">' + fmtSp(a.sp_away) + '</span></div>';
          var hcp = a.handicap || "";
          var hcpStr = hcp !== "" ? hcp : "-";
          h += '<div class="odds-group"><span class="hcp-line">' + hcpStr + '</span><span class="og-item og-sp-h">' + fmtSp(a.hh_win) + '</span><span class="og-item og-sp-d">' + fmtSp(a.hh_draw) + '</span><span class="og-item og-sp-a">' + fmtSp(a.hh_lose) + '</span></div>';
        }
        h += '</div>';
        h += '<div class="fa-c-dir">' + faDirBadge(a.direction, a.rating) + '</div>';
        h += '<div class="fa-c-fit-wrap"><span class="fa-c-fit">' + fmt1(a.fit_score, "-") + '</span><span class="fa-c-rating ' + (a.rating || "") + '">' + fmt(a.rating, "-") + '</span></div>';
        h += '<div class="fa-c-expand">▼</div>';
        h += '</div>';
      }
            h += '<div class="fa-expand" onclick="event.stopPropagation()">';
      var goals = a.top2_goals || [];
      var hf2 = a.top2_hf || [];
      var scores = a.top3_scores || [];
      if (goals.length || hf2.length || scores.length) {
        h += '<div class="fa-exp-pills">';
        if (goals.length) h += '<div class="fa-exp-pill"><span class="pil-icon">\u26bd</span><span class="pil-label">总进球</span><span class="pil-value">' + goals.join(" / ") + '</span></div>';
        if (hf2.length) h += '<div class="fa-exp-pill"><span class="pil-icon">\U0001f504</span><span class="pil-label">半全场</span><span class="pil-value">' + hf2.join(" / ") + '</span></div>';
        if (scores.length) h += '<div class="fa-exp-pill"><span class="pil-icon">\U0001f3af</span><span class="pil-label">比分</span><span class="pil-value">' + scores.join(" / ") + '</span></div>';
        h += '</div>';
      }
      if (hasScore) {
        h += '<div class="fa-exp-result">';
        h += '<div class="er-item"><span class="er-label">赛果</span><span class="er-score">' + fmt(a.actual_score, "-") + '</span></div>';
        h += '<div class="er-item"><span class="er-label">半全场</span><span class="er-value">' + fmt(a.half_full, "-") + '</span></div>';
        if (a.direction) h += '<div class="er-item"><span class="er-label">预测方向</span><span class="er-value">' + enc(a.direction) + '</span></div>';
        if (hitLabel) h += '<div class="er-item"><span class="er-label">诊断</span><span class="er-hit ' + hitBadgeClass + '">' + hitLabel + '</span></div>';
        h += '</div>';
      } else {
        if (hasDir) {
          h += '<div class="fa-exp-grid">';
          h += faBarHTML(a.physical, a.p_market, a.lambda_diff, a);
          h += '</div>';
        }
        if (narrative) {
          var bgSections = ['小组形势', '战意背景', '近期战绩'];
          h += '<div class="fa-exp-bg-grid">';
          for (var si = 0; si < bgSections.length; si++) {
            var secContent = parseNarrativeSection(narrative, bgSections[si]);
            if (secContent) {
              h += '<div class="fa-exp-bg-card"><div class="bg-title">' + bgSections[si] + '</div><div class="bg-body">' + enc(secContent) + '</div></div>';
            } else {
              h += '<div class="fa-exp-bg-card"><div class="bg-title">' + bgSections[si] + '</div><div class="bg-body-muted">暂无数据</div></div>';
            }
          }
          h += '</div>';
        }
      }
      h += '</div>';
      h += '</div>';
    }
    h += '</div></div>';
  }
  document.getElementById("fundamental-content").innerHTML = h || '<div class="empty">暂无数据</div>';
  lucide.createIcons();
}


function toggleSupplement() {
  const box = document.getElementById("supplement-box");
  box.style.display = box.style.display === "none" ? "block" : "none";
  if (box.style.display === "block") document.getElementById("supplement-input").focus();
}

async function submitSupplement() {
  const text = document.getElementById("supplement-input").value.trim();
  const status = document.getElementById("supplement-status");
  if (!text) { status.textContent = "请先粘贴内容"; return; }
  status.textContent = "正在处理...";
  try {
    const resp = await fetch("/api/dashboard/fundamental/supplement", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    const result = await resp.json();
    if (result.ok) {
      status.textContent = "已更新 " + result.count + " 场比赛，刷新中...";
      document.getElementById("supplement-input").value = "";
      setTimeout(() => loadFundamental(), 500);
    } else {
      status.textContent = "失败: " + (result.error || "未知错误");
    }
  } catch (e) {
    status.textContent = "请求失败: " + e.message;
  }
}
// ==================== 4. PLANS ====================
async function loadPlans() {
  document.getElementById("plan-content").innerHTML = '<iframe src="/static/plan.html" style="width:100%;height:calc(100vh - 120px);border:none;border-radius:8px;background:#f5f6f8"></iframe>';
}
// ==================== 5. REVIEW ====================
async function loadReview() {
  const r = await fetch("/api/dashboard/review").then(d => d.json());
  document.getElementById("rv-total").textContent = r.total || 0;
  document.getElementById("rv-hits").textContent = r.hit || 0;
  document.getElementById("rv-hitrate").textContent = (r.hitrate || 0) + "%";
  document.getElementById("rv-ratings").innerHTML = '<div class="rv-num">' + (r.hit || 0) + '/' + (r.total || 0) + '</div><div class="rv-label">\u547d\u4e2d/\u603b\u8ba1</div>';
  let html = "";
  for (const item of (r.review_list || [])) {
    html += '<div class="rv-item ' + (item.hit ? "hit" : "miss") + '"><span class="rv-teams">' + item.match_id + ' ' + fmt(item.home) + ' vs ' + fmt(item.away) + '</span><span>' + fmt(item.actual_score) + '</span>' + dirBadgeHTML(item.rating, item.direction) + '<span>' + (item.hit ? "\u2705" : "\u274c") + '</span></div>';
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
// ==================== 6. SYSTEM ====================
async function loadSystem() {
  if (!overviewData) overviewData = await fetch("/api/dashboard/overview").then(d => d.json());
  const r = await fetch("/api/dashboard/analysis").then(d => d.json());
  document.getElementById("sys-status").innerHTML =
    '<div><strong>\u6570\u636e\u5e93</strong>: ' + (overviewData.stats ? overviewData.stats.total + ' \u6761\u8bb0\u5f55' : '-') + '</div>' +
    '<div><strong>APP \u6570\u636e</strong>: ' + (r.total_ratings || 0) + ' \u6761\u8bc4\u5206, ' + (r.completed || 0) + ' \u5df2\u5b8c\u6210, ' + (r.predicted || 0) + ' \u9884\u6d4b\u4e2d</div>' +
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

// ==================== FETCH MATCH DATA MODAL ====================
async function showFetchDataModal() {
  var modal = document.getElementById("fetchDataModal");
  var body = document.getElementById("fetchDataModalBody");
  body.innerHTML = '<div style="padding:20px;text-align:center;color:#94a3b8">加载中...</div>';
  modal.style.display = "flex";

  try {
    var pending = await fetch("/api/dashboard/matches_pending").then(function(r){return r.json();});
    var list = pending.pending || [];
    if (list.length === 0) {
      body.innerHTML = '<div style="padding:20px;text-align:center;color:var(--t3)">所有比赛已有预测数据，无需采集</div>';
      document.getElementById("btn-confirm-fetch").style.display = "none";
      return;
    }
    document.getElementById("btn-confirm-fetch").style.display = "";
    var todayCount = 0;
    var html = "";
    for (var i = 0; i < list.length; i++) {
      var m = list[i];
      var mt = m.match_time ? m.match_time.substring(5, 16) : "";
      var checked = m.is_today ? " checked" : "";
      if (m.is_today) todayCount++;
      html += '<label class="data-match-row"><input type="checkbox" value="' + m.match_id + '"' + checked + '>';
      html += '<span class="dm-mid">' + (m.match_id||"") + '</span>';
      html += '<span class="dm-teams">' + (m.home||"") + ' vs ' + (m.away||"") + '</span>';
      html += '<span class="dm-time">' + mt + '</span>';
      if (m.is_today) html += '<span class="dm-tag">今天</span>';
      html += '</label>';
    }
    body.innerHTML = html;
    document.getElementById("fetchDataSummary").textContent = "共 " + list.length + " 场待预测，已勾选 " + todayCount + " 场";
    var cbs = body.querySelectorAll("input[type=checkbox]");
    for (var ci = 0; ci < cbs.length; ci++) {
      cbs[ci].addEventListener("change", function(){
        var n = body.querySelectorAll("input[type=checkbox]:checked").length;
        document.getElementById("fetchDataSummary").textContent = "共 " + list.length + " 场待预测，已勾选 " + n + " 场";
      });
    }
  } catch(e) {
    body.innerHTML = '<div style="padding:20px;text-align:center;color:#ef4444">加载失败: ' + e.message + '</div>';
  }
}

async function submitFetchData() {
  var cbs = document.querySelectorAll("#fetchDataModalBody input[type=checkbox]:checked");
  var ids = [];
  for (var i = 0; i < cbs.length; i++) { ids.push(cbs[i].value); }
  if (ids.length === 0) { alert("请至少选择一场比赛"); return; }

  var btn = document.getElementById("btn-confirm-fetch");
  btn.disabled = true; btn.textContent = "采集中...";

  document.getElementById("fetchDataModal").style.display = "none";
  var rbody = document.getElementById("dataResultModalBody");
  rbody.innerHTML = '<div style="padding:20px;text-align:center;color:#e2e8f0">正在采集数据...<br><small>' + ids.length + ' 场比赛，请稍候</small></div>';
  var rmodal = document.getElementById("dataResultModal");
  rmodal.style.display = "flex";

  try {
    var resp = await fetch("/api/dashboard/action/fetch_match_data", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({match_ids: ids})
    });
    var d = await resp.json();
    showDataResultModal(d);
  } catch(e) {
    rbody.innerHTML = '<div style="padding:20px;text-align:center;color:#ef4444">采集失败: ' + e.message + '</div>';
  }
  btn.disabled = false; btn.textContent = "开始采集";
}

function showDataResultModal(data) {
  var rbody = document.getElementById("dataResultModalBody");
  var results = data.results || {};
  var logs = data.logs || [];

  var logHtml = '<div style="margin-bottom:12px;max-height:120px;overflow-y:auto;background:rgba(0,0,0,.2);padding:8px;border-radius:6px;font-size:11px;font-family:monospace;color:var(--t3,#94a3b8)">';
  for (var li = 0; li < logs.length; li++) {
    logHtml += '<div>' + logs[li] + '</div>';
  }
  logHtml += '</div>';

  var html = logHtml;
  var panelNames = {"panel_2_jc_odds": "竞彩赔率", "panel_3_asian_hcp": "亚洲盘口", "panel_4_sofascore": "SofaScore数据", "panel_5_recent_form": "近期战绩", "panel_6_8_ai": "AI分析(伤停/战意/特殊)"};
  var matchIds = Object.keys(results);
  // Save collected match IDs for console annotation
  window._dataCollectedIds = {};
  for (var _mi = 0; _mi < matchIds.length; _mi++) {
    window._dataCollectedIds[matchIds[_mi]] = true;
  }
  // Save collected match IDs for annotation
  window._dataCollectedIds = {};
  for (var _mi = 0; _mi < matchIds.length; _mi++) {
    window._dataCollectedIds[matchIds[_mi]] = true;
  }
  for (var mi = 0; mi < matchIds.length; mi++) {
    var mid = matchIds[mi];
    var mr = results[mid];
    html += '<div class="data-result-grid"><h4>' + mid + '</h4><div class="data-result-panels">';
    var panelKeys = ["panel_2_jc_odds", "panel_3_asian_hcp", "panel_4_sofascore", "panel_5_recent_form", "panel_6_8_ai"];
    for (var pi = 0; pi < panelKeys.length; pi++) {
      var pk = panelKeys[pi];
      var pr = mr[pk] || {};
      var icon = pr.ok ? '<span class="dr-ok">✓</span>' : (pr.skipped ? '<span class="dr-skip">○</span>' : '<span class="dr-fail">✗</span>');
      var extra = "";
      if (pk === "panel_5_recent_form" && pr.home_form) extra = " " + pr.home_form + " / " + pr.away_form;
      if (pk === "panel_2_jc_odds" && !pr.has_had && pr.has_hhad) extra = " (仅让球盘)";
      html += '<div class="dr-item">' + icon + ' ' + (panelNames[pk]||pk) + extra + '</div>';
    }
    html += '</div></div>';
  }
  rbody.innerHTML = html;
  var totalOk = 0, totalFail = 0;
  for (var mi2 = 0; mi2 < matchIds.length; mi2++) {
    var mr2 = results[matchIds[mi2]];
    var pk2 = ["panel_2_jc_odds", "panel_3_asian_hcp", "panel_5_recent_form", "panel_6_8_ai"];
    for (var pj = 0; pj < pk2.length; pj++) {
      if (mr2[pk2[pj]] && mr2[pk2[pj]].ok) totalOk++;
      else totalFail++;
    }
  }
  document.getElementById("dataResultSummary").textContent = "成功 " + totalOk + " / 失败 " + totalFail + " 项";
}

document.addEventListener("DOMContentLoaded", function(){
  var btn = document.getElementById("btn-fetch-data");
  if (btn) btn.addEventListener("click", showFetchDataModal);
});

// ==================== INIT ====================
document.getElementById("loadingOverlay").style.display = "none";
try { overview(); } catch(e) { console.error("Init overview error:", e); }
lucide.createIcons();


function showResultModal(results, count) {
  var body = document.getElementById("resultModalBody");
  var summary = document.getElementById("resultModalSummary");
  // Set title for result query
  var titleEl = document.querySelector("#resultModal .result-modal-head h3 span:last-child");
  if (titleEl) titleEl.textContent = '赛果查询结果';
  var h = '<table>';
  results.forEach(function(r) {
    h += '<tr><td>' + r.match_id + '</td><td>' + r.home + ' vs ' + r.away + '</td><td class="rm-score">' + (r.full_score||"") + '</td><td class="rm-hf">' + (r.half_full||"") + '</td></tr>';
  });
  h += '</table>';
  body.innerHTML = h;
  summary.textContent = '共更新 ' + count + ' 场比赛';
  document.getElementById("resultModal").style.display = "flex";
}
function closeDataResultModal() {
  document.getElementById("dataResultModal").style.display = "none";
  if (window._renderPreview) window._renderPreview();
}

function closeResultModal() {
  document.getElementById("resultModal").style.display = "none";
  refreshConsoleAfterFetch();
  if (window._modalAfterClose === "fundamental") {
    window._modalAfterClose = null;
    setTimeout(function() {
      var fundNav = document.querySelector('.nav-item[data-panel="fundamental"]');
      if (fundNav) {
        fundNav.click();
        setTimeout(function() {
          var logEl = document.getElementById("console-log");
          if (logEl) {
            logEl.style.display = "block";
            logEl.innerHTML += '<div style="color:#2563eb">[' + new Date().toLocaleTimeString("zh-CN") + '] \u5df2\u8df3\u8f6c\u5230\u57fa\u672c\u9762\u5206\u6790\uff0c\u786e\u8ba4\u6570\u636e\u540e\u53ef\u56de\u63a7\u5236\u53f0\u8fd0\u884c\u9884\u6d4b</div>';
            logEl.scrollTop = logEl.scrollHeight;
          }
        }, 1000);
      }
    }, 300);
  }
}
function showFetchJczqModal(matches, count) {
  var body = document.getElementById("resultModalBody");
  var summary = document.getElementById("resultModalSummary");
  var h = '<table>';
  matches.forEach(function(m) {
    var t = m.match_time ? m.match_time.substring(5, 16) : "";
    h += '<tr><td>' + fmt(m.match_id) + '</td><td>' + fmt(m.home) + ' vs ' + fmt(m.away) + '</td><td>' + t + '</td></tr>';
  });
  h += '</table>';
  body.innerHTML = h;
  summary.textContent = '共新增 ' + count + ' 场比赛';
  // Update modal title
  var titleEl = document.querySelector("#resultModal .result-modal-head h3 span:last-child");
  if (titleEl) titleEl.textContent = '获取竞彩网比赛';
  document.getElementById("resultModal").style.display = "flex";
}

async function refreshConsoleAfterFetch() {
  // Re-fetch overview data
  try {
    overviewData = await fetch("/api/dashboard/overview").then(function(d){return d.json();});
    var s = overviewData.stats;
    // Update task cards
    document.getElementById("console-tasks").innerHTML =
      '<div class="task-card" data-nav="matches" data-filter="pred"><div class="task-num red">' + overviewData.missing_results + '</div><div class="task-label">需补赛果</div></div>' +
      '<div class="task-card" data-nav="matches" data-filter="wait"><div class="task-num yellow">' + (s.total - s.predicted) + '</div><div class="task-label">待预测</div></div>' +
      '<div class="task-card" data-nav="matches" data-filter="done"><div class="task-num green">' + s.scored + '</div><div class="task-label">可复盘</div></div>' +
      '<div class="task-card" data-nav="plans"><div class="task-num gray">' + (overviewData.plan_info ? overviewData.plan_info.plan_count : "—") + '</div><div class="task-label">计划单</div></div>';
    // Re-bind click handlers
    document.querySelectorAll("#console-tasks .task-card").forEach(function(card){
      card.addEventListener("click", function(){
        if (card.dataset.filter) {
          navigateToMatches(card.dataset.filter);
        } else {
          var navItem = document.querySelector('.nav-item[data-panel="' + card.dataset.nav + '"]');
          if (navItem) navItem.click();
        }
      });
    });
    // Re-fetch preview data and re-render
    window._consoleNeedR = []; window._consoleNeedP = [];
    var previewData = await fetch("/api/dashboard/matches_grouped").then(function(d){return d.json();});
    for (var gi=0; gi<(previewData.groups||[]).length; gi++) {
      var gms = previewData.groups[gi].matches;
      for (var mi=0; mi<gms.length; mi++) {
        var m = gms[mi];
        if (m.actual_score) continue;
        if (!m.direction) { window._consoleNeedP.push(m); }
        else if (m.match_time) { window._consoleNeedR.push(m); }
      }
    }
    if (window._renderPreview) window._renderPreview();
  } catch(e) { console.log("refresh error:", e); }
}
