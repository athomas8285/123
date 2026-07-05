import { fmt, fmt1, fmtSp, enc, parseWeekday } from "./utils.js";
import { apiGet, apiPost } from "./api.js";

function spArrow(flag) {
  if (flag === 1) return '↑';
  if (flag === -1) return '↓';
  return '';
}

async function loadConsole() {
  try {
    window.overviewData = await fetch("/api/dashboard/overview").then(d => d.json());
  } catch(e) {
    console.error("loadConsole: overview fetch failed", e);
    document.getElementById("console-tasks").innerHTML = '<div class="cp-empty">加载失败，请刷新页面重试</div>';
    return;
  }
  const r = overviewData;
  const s = r.stats;
  document.getElementById("console-tasks").innerHTML =
    '<div class="task-card" data-nav="matches" data-filter="pred"><div class="task-num red">' + r.missing_results + '</div><div class="task-label">需补赛果</div></div>' +
    '<div class="task-card" data-nav="matches" data-filter="wait"><div class="task-num yellow">' + (s.total - s.predicted) + '</div><div class="task-label">待预测</div></div>' +
    '<div class="task-card" data-nav="matches" data-filter="done"><div class="task-num green">' + s.scored + '</div><div class="task-label">可复盘</div></div>' +
    '<div class="task-card" data-nav="plans"><div class="task-num gray">' + (r.plan_info ? r.plan_info.plan_count : "—") + '</div><div class="task-label">计划单</div></div>';
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
    var ph = '<div class="cp-col cp-col-wide"><h4>需补赛果 ('+nr.length+')</h4>';
    if (nr.length===0) ph += '<div class="cp-empty">无</div>';
        else for (var j=0;j<nr.length;j++) {
      var mr=nr[j]; var t=mr.match_time?mr.match_time.substring(5,16):"";
      var hasDir = mr.direction && mr.direction !== "";
      var badge = hasDir ? '<span class="cp-status done">已预测</span>' : '<span class="cp-status wait">等待预测</span>';
      var spAllMissing = (mr.jc_sp_home == null && mr.jc_sp_draw == null && mr.jc_sp_away == null);
      var hcpVal = mr.jc_handicap;
      var hcpStr = (hcpVal != null && hcpVal !== "") ? (hcpVal > 0 ? '+'+hcpVal : String(hcpVal)) : '';
      ph += '<div class="cp-row cp-row-card" data-mid="'+mr.match_id+'" style="cursor:pointer;flex-wrap:wrap">';
      ph += '<span class="cp-mid">'+fmt(mr.match_id)+'</span>';
      ph += '<span class="cp-teams">'+fmt(mr.home)+' vs '+fmt(mr.away)+'</span>';
      ph += '<div style="display:flex;align-items:center;gap:8px;font-size:11px;line-height:1.6;flex-wrap:wrap">';
      ph += '<span style="display:inline-flex;align-items:center;gap:4px;width:140px;flex-shrink:0">';
      if (spAllMissing) {
        ph += '<span style="font-size:9px;color:#94a3b8;font-family:monospace">(0)</span><span style="color:#f59e0b;font-size:11px">⚠未开售</span>';
      } else {
        ph += '<span style="font-size:9px;color:#94a3b8;font-family:monospace">(0)</span><span style="font-size:10.5px;font-family:monospace;font-weight:600;color:#ef5350;text-align:center;min-width:18px">'+fmtSp(mr.jc_sp_home)+'</span><span style="font-size:9px;color:#ef5350;font-weight:700">'+spArrow(mr.jc_sp_home_flag)+'</span><span style="font-size:10.5px;font-family:monospace;font-weight:600;color:#2563eb;text-align:center;min-width:18px">'+fmtSp(mr.jc_sp_draw)+'</span><span style="font-size:9px;color:#2563eb;font-weight:700">'+spArrow(mr.jc_sp_draw_flag)+'</span><span style="font-size:10.5px;font-family:monospace;font-weight:600;color:#16a34a;text-align:center;min-width:18px">'+fmtSp(mr.jc_sp_away)+'</span><span style="font-size:9px;color:#16a34a;font-weight:700">'+spArrow(mr.jc_sp_away_flag)+'</span>';
      }
      ph += '</span>';
      if (hcpStr && mr.jc_hhad_win != null) {
        ph += '<span style="display:inline-flex;align-items:center;gap:4px"><span style="font-size:9px;color:#94a3b8;font-family:monospace">('+hcpStr+')</span><span style="font-size:10.5px;font-family:monospace;font-weight:600;color:#ef5350;text-align:center;min-width:18px">'+fmtSp(mr.jc_hhad_win)+'</span>'+spArrow(mr.jc_hhad_win_flag)+'<span style="font-size:10.5px;font-family:monospace;font-weight:600;color:#2563eb;text-align:center;min-width:18px">'+fmtSp(mr.jc_hhad_draw)+'</span>'+spArrow(mr.jc_hhad_draw_flag)+'<span style="font-size:10.5px;font-family:monospace;font-weight:600;color:#16a34a;text-align:center;min-width:18px">'+fmtSp(mr.jc_hhad_lose)+'</span>'+spArrow(mr.jc_hhad_lose_flag)+'</span>';
      }
      ph += '</div>';
      ph += '<div style="display:flex;align-items:center;gap:8px;margin-left:auto">';
      ph += '<span class="cp-time">'+t+'</span>';
      ph += badge;
      ph += '</div>';
      if (manualOn) {
        ph += '<span class="cp-inputs"><input class="cp-inp-score" data-mid="'+mr.match_id+'" placeholder="比分 如3:1" size="8"> <input class="cp-inp-hf" data-mid="'+mr.match_id+'" placeholder="半全如胜胜" size="6"> <button class="cp-btn-save" data-mid="'+mr.match_id+'">Save</button></span>';
      }
      ph += '</div>';
    }
    ph += '</div><div class="cp-col cp-col-wide"><h4>待预测 ('+np.length+') <label class="cp-sel-all" style="font-weight:normal;font-size:12px;margin-left:8px;cursor:pointer"><input type="checkbox" class="cp-chk-all" onchange="var c=this.checked;document.querySelectorAll(\'.cp-chk-pend\').forEach(function(cb){cb.checked=c})"> 全选</label></h4>';
    if (np.length===0) ph += '<div class="cp-empty">无</div>';
    else for (var k=0;k<np.length;k++) {
      var p=np[k];
      ph += '<div class="cp-row cp-row-card" data-mid="'+p.match_id+'" style="cursor:pointer">';
      ph += '<input type="checkbox" class="cp-chk-pend" data-mid="'+p.match_id+'" style="margin-right:6px;cursor:pointer" onclick="event.stopPropagation()"' + (window._dataCollectedIds && window._dataCollectedIds[p.match_id] ? ' checked' : '') + '>';
      ph += '<span class="cp-mid">'+fmt(p.match_id)+'</span>';
      ph += '<span class="cp-teams">'+fmt(p.home)+' vs '+fmt(p.away)+'</span>';
      var _hasData = window._dataCollectedIds && window._dataCollectedIds[p.match_id];
      ph += '<span class="cp-status ' + (_hasData ? 'done' : 'wait') + '" style="margin-left:auto;' + (_hasData ? 'background:#dbeafe;color:#2563eb' : '') + '" data-mid="'+p.match_id+'">' + (_hasData ? '✓ 已采集' : '等待预测') + '</span>';
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
        if (!score) { alert("请输入比分"); return; }
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
            // ★ 失效其他面板缓存
            if (window.panelLoaded) {
              window.panelLoaded.matches = false;
              window.panelLoaded.fundamental = false;
              window.panelLoaded.featured = false;
              window.panelLoaded.plans = false;
            }
            logMsg("赛果已同步，切换导航查看", "#16a34a");

    var needResultRows = document.querySelectorAll(".cp-row-card[data-mid]");
    for (var ri=0; ri<needResultRows.length; ri++) {
      needResultRows[ri].onclick = function() {
        var mid = this.dataset.mid;
        var fundNav = document.querySelector('.nav-item[data-panel="fundamental"]');
        if (fundNav) fundNav.click();
        setTimeout(function() {
          var card = document.querySelector('.fa-card[data-mid="'+mid+'"]');
          if (card) {
            card.scrollIntoView({behavior: "smooth", block: "center"});
            if (window.toggleFaCard) window.toggleFaCard(card);
          }
        }, 800);
      };
    }
          }
        } catch(e) { logMsg("Save error: " + e, "#dc2626"); }
        this.disabled = false; this.textContent = "Save";
      };
    }

    // Bind "Wait predict" clickable badges
    var needPredictRows = document.querySelectorAll(".cp-row-card[data-mid]");
    for (var ri=0; ri<needPredictRows.length; ri++) {
      needPredictRows[ri].onclick = function() {
        var mid = this.dataset.mid;
        var fundNav = document.querySelector('.nav-item[data-panel="fundamental"]');
        if (fundNav) fundNav.click();
        setTimeout(function() {
          var card = document.querySelector('.fa-card[data-mid="'+mid+'"]');
          if (card) {
            card.scrollIntoView({behavior: "smooth", block: "center"});
            if (window.toggleFaCard) window.toggleFaCard(card);
          }
        }, 800);
      };
    }
  };
  window._renderPreview();

  // Console log loading
  try {
    var clogR = await fetch("/api/dashboard/console_log").then(function(d) { return d.json(); });
    var clog = document.getElementById("console-log");
    if (clogR.log) {
      var logLines = clogR.log.split("\n").filter(function(l){ return l.trim(); });
      clog.innerHTML = logLines.map(function(l) {
        var color = l.indexOf("[ERROR]")>=0 ? "#dc2626" : l.indexOf("ERROR")>=0 ? "#dc2626" : l.indexOf("OK:")>=0 ? "#16a34a" : "";
        var lineDiv = document.createElement("div");
        lineDiv.style.cssText = "padding:2px 0;font-size:12px;color:" + (color || "#6b7280");
        lineDiv.textContent = l;
        return lineDiv.outerHTML;
      }).join("");
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
        window.prevData = await fetch("/api/dashboard/matches_grouped").then(function(rr){return rr.json();});
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
        window.overviewData = await fetch("/api/dashboard/overview").then(function(rr){return rr.json();});
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
        // ★ 失效其他面板缓存，确保切过去时重新加载
        if (window.panelLoaded) {
          window.panelLoaded.matches = false;
          window.panelLoaded.fundamental = false;
          window.panelLoaded.plans = false;
          window.panelLoaded.featured = false;
        }
        // ★ 刷新 iframe（计划池 + 精选计划单）
        var planIframe = document.querySelector('#panel-plans iframe');
        if (planIframe) planIframe.src = '/static/plan.html?_t=' + Date.now();
        var featIframe = document.getElementById('featured-iframe');
        if (featIframe) featIframe.src = '/api/dashboard/featured?_t=' + Date.now();
        logMsg("全面板数据已同步，切换导航查看", "#16a34a");
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
    logMsg(isOn ? "手动录入模式 ON" : "手动录入模式 OFF", isOn ? "#2563eb" : "#6b7280");
    if (window._renderPreview) window._renderPreview();
    lucide.createIcons();
  }
  document.getElementById("btn-fetch-jczq").onclick = async () => {
    logMsg("正在从竞彩网获取比赛...", "#2563eb");
    try {
      const d = await fetch("/api/dashboard/action/fetch_jczq").then(r => r.json());
      if (d.logs && d.logs.length) d.logs.forEach(function(l) { logMsg(l, l.indexOf("ERROR")>=0 ? "#dc2626" : l.indexOf("新增")>=0 ? "#16a34a" : "#6b7280"); });
      else logMsg(d.msg || "获取完成", "#16a34a");
      // ★ 获取比赛后刷新相关面板（新比赛/赔率更新）
      if (window.panelLoaded) {
        window.panelLoaded.matches = false;
        window.panelLoaded.fundamental = false;
        window.panelLoaded.overview = false;
      }
      // 刷新控制台预览（待预测列表）
      try {
        var jczqPreview = await fetch("/api/dashboard/matches_grouped").then(function(rr){return rr.json();});
        window._consoleNeedP = [];
        for (var jgi=0; jgi<(jczqPreview.groups||[]).length; jgi++) {
          var jgms = jczqPreview.groups[jgi].matches;
          for (var jmi=0; jmi<jgms.length; jmi++) {
            var jm = jgms[jmi];
            if (!jm.actual_score && !jm.direction) { window._consoleNeedP.push(jm); }
          }
        }
        if (window._renderPreview) window._renderPreview();
      } catch(pe) { console.log("preview refresh error:", pe); }
      if (d.ok && d.new_matches && d.new_matches.length > 0) {
        showFetchJczqModal(d.new_matches, d.new_count);
      } else {
        logMsg(d.msg || "无新增比赛", "#6b7280");
        logMsg("比赛/基本面面板已同步，切换导航查看", "#16a34a");
      }
    } catch(e) { logMsg("获取失败: " + e.message, "#dc2626"); }
  };
  document.getElementById("btn-fetch-data").onclick = async () => {
    showFetchDataModal();
    lucide.createIcons();
  };
  document.getElementById("btn-refresh-odds").onclick = async function() {
    // Collect match IDs from need-results list
    var nr = window._consoleNeedR || [];
    var needResultIds = [];
    for (var ri = 0; ri < nr.length; ri++) {
      if (nr[ri].match_id) needResultIds.push(nr[ri].match_id);
    }
    if (needResultIds.length === 0) {
      logMsg("暂无需要更新赔率的比赛", "#d97706");
      return;
    }
    logMsg("正在刷新 " + needResultIds.length + " 场比赛的赔率...", "#2563eb");
    try {
      const d = await fetch("/api/dashboard/action/refresh_odds", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({match_ids: needResultIds})
      }).then(r => r.json());
      if (d.logs) d.logs.forEach(function(l) { logMsg(l, l.indexOf("失败")>=0 || l.indexOf("异常")>=0 ? "#dc2626" : "#6b7280"); });
      logMsg(d.msg || "赔率刷新完成", d.ok ? "#16a34a" : "#dc2626");
      // Refresh related panels
      if (window.panelLoaded) {
        window.panelLoaded.matches = false;
        window.panelLoaded.fundamental = false;
        window.panelLoaded.plans = false;
        window.panelLoaded.featured = false;
      }
      var planIframe = document.querySelector('#panel-plans iframe');
      if (planIframe) planIframe.src = '/static/plan.html?_t=' + Date.now();
      var featIframe = document.getElementById('featured-iframe');
      if (featIframe) featIframe.src = '/api/dashboard/featured?_t=' + Date.now();
      logMsg("相关面板已同步，切换导航查看", "#16a34a");
    } catch(e) {
      logMsg("刷新赔率失败: " + e.message, "#dc2626");
    }
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
                  logMsg(line, "#dc2626");
                } else if (line.indexOf("[DB]") >= 0 || line.indexOf("DDI") >= 0 || line.indexOf("Fit") >= 0 || line.indexOf("Rating") >= 0 || line.indexOf("History") >= 0 || line.indexOf("saved") >= 0) {
                  logMsg(line, "#6b7280");
                } else {
                  logMsg(line, "#6b7280");
                }
              }
            }
            // Stop polling when done
            if (pr.done) {
              clearInterval(pollTimer);
              logMsg("预测管道已完成，自动刷新相关面板...", "#16a34a");
              // Auto-refresh panels after prediction
              try {
                var refreshData = await fetch("/api/dashboard/matches_grouped").then(function(rr){return rr.json();});
                window._consoleNeedR = []; window._consoleNeedP = [];
                for (var gi=0; gi<(refreshData.groups||[]).length; gi++) {
                  var gms = refreshData.groups[gi].matches;
                  for (var mi=0; mi<gms.length; mi++) {
                    var mm = gms[mi];
                    if (mm.actual_score) continue;
                    if (!mm.direction) { window._consoleNeedP.push(mm); }
                    else if (mm.match_time) { window._consoleNeedR.push(mm); }
                  }
                }
                // Also refresh task cards
                window.overviewData = await fetch("/api/dashboard/overview").then(function(rr){return rr.json();});
                var r2 = overviewData;
                var s2 = r2.stats;
                document.getElementById("console-tasks").innerHTML =
                  '<div class="task-card" data-nav="matches" data-filter="pred"><div class="task-num red">' + r2.missing_results + '</div><div class="task-label">需补赛果</div></div>' +
                  '<div class="task-card" data-nav="matches" data-filter="wait"><div class="task-num yellow">' + (s2.total - s2.predicted) + '</div><div class="task-label">待预测</div></div>' +
                  '<div class="task-card" data-nav="matches" data-filter="done"><div class="task-num green">' + s2.scored + '</div><div class="task-label">可复盘</div></div>' +
                  '<div class="task-card" data-nav="plans"><div class="task-num gray">' + (r2.plan_info ? r2.plan_info.plan_count : "—") + '</div><div class="task-label">计划单</div></div>';
                document.querySelectorAll("#console-tasks .task-card").forEach(function(card) {
                  card.addEventListener("click", function() {
                    if (card.dataset.filter) { navigateToMatches(card.dataset.filter); }
                    else { var ni = document.querySelector('.nav-item[data-panel="' + card.dataset.nav + '"]'); if (ni) ni.click(); }
                  });
                });
                if (window._renderPreview) window._renderPreview();
                if (window.panelLoaded) window.panelLoaded.fundamental = false;
                // ★ 同时失效比赛和计划面板
                if (window.panelLoaded) {
                  window.panelLoaded.matches = false;
                  window.panelLoaded.plans = false;
                  window.panelLoaded.featured = false;
                }
                var pIframe = document.querySelector('#panel-plans iframe');
                if (pIframe) pIframe.src = '/static/plan.html?_t=' + Date.now();
                var fIframe = document.getElementById('featured-iframe');
                if (fIframe) fIframe.src = '/api/dashboard/featured?_t=' + Date.now();
                logMsg("相关面板已同步", "#16a34a");
              } catch(refreshErr) { console.log("auto-refresh error:", refreshErr); }
            }
          } catch(e2) {}
        }, 3000);
      }
    } catch(e) {
      logMsg("预测启动失败: " + e.message, "#dc2626");
    }
    btn.disabled = false;
    btn.textContent = origText;
  };
  document.getElementById("btn-gen-plan").onclick = async function() {
    logMsg("正在生成计划池...", "#2563eb");
    try {
      const d = await fetch("/api/dashboard/action/gen_plan").then(r => r.json());
      if (d.logs && d.logs.length) d.logs.forEach(function(l) { logMsg(l, l.indexOf("ERROR")>=0 ? "#dc2626" : "#6b7280"); });
      logMsg(d.msg || "生成完成", "#16a34a");
      if (window.panelLoaded) {
        window.panelLoaded.plans = false;
        window.panelLoaded.featured = false;
      }
      var planIframe = document.querySelector('#panel-plans iframe');
      if (planIframe) planIframe.src = '/static/plan.html?_t=' + Date.now();
      var featuredIframe = document.getElementById('featured-iframe');
      if (featuredIframe) featuredIframe.src = '/api/dashboard/featured?_t=' + Date.now();
      logMsg("计划池/精选计划单已刷新", "#16a34a");
    } catch(e) { logMsg("生成失败: " + e.message, "#dc2626"); }
  };
  // stat-card click to navigate (overview cards)
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

