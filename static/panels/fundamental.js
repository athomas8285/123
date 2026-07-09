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
function spArrow(flag) {
  if (flag === 1) return '<span style="color:#ef5350">↑</span>';
  if (flag === -1) return '<span style="color:#16a34a">↓</span>';
  return '';
}

function fmtHcp(v) {
  if (v === null || v === undefined || v === "" || v === 0) return "-";
  var n = Number(v);
  return n > 0 ? "+" + String(n) : String(n);
}



function fmt(v, d) { return (v === null || v === undefined || v === '') ? (d || '-') : v; }
function fmt1(v, d) { if (v === null || v === undefined || v === '') return d || '-'; var n = Number(v); return isNaN(n) ? (d || '-') : n.toFixed(1); }

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
    var t = m.display_date || m.time || "";
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
        var hcpVal = a.handicap;
        var hcpS = hcpVal !== "" && hcpVal != null ? (hcpVal > 0 ? "+" + hcpVal : String(hcpVal)) : "-";
        h += '<div class="fa-c-odds"><div class="odds-rows">';
        var spAllMissing = a.sp_home == null && a.sp_draw == null && a.sp_away == null;
        if (spAllMissing) {
          h += '<div class="odds-row"><span class="or-label">(0)</span><span class="fa-c-sp-missing">⚠未开售</span></div>';
        } else {
          h += '<div class="odds-row"><span class="or-label">(0)</span><span class="og-item og-sp-h">' + fmtSp(a.sp_home) + '</span>' + spArrow(a.sp_home_flag) + '<span class="og-item og-sp-d">' + fmtSp(a.sp_draw) + '</span>' + spArrow(a.sp_draw_flag) + '<span class="og-item og-sp-a">' + fmtSp(a.sp_away) + '</span>' + spArrow(a.sp_away_flag) + '</div>';
        }
        h += '<div class="odds-row"><span class="or-label">(' + hcpS + ')</span><span class="og-item og-sp-h">' + fmtSp(a.hh_win) + '</span>' + spArrow(a.hh_win_flag) + '<span class="og-item og-sp-d">' + fmtSp(a.hh_draw) + '</span>' + spArrow(a.hh_draw_flag) + '<span class="og-item og-sp-a">' + fmtSp(a.hh_lose) + '</span>' + spArrow(a.hh_lose_flag) + '</div>';
        h += '</div></div>';
        h += '<div class="fa-c-dir">' + faDirBadge(a.direction, "") + '</div>';
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
        h += '<div class="fa-c-odds"><div class="odds-rows">';
        if (spAllMissing) {
          h += '<div class="odds-row"><span class="or-label">(0)</span><span class="fa-c-sp-missing">⚠未开售</span></div>';
        } else {
          h += '<div class="odds-row"><span class="or-label">(0)</span><span class="og-item og-sp-h">' + fmtSp(a.sp_home) + '</span>' + spArrow(a.sp_home_flag) + '<span class="og-item og-sp-d">' + fmtSp(a.sp_draw) + '</span>' + spArrow(a.sp_draw_flag) + '<span class="og-item og-sp-a">' + fmtSp(a.sp_away) + '</span>' + spArrow(a.sp_away_flag) + '</div>';
        }
        var hcp = a.handicap;
        var hcpStr = hcp !== "" && hcp != null ? (hcp > 0 ? "+" + hcp : String(hcp)) : "-";
        h += '<div class="odds-row"><span class="or-label">(' + hcpStr + ')</span><span class="og-item og-sp-h">' + fmtSp(a.hh_win) + '</span>' + spArrow(a.hh_win_flag) + '<span class="og-item og-sp-d">' + fmtSp(a.hh_draw) + '</span>' + spArrow(a.hh_draw_flag) + '<span class="og-item og-sp-a">' + fmtSp(a.hh_lose) + '</span>' + spArrow(a.hh_lose_flag) + '</div>';
        h += '</div></div>';
        h += '<div class="fa-c-dir">' + faDirBadge(a.direction, "") + '</div>';
        h += '<div class="fa-c-fit-wrap"><span class="fa-c-predicting">预测中</span></div>';
        h += '<div class="fa-c-expand">▼</div>';
        h += '</div>';
      }
      h += '<div class="fa-expand" onclick="event.stopPropagation()">';
      // 正在预测：新展开内容
      if (hasDir && !hasScore) {
        // 1. Pills
        var g2 = a.top2_goals || [];
        var h2 = a.top2_hf || [];
        var s3 = a.top3_scores || [];
        h += '<div class="fa-exp-pills">';
        h += '<div class="fa-exp-pill"><span class="pil-icon">⚽</span><span class="pil-label">总进球</span><span class="pil-value">' + (g2.length ? g2.join(" / ") : '——') + '</span></div>';
        h += '<div class="fa-exp-pill"><span class="pil-icon">🔄</span><span class="pil-label">半全场</span><span class="pil-value">' + (h2.length ? h2.join(" / ") : '——') + '</span></div>';
        h += '<div class="fa-exp-pill"><span class="pil-icon">🎯</span><span class="pil-label">比分</span><span class="pil-value">' + (s3.length ? s3.join(" / ") : '——') + '</span></div>';
        h += '</div>';
        // 2. Three-column grid
        h += '<div class="fa-exp-grid">';
        // A: Lambda chart
        var lh = a.lambda_h || 0;
        var la = a.lambda_a || 0;
        var ld = a.lambda_diff || 0;
        var maxLam = Math.max(lh, la, 0.5);
        h += '<div class="fa-exp-chart"><div class="ch-title">λ 对比</div>';
        h += '<div class="ch-sub"><span style="color:#fbbf24;font-weight:600">Δ ' + (ld>=0?'+':'') + ld.toFixed(4) + '</span></div>';
        h += '<div class="chart-svg-wrap"><svg viewBox="0 0 260 130">';
        for (var si=0;si<5;si++){var gy=18+si*23;h+='<line x1="36" y1="'+gy+'" x2="240" y2="'+gy+'" stroke="#1e293b" stroke-dasharray="3,3" stroke-width="1"/>';}
        h += '<text x="34" y="22" text-anchor="end" fill="#64748b" font-size="9">'+maxLam.toFixed(1)+'</text>';
        h += '<text x="34" y="45" text-anchor="end" fill="#64748b" font-size="9">'+(maxLam*3/4).toFixed(1)+'</text>';
        h += '<text x="34" y="68" text-anchor="end" fill="#64748b" font-size="9">'+(maxLam/2).toFixed(1)+'</text>';
        h += '<text x="34" y="91" text-anchor="end" fill="#64748b" font-size="9">'+(maxLam/4).toFixed(1)+'</text>';
        h += '<text x="34" y="114" text-anchor="end" fill="#64748b" font-size="9">0.0</text>';
        var lhH = Math.max(3, lh/maxLam*96);
        var laH = Math.max(3, la/maxLam*96);
        h += '<rect x="70" y="'+(110-lhH)+'" width="44" height="'+lhH+'" rx="3" fill="#10b981" opacity=".85"/>';
        h += '<text x="92" y="'+(104-lhH)+'" text-anchor="middle" fill="#10b981" font-size="10" font-weight="600">'+lh.toFixed(3)+'</text>';
        h += '<rect x="150" y="'+(110-laH)+'" width="44" height="'+laH+'" rx="3" fill="#ef4444" opacity=".85"/>';
        h += '<text x="172" y="'+(104-laH)+'" text-anchor="middle" fill="#ef4444" font-size="10" font-weight="600">'+la.toFixed(3)+'</text>';
        h += '<text x="92" y="128" text-anchor="middle" fill="#94a3b8" font-size="10">入主</text><text x="172" y="128" text-anchor="middle" fill="#94a3b8" font-size="10">入客</text>';
        h += '</svg></div></div>';
                                        // B: Physical vs Market probability
        var phys = a.physical || {};
        var mkt = a.p_market || {};
        var ph = (phys.home_win||0)*100;
        var pd = (phys.draw||0)*100;
        var pa = (phys.away_win||0)*100;
        var mh = (mkt.home_win||0)*100;
        var md = (mkt.draw||0)*100;
        var ma = (mkt.away_win||0)*100;
        var hasMkt = mh>0 || md>0 || ma>0;
        h += '<div class="fa-exp-chart"><div class="ch-title">物理概率' + (hasMkt ? ' vs 市场' : '') + '</div>';
        h += '<div class="chart-svg-wrap"><svg viewBox="0 0 260 130">';
        var maxV = hasMkt ? Math.max(ph, pd, pa, mh, md, ma, 10) : Math.max(ph, pd, pa, 10);
        for (var bi=0;bi<5;bi++){var by=18+bi*23;h+='<line x1="36" y1="'+by+'" x2="240" y2="'+by+'" stroke="#1e293b" stroke-dasharray="3,3" stroke-width="1"/>';}
        h += '<text x="34" y="22" text-anchor="end" fill="#64748b" font-size="9">'+maxV.toFixed(0)+'%</text>';
        h += '<text x="34" y="45" text-anchor="end" fill="#64748b" font-size="9">'+(maxV*3/4).toFixed(0)+'%</text>';
        h += '<text x="34" y="68" text-anchor="end" fill="#64748b" font-size="9">'+(maxV/2).toFixed(0)+'%</text>';
        h += '<text x="34" y="91" text-anchor="end" fill="#64748b" font-size="9">'+(maxV/4).toFixed(0)+'%</text>';
        h += '<text x="34" y="114" text-anchor="end" fill="#64748b" font-size="9">0%</text>';
        var barMax = Math.max(maxV, 1);
        function barH(v) { return Math.max(3, v/barMax*96); }
        var phH = barH(ph); var pdH = barH(pd); var paH = barH(pa);
        h += '<rect x="60" y="'+(110-phH)+'" width="28" height="'+phH+'" rx="3" fill="#4ade80" opacity=".85"/>';
        h += '<text x="74" y="'+(104-phH)+'" text-anchor="middle" fill="#4ade80" font-size="9" font-weight="600">'+ph.toFixed(0)+'%</text>';
        h += '<rect x="102" y="'+(110-pdH)+'" width="28" height="'+pdH+'" rx="3" fill="#60a5fa" opacity=".85"/>';
        h += '<text x="116" y="'+(104-pdH)+'" text-anchor="middle" fill="#60a5fa" font-size="9" font-weight="600">'+pd.toFixed(0)+'%</text>';
        h += '<rect x="144" y="'+(110-paH)+'" width="28" height="'+paH+'" rx="3" fill="#ef4444" opacity=".85"/>';
        h += '<text x="158" y="'+(104-paH)+'" text-anchor="middle" fill="#ef4444" font-size="9" font-weight="600">'+pa.toFixed(0)+'%</text>';
        if (hasMkt) {
          var mhH = barH(mh); var mdH = barH(md); var maH = barH(ma);
          h += '<rect x="60" y="'+(110-mhH)+'" width="28" height="'+mhH+'" rx="3" fill="none" stroke="#4ade80" stroke-width="2" stroke-dasharray="4,2" opacity=".7"/>';
          h += '<rect x="102" y="'+(110-mdH)+'" width="28" height="'+mdH+'" rx="3" fill="none" stroke="#60a5fa" stroke-width="2" stroke-dasharray="4,2" opacity=".7"/>';
          h += '<rect x="144" y="'+(110-maH)+'" width="28" height="'+maH+'" rx="3" fill="none" stroke="#ef4444" stroke-width="2" stroke-dasharray="4,2" opacity=".7"/>';
        }
        h += '<text x="74" y="128" text-anchor="middle" fill="#94a3b8" font-size="10">主</text><text x="116" y="128" text-anchor="middle" fill="#94a3b8" font-size="10">平</text><text x="158" y="128" text-anchor="middle" fill="#94a3b8" font-size="10">客</text>';
        h += '</svg></div></div>';
        h += '</div>'; // end grid
      } else {
        // 已完赛：保持原有展开内容
        var goals = a.top2_goals || [];
        var hf2 = a.top2_hf || [];
        var scores = a.top3_scores || [];
        if (goals.length || hf2.length || scores.length) {
          h += '<div class="fa-exp-pills">';
          if (goals.length) h += '<div class="fa-exp-pill"><span class="pil-icon">⚽</span><span class="pil-label">总进球</span><span class="pil-value">' + goals.join(" / ") + '</span></div>';
          if (hf2.length) h += '<div class="fa-exp-pill"><span class="pil-icon">🔄</span><span class="pil-label">半全场</span><span class="pil-value">' + hf2.join(" / ") + '</span></div>';
          if (scores.length) h += '<div class="fa-exp-pill"><span class="pil-icon">🎯</span><span class="pil-label">比分</span><span class="pil-value">' + scores.join(" / ") + '</span></div>';
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
      }
      h += '</div>';
      h += '</div>';
    }
    h += '</div></div>';
  }
  document.getElementById("fundamental-content").innerHTML = h || '<div class="empty">暂无数据</div>';
  lucide.createIcons();
}
export { loadFundamental, toggleFaCard, toggleFaDateGroup };
