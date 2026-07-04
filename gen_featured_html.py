import json, os

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "featured_data.json")

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html{background:transparent}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:transparent;color:#1f2937;padding:0 4px}

.round-section{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:14px 18px;margin-bottom:16px}
.round-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.round-header h2{font-size:14px;font-weight:600;color:#1f2937}
.round-header .next-stake{font-size:13px;color:#d97706;font-weight:600}
.round-dots{display:flex;gap:8px;align-items:center}
.dot{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;font-family:"SF Mono",Consolas,monospace;border:2px solid #e5e7eb;color:#9ca3af;background:#f9fafb;transition:.2s}
.dot.active{border-color:#d97706;color:#d97706;background:#fef3c7;box-shadow:0 0 8px rgba(217,119,6,.15)}
.dot.done{border-color:#d1d5db;color:#9ca3af;background:#f3f4f6}
.dot .mul{font-size:8px;color:#9ca3af;margin-top:1px}
.arr{color:#d1d5db;font-size:10px;margin:0 2px}
.round-ctrl{display:flex;gap:16px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
.round-ctrl label{font-size:11px;color:#6b7280;font-weight:500}
.round-ctrl .round-btn{width:26px;height:26px;border:1px solid #d1d5db;border-radius:4px;background:#f9fafb;cursor:pointer;font-size:14px;line-height:1;font-family:monospace;color:#374151}
.round-ctrl .round-btn:hover{background:#dbeafe;border-color:#2563eb;color:#2563eb}
.round-capital{font-size:13px;font-weight:700;font-family:monospace;color:#1f2937}

.hi{color:#d97706;font-weight:600}

.hist-section{background:linear-gradient(135deg,#f0fdf4,#f0f9ff);border:1px solid #bbf7d0;border-radius:8px;overflow:hidden;margin-bottom:16px}
.hist-section h3{font-size:13px;font-weight:600;color:#1f2937;padding:12px 16px;border-bottom:1px solid #e5e7eb}
.hist-table{width:100%;border-collapse:collapse;font-size:12px}
.hist-table th{padding:8px 12px;text-align:left;font-weight:600;color:#6b7280;background:#f9fafb;font-size:10px;white-space:nowrap;border-bottom:1px solid #e5e7eb}
.hist-table td{padding:7px 12px;border-bottom:1px solid #f3f4f6;color:#374151}
.hist-table tr:hover{background:rgba(255,255,255,.6)}
.hist-table .td-date{font-family:"SF Mono",Consolas,monospace;color:#1f2937;font-weight:500}
.hist-table .td-teams{font-size:11px;color:#1f2937;font-weight:500}
.hist-table .td-stake{font-family:"SF Mono",Consolas,monospace}
.hist-table .td-opt{position:relative;font-family:"SF Mono",Consolas,monospace;font-size:11px}
.hist-table .td-opt .opt-label{display:inline-block;padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px;font-weight:600;border:none;background:#cffafe;color:#0891b2;font-family:inherit;position:relative}
.hist-table .td-opt .opt-label:hover{background:#a5f3fc}
.hist-table .td-opt .opt-none{color:#9ca3af;font-size:10px}
.hist-table .td-opt .opt-detail{display:none;position:absolute;z-index:100;background:#fff;color:#1f2937;padding:8px 12px;border-radius:8px;font-size:12px;line-height:1.5;box-shadow:0 8px 24px rgba(0,0,0,.15);margin-top:4px;left:0;min-width:260px;border:1px solid #e5e7eb}
.hist-table .td-profit.up{color:#16a34a}.hist-table .td-profit.down{color:#dc2626}
.hist-table .td-cum{font-family:"SF Mono",Consolas,monospace;font-size:11px}.hist-table .td-cum.up{color:#16a34a}.hist-table .td-cum.down{color:#dc2626}
.hist-table .td-result{text-align:center;font-weight:700;font-size:14px}
.tag{font-size:9px;padding:1px 6px;border-radius:3px;white-space:nowrap;font-weight:600}
.tag.dir{background:#dbeafe;color:#2563eb}
.tag.pk{background:#cffafe;color:#0891b2;border:1px solid #a5f3fc}
.tag.hf{background:#fef3c7;color:#d97706}
.tag.active{background:#fef3c7;color:#d97706;font-weight:600;font-size:10px}
"""

JS_LOGIC = r"""
const DATA = __DATA__;

function typeTag(t) {
  var m = {'方向':'dir','半全场':'hf'};
  var b = t.replace('打包','');
  var cls = m[b] || '';
  if (t.indexOf('打包')>=0) return '<span class="tag pk">'+t.replace('打包','')+'</span>';
  return '<span class="tag '+cls+'">'+t+'</span>';
}
function legOpts(leg) {
  var cps = leg.comps || [leg.odds];
  var opts = leg.option.split('/');
  var hasRang = leg.type.indexOf('打包')>=0 && (opts[0].indexOf('让')>=0 || (opts[1]||'').indexOf('让')>=0);
  var s = '';
  for (var o=0; o<opts.length; o++) {
    var po = opts[o];
    if (hasRang && po == '平') po = '让平';
    if (hasRang && po == '负') po = '让负';
    var od = cps.length > o ? cps[o] : leg.odds;
    s += (o>0 ? '+' : '') + po + '(' + od.toFixed(2) + ')';
  }
  return '<span class="hi">'+s+'</span>';
}
function fmt(v,d) { return (v===null||v===undefined||v==='') ? (d||'-') : v; }
function pc(v) { return (v*100).toFixed(1)+'%'; }
function fm(v) { return v>=0 ? '+'+v.toLocaleString() : v.toLocaleString(); }

function legShortName(leg) {
  var match = leg.match || '';
  var home = match.split(' vs ')[0] || match;
  return home.length > 4 ? home.slice(0,4) : home;
}
function legHcpStr(mid) {
  var m = DATA.matches[mid];
  if (!m) return '';
  var h = m.handicap || 0;
  return h > 0 ? '+'+h : (h < 0 ? String(h) : '');
}
function optHTML(s, dynStake) {
  if (!s || !s.pick) return '-';
  var l1 = s.pick.l1, l2 = s.pick.l2;
  var c1 = l1.comps || [l1.odds];
  var c2 = l2.comps || [l2.odds];
  var hasPack = c1.length > 1 || c2.length > 1;
  if (!hasPack) return '<span class="opt-none">无需优化</span>';
  var pathOdds = [];
  var path_i1 = [];
  var path_i2 = [];
  for (var i=0; i<c1.length; i++) {
    for (var j=0; j<c2.length; j++) {
      pathOdds.push(c1[i]*c2[j]);
      path_i1.push(i);
      path_i2.push(j);
    }
  }
  if (pathOdds.length <= 1) return '<span class="opt-none">无需优化</span>';
  var totalUnits = Math.floor((dynStake || s.stake) / 2);
  if (totalUnits <= 0) return '<span class="opt-none">-</span>';
  var invSum = 0;
  for (var p=0; p<pathOdds.length; p++) invSum += 1/pathOdds[p];
  var units = [];
  var allocated = 0;
  for (var p=0; p<pathOdds.length; p++) {
    var u = Math.round(totalUnits / pathOdds[p] / invSum);
    if (p === pathOdds.length-1) u = totalUnits - allocated;
    units.push(u);
    allocated += u;
  }
  var uid = 'opt-' + s.date.replace(/-/g,'');
  var mid1 = l1.mid ? l1.mid.slice(-3) : '';
  var mid2 = l2.mid ? l2.mid.slice(-3) : '';
  var h1 = legShortName(l1);
  var h2 = legShortName(l2);
  var hcp1 = legHcpStr(l1.mid);
  var hcp2 = legHcpStr(l2.mid);
  var l1opts = l1.option.split('/');
  var l2opts = l2.option.split('/');
  var hasRang1 = l1.type.indexOf('打包')>=0 && (l1opts[0].indexOf('让')>=0 || (l1opts[1]||'').indexOf('让')>=0);
  var hasRang2 = l2.type.indexOf('打包')>=0 && (l2opts[0].indexOf('让')>=0 || (l2opts[1]||'').indexOf('让')>=0);
  function fixOpt(o, hr) {
    if (hr && o === '平') return '让平';
    if (hr && o === '负') return '让负';
    return o;
  }
  var tbl = '<table style="border-collapse:collapse;font-size:12px;width:100%"><thead><tr style="border-bottom:1px solid #e5e7eb;background:#f8fafc">';
  tbl += '<th style="text-align:left;padding:4px 6px;font-weight:600;color:#64748b;font-size:10px">选单</th>';
  tbl += '<th style="text-align:right;padding:4px 6px;font-weight:600;color:#64748b;font-size:10px">注数</th>';
  tbl += '<th style="text-align:right;padding:4px 6px;font-weight:600;color:#64748b;font-size:10px">理论奖金</th></tr></thead><tbody>';
  for (var p=0; p<pathOdds.length; p++) {
    var opt1 = fixOpt(l1opts[path_i1[p] < l1opts.length ? path_i1[p] : 0], hasRang1);
    var opt2 = fixOpt(l2opts[path_i2[p] < l2opts.length ? path_i2[p] : 0], hasRang2);
    var hcpStr1 = '('+(hcp1||'')+opt1+')';
    var hcpStr2 = '('+(hcp2||'')+opt2+')';
    var ret = (units[p] * pathOdds[p]).toFixed(0);
    tbl += '<tr style="border-bottom:1px solid #f3f4f6">';
    tbl += '<td style="padding:4px 6px;line-height:1.6;font-size:12px"><div>'+mid1+' '+h1+' '+hcpStr1+'</div><div>'+mid2+' '+h2+' '+hcpStr2+'</div></td>';
    tbl += '<td style="text-align:right;padding:4px 6px;font-family:monospace;font-size:13px;font-weight:600">'+units[p]+'</td>';
    tbl += '<td style="text-align:right;padding:4px 6px;font-family:monospace;font-size:13px;font-weight:600;color:#16a34a">'+ret+'</td>';
    tbl += '</tr>';
  }
  tbl += '</tbody></table>';
  var detail = '<div class="opt-detail" id="'+uid+'">'+tbl+'</div>';
  return "<span class=\"opt-label\" onmouseenter=\"showOpt(this,'"+uid+"')\" onmouseleave=\"hideOpt(this,'"+uid+"')\">奖金优化</span>" + detail;
}

function showOpt(el, id) {
  var d = document.getElementById(id);
  if (d) { d.style.display = 'block'; var r = d.getBoundingClientRect(); if (r.right > window.innerWidth) d.style.right = '0'; }
}
function hideOpt(el, id) {
  document.getElementById(id).style.display = 'none';
}

var seq = DATA.sequence;
var strat = DATA.strategy;
var cur = DATA.current;

// Round indicator + strategy params
var _simRound = 0;
var _maxRounds = DATA.strategy.max_rounds;

function changeMaxRounds(delta) {
  var inp = document.getElementById('sim-rounds');
  if (!inp) return;
  var v = parseInt(inp.value) || 6;
  v = Math.max(2, Math.min(12, v + delta));
  inp.value = v;
  onMaxRoundsChange(v);
}

function onMaxRoundsChange(val) {
  var v = parseInt(val) || 6;
  v = Math.max(2, Math.min(12, v));
  var inp = document.getElementById('sim-rounds');
  if (inp) inp.value = v;
  renderSim();
  renderPlanTable();
}

function renderSim() {
  var seq = DATA.sequence;
  var strat = DATA.strategy;

  // Read current values from DOM first (for cr calculation + display)
  var maxRounds = parseInt(document.getElementById('sim-rounds') ? document.getElementById('sim-rounds').value : _maxRounds) || _maxRounds || strat.max_rounds;
  var baseStake = parseFloat(document.getElementById('sim-stake') ? document.getElementById('sim-stake').value : strat.base_stake) || strat.base_stake;
  var mults = [];
  if (document.querySelectorAll) {
    document.querySelectorAll('.sim-mult').forEach(function(inp){ mults.push(parseFloat(inp.value) || 1); });
  }
  if (mults.length === 0) mults = strat.multipliers;

  // Calculate current round (forward pass through actual history)
  var cr = 1;
  for (var fi=0; fi<seq.length; fi++) {
    var fs = seq[fi];
    if (!fs.pick || fs.result === 'no_pick') continue;
    if (fs.result === 'hit') { cr = 1; }
    else if (fs.result === 'miss') { cr++; if (cr > maxRounds) cr = maxRounds; }
  }

  // Calculate required capital
  var requiredCapital = 0;
  for (var ri = 0; ri < maxRounds; ri++) {
    var rm = mults[ri] !== undefined ? mults[ri] : (mults[mults.length-1] || 1);
    requiredCapital += Math.round(baseStake * rm);
  }

  var rnd = '';

  // Title: 计划参数设置
  rnd += '<div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #e5e7eb">计划参数设置</div>';

  // Row 1: 基础投注额 + 所需本金 + 翻倍系数设置
  rnd += '<div style="display:flex;gap:12px;align-items:center;margin-bottom:10px;flex-wrap:wrap">';
  rnd += '<label style="font-size:11px;color:#6b7280;font-weight:500">基础投注额</label>';
  rnd += '<input type="number" id="sim-stake" value="'+baseStake+'" min="10" step="10" style="width:80px;padding:4px 6px;border:1px solid #d1d5db;border-radius:4px;font-size:12px;font-family:monospace" oninput="renderSim();renderPlanTable()">';
  rnd += '<span style="font-size:11px;color:#9ca3af">所需本金:</span>';
  rnd += '<span class="round-capital">'+requiredCapital.toLocaleString()+'</span>';
  rnd += '<span style="color:#d1d5db;font-size:12px">|</span>';
  rnd += '<label style="font-size:11px;color:#6b7280;font-weight:500">翻倍系数设置</label>';
  for (var i=0; i<maxRounds; i++) {
    var mv = mults[i] !== undefined ? mults[i] : 1;
    rnd += '<input type="number" class="sim-mult" value="'+mv+'" data-idx="'+i+'" min="0" step="1" style="width:44px;text-align:center;padding:4px 3px;border:1px solid #d1d5db;border-radius:4px;font-size:11px;font-family:monospace" oninput="renderSim();renderPlanTable()">';
  }
  rnd += '</div>';

  // Row 2: 调节总轮次 + 当前轮次 + 圆点
  rnd += '<div class="round-ctrl">';
  rnd += '<label>调节总轮次</label>';
  rnd += '<div style="display:flex;align-items:center;gap:4px">';
  rnd += '<button class="round-btn" onclick="changeMaxRounds(-1)">-</button>';
  rnd += '<input type="number" id="sim-rounds" value="'+maxRounds+'" min="2" max="12" style="width:40px;text-align:center;padding:4px 3px;border:1px solid #d1d5db;border-radius:4px;font-size:12px;font-family:monospace" onchange="onMaxRoundsChange(this.value)">';
  rnd += '<button class="round-btn" onclick="changeMaxRounds(1)">+</button>';
  rnd += '</div>';
  rnd += '<span style="color:#d1d5db">|</span>';
  rnd += '<span style="font-size:13px;font-weight:600;color:#1f2937">当前：第 '+cr+' 轮</span>';
  rnd += '<span class="arr" style="margin:0 4px">→</span>';
  rnd += '<div class="round-dots" style="display:inline-flex">';
  for (var i=0; i<maxRounds; i++) {
    var rm = mults[i] !== undefined ? mults[i] : (mults[mults.length-1] || 1);
    var cls = '';
    if (i+1 < cr) cls = 'done';
    else if (i+1 == cr) cls = 'active';
    rnd += '<div class="dot '+cls+'">'+rm+'<span class="mul">x</span></div>';
    if (i < maxRounds-1) rnd += '<span class="arr">→</span>';
  }
  rnd += '</div>';
  rnd += '</div>';

  document.getElementById('round-section').innerHTML = rnd;
}

function renderPlanTable() {
  var base = parseFloat(document.getElementById('sim-stake') ? document.getElementById('sim-stake').value : 1000) || 1000;
  var m = [];
  document.querySelectorAll('.sim-mult').forEach(function(inp){ m.push(parseFloat(inp.value) || 1); });
  if (m.length === 0) { m = DATA.strategy.multipliers; }
  var seq = DATA.sequence;
  var maxRoundsPT = parseInt(document.getElementById('sim-rounds') ? document.getElementById('sim-rounds').value : _maxRounds) || _maxRounds || m.length;

  // Forward pass: calculate round AND cumulative for each entry (chronological order)
  var entryRound = [];
  var entryProfit = [];
  var entryCum = [];
  var cr = 1;
  var runningCum = 0;
  for (var fi=0; fi<seq.length; fi++) {
    var fs = seq[fi];
    if (!fs.pick || fs.result === 'no_pick') { entryRound.push(-1); entryProfit.push(0); entryCum.push(null); continue; }
    entryRound.push(cr);
    var rnd = cr;
    var mu = m[rnd-1] || m[m.length-1] || 1;
    var st = Math.round(base * mu);
    // Calculate profit for this entry
    var prof = 0;
    if (fs.result === 'pending') { prof = 0; }
    else if (fs.result === 'hit') { prof = Math.round(st * (fs.pick.opt_odds || 2.0)) - st; }
    else if (fs.result === 'miss') { prof = -st; }
    entryProfit.push(prof);
    if (fs.result === 'pending') { entryCum.push(null); }
    else { runningCum += prof; entryCum.push(runningCum); }
    // Update round for next entry
    if (fs.result === 'hit') { cr = 1; }
    else if (fs.result === 'miss') { cr++; if (cr > maxRoundsPT) cr = maxRoundsPT; }
  }

  // Render table (backward — newest first)
  var hb = '';
  for (var i=seq.length-1; i>=0; i--) {
    var s = seq[i];
    if (!s.pick || s.result === 'no_pick') continue;
    var rnd = entryRound[i];
    var mult = m[rnd-1] || m[m.length-1] || 1;
    var stk = Math.round(base * mult);
    var prof = entryProfit[i];
    var cum = entryCum[i];
    var resIcon = s.result==='hit' ? '<span style="color:#16a34a">✓</span>' : (s.result==='miss' ? '<span style="color:#dc2626">✗</span>' : (s.result==='pending' ? '<span style="color:#eab308">等待</span>' : '-'));
    var teams = s.pick ? s.pick.l1.mid.slice(-3)+' '+s.pick.l1.match+' '+typeTag(s.pick.l1.type)+' '+legOpts(s.pick.l1)+' x '+s.pick.l2.mid.slice(-3)+' '+s.pick.l2.match+' '+typeTag(s.pick.l2.type)+' '+legOpts(s.pick.l2) : '-';
    var odds = s.pick ? String(s.pick.opt_odds) : '-';
    var sc = '';
    if (s.pick) {
      var m1 = DATA.matches[s.pick.l1.mid];
      var m2 = DATA.matches[s.pick.l2.mid];
      if (m1 && m1.actual_score) sc += m1.actual_score.replace('-',':') + (m1.half_full ? '('+m1.half_full+')' : '');
      if (m2 && m2.actual_score) sc += ' + ' + m2.actual_score.replace('-',':') + (m2.half_full ? '('+m2.half_full+')' : '');
    }
    if (s.result === 'pending') {
      hb += '<tr style="background:rgba(254,243,199,.25)"><td class="td-date">'+s.date+'</td><td class="td-teams">'+teams+'</td><td style="font-family:monospace">'+odds+'</td><td class="td-opt">'+optHTML(s, stk)+'</td><td style="font-family:monospace;font-size:11px">'+(sc||'-')+'</td><td class="td-stake">'+stk.toLocaleString()+'</td><td class="td-result">'+resIcon+'</td><td class="td-profit"><span style="color:#eab308">等待</span></td><td class="td-cum"><span style="color:#eab308">等待</span></td></tr>';
      continue;
    }
    var profitCls = prof>=0 ? 'up' : 'down';
    var cumCls = cum>=0 ? 'up' : 'down';
    hb += '<tr><td class="td-date">'+s.date+'</td><td class="td-teams">'+teams+'</td><td style="font-family:monospace">'+odds+'</td><td class="td-opt">'+optHTML(s, stk)+'</td><td style="font-family:monospace;font-size:11px">'+(sc||'-')+'</td><td class="td-stake">'+stk.toLocaleString()+'</td><td class="td-result">'+resIcon+'</td><td class="td-profit '+profitCls+'">'+(prof>=0?'+':'')+prof.toLocaleString()+'</td><td class="td-cum '+cumCls+'">'+(cum>=0?'+':'')+cum.toLocaleString()+'</td></tr>';
  }
  document.getElementById('hist-body').innerHTML = hb;
}

// Initial render
renderSim();
renderPlanTable();

"""

def build():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    html = '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n'
    html += '<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    html += '<title>精选计划单</title>\n<style>\n'
    html += CSS
    html += '\n</style>\n</head>\n<body>\n\n'

    html += '  <div class="round-section" id="round-section"></div>\n'
    html += '  <div class="hist-section">\n'
    html += '    <h3>投注序列</h3>\n'
    html += '    <div style="overflow-x:auto"><table class="hist-table"><thead><tr>\n'
    html += '      <th>日期</th><th>比赛</th><th>优化赔率</th><th>奖金优化</th><th>赛果</th><th>金额</th><th style="text-align:center">结果</th><th>盈亏</th><th>累计</th>\n'
    html += '    </tr></thead><tbody id="hist-body"></tbody></table></div>\n'
    html += '  </div>\n\n'

    html += '<script>\n'
    html += JS_LOGIC.replace('__DATA__', json.dumps(data, ensure_ascii=False))
    html += '\n</script>\n</body>\n</html>'

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'featured.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'featured.html written ({len(html)} bytes)')

build()