// ===== Fetch Data Modal =====
function showFetchDataModal() {
  if (!window._consoleNeedP || window._consoleNeedP.length === 0) {
    logMsg("暂无待采集比赛", "#d97706");
    return;
  }
  var overlay = document.getElementById("fetch-data-modal");
  var tbody = document.getElementById("fetch-data-list");
  var html = "";
  window._dataCollectedIds = {};
  for (var i = 0; i < window._consoleNeedP.length; i++) {
    var pm = window._consoleNeedP[i];
    html += '<tr><td><input type="checkbox" class="fd-chk" data-idx="' + i + '" checked></td><td>' + fmt(pm.match_id) + '</td><td>' + fmt(pm.home) + ' vs ' + fmt(pm.away) + '</td></tr>';
    window._dataCollectedIds[pm.match_id] = true;
  }
  tbody.innerHTML = html;
  overlay.style.display = "flex";
  document.getElementById("fd-select-all").onclick = function() {
    var checked = this.checked;
    tbody.querySelectorAll(".fd-chk").forEach(function(cb) { cb.checked = checked; });
    window._consoleNeedP.forEach(function(pm) { window._dataCollectedIds[pm.match_id] = checked; });
  };
  tbody.querySelectorAll(".fd-chk").forEach(function(cb) {
    cb.onchange = function() {
      var pm = window._consoleNeedP[parseInt(this.dataset.idx)];
      window._dataCollectedIds[pm.match_id] = this.checked;
    };
  });
  document.getElementById("fd-cancel").onclick = function() { overlay.style.display = "none"; };
  document.getElementById("fd-submit").onclick = submitFetchData;
  lucide.createIcons();
}

async function submitFetchData() {
  var checked = document.querySelectorAll("#fetch-data-list .fd-chk:checked");
  var selectedIds = [];
  for (var i = 0; i < checked.length; i++) {
    var pm = window._consoleNeedP[parseInt(checked[i].dataset.idx)];
    selectedIds.push(pm.match_id);
  }
  if (selectedIds.length === 0) { logMsg("请选择至少1场比赛", "#dc2626"); return; }
  document.getElementById("fetch-data-modal").style.display = "none";
  logMsg("正在采集 " + selectedIds.length + " 场比赛的数据...", "#2563eb");
  try {
    const d = await fetch("/api/dashboard/action/fetch_match_data", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({match_ids: selectedIds})
    }).then(r => r.json());
    if (d.logs) d.logs.forEach(function(l) { logMsg(l, l.indexOf("ERROR")>=0 ? "#dc2626" : "#6b7280"); });
    logMsg(d.msg || "采集完成", "#16a34a");
    if (window._renderPreview) window._renderPreview();
  } catch(e) { logMsg("采集失败: " + e.message, "#dc2626"); }
}

function showDataResultModal(data, updated) {
  var overlay = document.getElementById("fetch-data-modal");
  var tbody = document.getElementById("fetch-data-list");
  var html = "";
  for (var i = 0; i < data.length; i++) {
    var d = data[i];
    html += '<tr><td>' + fmt(d.match_id) + '</td><td>' + fmt(d.home) + ' vs ' + fmt(d.away) + '</td><td>' + (d.status || "✓") + '</td></tr>';
  }
  tbody.innerHTML = html;
  overlay.style.display = "flex";
  document.getElementById("fd-submit").style.display = "none";
  document.getElementById("fd-cancel").textContent = "关闭";
}

function showResultModal(results, updated) {
  var overlay = document.getElementById("result-modal");
  document.getElementById("rm-body").innerHTML = results.map(function(r) {
    return '<tr><td>' + fmt(r.match_id) + '</td><td>' + fmt(r.home) + ' vs ' + fmt(r.away) + '</td><td><strong>' + fmt(r.full_score) + '</strong>' + (r.half_full ? ' (' + fmt(r.half_full) + ')' : '') + '</td></tr>';
  }).join("");
  document.getElementById("rm-count").textContent = updated;
  overlay.style.display = "flex";
  document.getElementById("rm-close").onclick = function() {
    closeResultModal();
  };
  // Capture close via backdrop
  overlay.onclick = function(e) {
    if (e.target === overlay) closeResultModal();
  };
}

function closeResultModal() {
  document.getElementById("result-modal").style.display = "none";
  // Restore original footer (showResultModal depends on rm-close button)
  var foot = document.querySelector("#result-modal .result-modal-foot");
  foot.innerHTML = '<span class="rm-summary" id="rm-count"></span><button type="button" id="rm-close">确定</button>';
  document.getElementById("rm-heading").innerHTML = "&#9989; 结果";
  document.getElementById("rm-close").onclick = function() { closeResultModal(); };
  // If we have new results, navigate to fundamental panel
  var fundNav = document.querySelector('.nav-item[data-panel="fundamental"]');
  if (fundNav) fundNav.click();
}

function showFetchJczqModal(newMatches, count) {
  var overlay = document.getElementById("result-modal");
  var body = document.getElementById("rm-body");
  var head = document.getElementById("rm-heading");
  var foot = document.querySelector("#result-modal .result-modal-foot");
  head.innerHTML = "&#128268; 获取到 " + count + " 场新比赛";
  body.innerHTML = newMatches.map(function(m, i) {
    return '<tr><td><input type="checkbox" class="jczq-chk" data-idx="' + i + '" checked></td><td>' + fmt(m.match_id) + '</td><td>' + fmt(m.home) + ' vs ' + fmt(m.away) + '</td><td>' + fmt(m.match_time) + '</td></tr>';
  }).join("");
  // Show select-all + confirm in footer
  foot.innerHTML =
    '<span class="rm-summary"><label style="font-size:12px;cursor:pointer"><input type="checkbox" id="jczq-select-all" checked onchange="var c=this.checked;document.querySelectorAll(\'.jczq-chk\').forEach(function(cb){cb.checked=c})"> 全选/取消</label></span>' +
    '<div><button type="button" id="jczq-cancel">取消</button><button type="button" id="jczq-confirm" style="margin-left:8px;background:var(--cyan,#00e5ff);color:#000">确认</button></div>';
  overlay.style.display = "flex";
  document.getElementById("jczq-cancel").onclick = function() {
    closeResultModal();
  };
  document.getElementById("jczq-confirm").onclick = async function() {
    var checked = document.querySelectorAll(".jczq-chk:checked");
    var selectedIds = [];
    for (var ci = 0; ci < checked.length; ci++) {
      var idx = parseInt(checked[ci].dataset.idx);
      selectedIds.push(newMatches[idx].match_id);
    }
    if (selectedIds.length === 0) {
      logMsg("请至少选择一场比赛", "#dc2626");
      return;
    }
    logMsg("正在确认 " + selectedIds.length + " 场新比赛...", "#2563eb");
    try {
      const r = await fetch("/api/dashboard/action/confirm_jczq_matches", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({match_ids: selectedIds})
      }).then(res => res.json());
      if (r.logs) r.logs.forEach(function(l) { logMsg(l, l.indexOf("ERROR")>=0 ? "#dc2626" : "#6b7280"); });
      logMsg(r.msg || "确认完成", r.ok ? "#16a34a" : "#dc2626");
      document.getElementById("result-modal").style.display = "none";
      var foot = document.querySelector("#result-modal .result-modal-foot");
      foot.innerHTML = '<span class="rm-summary" id="rm-count"></span><button type="button" id="rm-close">确定</button>';
      document.getElementById("rm-heading").innerHTML = "&#9989; 结果";
      document.getElementById("rm-close").onclick = function() { closeResultModal(); };
      // Refresh related panels
      if (window.panelLoaded) {
        window.panelLoaded.matches = false;
        window.panelLoaded.fundamental = false;
        window.panelLoaded.overview = false;
      }
      try {
        var jczqPreview = await fetch("/api/dashboard/matches_grouped").then(function(rr){return rr.json();});
        window._consoleNeedP = [];
        for (var jgi=0; jgi<(jczqPreview.groups||[]).length; jgi++) {
          var jgms = jczqPreview.groups[jgi].matches;
          for (var jmi=0; jmi<jgms.length; jmi++) {
            var jm = jgms[jmi];
            if (!jm.actual_score && !jm.direction) { window._consoleNeedP.push(jm); }
          }
        }
        if (window._renderPreview) window._renderPreview();
      } catch(pe) { console.log("preview refresh error:", pe); }
      logMsg("比赛/基本面面板已同步，切换导航查看", "#16a34a");
    } catch(e) {
      logMsg("确认失败: " + e.message, "#dc2626");
    }
  };
  overlay.onclick = function(e) { if (e.target === overlay) closeResultModal(); };
}

function closeDataResultModal() {
  document.getElementById("fetch-data-modal").style.display = "none";
}

// ===== Log helper =====
function logMsg(msg, color) {
  var logDiv = document.getElementById("console-log");
  var line = document.createElement("div");
  line.style.cssText = "padding:2px 0;font-size:12px;color:" + (color || "#6b7280");
  var now = new Date();
  var ts = ("0" + now.getHours()).slice(-2) + ":" + ("0" + now.getMinutes()).slice(-2) + ":" + ("0" + now.getSeconds()).slice(-2);
  line.textContent = "[" + ts + "] " + msg;
  logDiv.appendChild(line);
  logDiv.scrollTop = logDiv.scrollHeight;
}

async function refreshConsoleAfterFetch() {
  try {
    window.overviewData = await fetch("/api/dashboard/overview").then(function(r) { return r.json(); });
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
    var previewData2 = await fetch("/api/dashboard/matches_grouped").then(function(d) { return d.json(); });
    window._consoleNeedR = []; window._consoleNeedP = [];
    for (var gi=0; gi<(previewData2.groups||[]).length; gi++) {
      var gms = previewData2.groups[gi].matches;
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

export { loadConsole, showFetchDataModal, submitFetchData, showDataResultModal, showResultModal, closeDataResultModal, closeResultModal, showFetchJczqModal, refreshConsoleAfterFetch };