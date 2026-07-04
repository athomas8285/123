#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen_plan_html.py V4.0 - 计划池 (日期切换 + top-5 + 命中判断 + 基本面)"""

import json, os, sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

CSS = r"""
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#f5f6f8;--surface:#fff;--s2:#f0f1f4;--t1:#1a1d26;--t2:#5a6072;--t3:#9ca3af;--yw:#eab308;--gr:#16a34a;--rd:#dc2626;--go:#d97706;--bl:#2563eb;--cy:#0891b2;--pu:#7c3aed;--bd:rgba(0,0,0,.08);--mono:"SF Mono",Consolas,monospace;--sans:"Inter","SF Pro","Microsoft YaHei",sans-serif}
body{font-family:var(--sans);background:var(--bg);color:var(--t1);min-height:100vh}
.wrap{padding:16px 20px 40px}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.topbar h1{font-size:18px;font-weight:700}
.date-select{padding:4px 8px;font-size:11px;border:1px solid var(--bd);border-radius:5px;background:var(--surface);color:var(--t1);font-family:var(--sans);cursor:pointer;outline:none}
.date-select:focus{border-color:var(--bl)}
.stats{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.stat-card{padding:6px 12px;background:var(--surface);border:1px solid var(--bd);border-radius:6px;font-size:11px;color:var(--t2);display:flex;align-items:center;gap:6px}
.stat-card .sc-num{font-size:15px;font-weight:700;color:var(--t1);font-family:var(--mono)}
.sc-num.gr{color:var(--gr)}.sc-num.go{color:var(--go)}.sc-num.cy{color:var(--cy)}.sc-num.rd{color:var(--rd)}.sc-num.t3{color:var(--t3)}
.cols{display:flex;gap:16px;align-items:flex-start}.summary-section{margin:16px 0}.summary-cards{display:flex;gap:8px;flex-wrap:wrap}
.col-left{width:380px;flex-shrink:0}
.col-right{flex:1;min-width:0}
@media(max-width:768px){.cols{flex-direction:column}.col-left{width:100%}}
.top-pick{background:linear-gradient(135deg,rgba(22,163,74,.06),rgba(8,145,178,.04));border:1px solid rgba(22,163,74,.2);border-radius:10px;padding:14px 18px}
.tp-badge{display:inline-block;font-size:10px;font-weight:700;color:var(--gr);background:rgba(22,163,74,.1);padding:2px 10px;border-radius:12px;margin-bottom:8px}
.tp-title{font-size:14px;font-weight:700;margin-bottom:4px}
.tp-sub{font-size:11px;color:var(--t2);margin-bottom:10px}
.tp-legs{display:flex;flex-direction:column;gap:6px}
.tp-leg{background:rgba(255,255,255,.5);border:1px solid var(--bd);border-radius:6px;padding:8px 10px}
.tpl-match{font-size:12px;font-weight:600;margin-bottom:2px}
.tpl-detail{font-size:10px;color:var(--t2);line-height:1.5}
.tpl-detail .hl{color:var(--go);font-weight:600}
.tpl-detail .hl2{color:var(--cy)}
.tp-total{display:flex;align-items:center;gap:10px;margin-top:10px;padding-top:8px;border-top:1px solid rgba(22,163,74,.12)}
.tpt-odds{font-size:18px;font-weight:700;color:var(--gr)}
.tpt-hitrate{font-size:13px;color:var(--t2)}
.tpt-hitrate b{color:var(--gr)}
.tp-reason{font-size:10px;color:var(--t2);margin-top:6px;background:rgba(0,0,0,.02);padding:6px 10px;border-radius:4px;line-height:1.5}
.tabs{display:flex;gap:0;margin-bottom:12px;background:var(--surface);border-radius:6px;overflow:hidden;border:1px solid var(--bd);width:fit-content}
.tab{padding:6px 14px;font-size:11px;cursor:pointer;color:var(--t3);border:none;background:transparent}
.tab.active{color:var(--t1);background:var(--s2);font-weight:600}
.tab-content{display:none}.tab-content.show{display:block}
.ctable{width:100%;border-collapse:collapse;font-size:11px}
.ctable thead th{padding:6px 8px;text-align:left;font-weight:600;color:var(--t3);background:rgba(0,0,0,.02);border-bottom:1px solid var(--bd);font-size:9px;white-space:nowrap}
.ctable tbody td{padding:6px 8px;border-bottom:1px solid rgba(0,0,0,.02);color:var(--t2);vertical-align:top}
.ctable tbody tr:hover{background:rgba(0,0,0,.015)}
.td-rank{font-family:var(--mono);font-weight:700;color:var(--t3);width:22px;font-size:11px}
.td-rank.top1{color:var(--go)}
.td-legs{line-height:1.6}
.td-legs .lr{display:flex;gap:3px;align-items:center;flex-wrap:wrap}
.td-legs .leg-x{color:var(--t3);font-size:9px;width:12px;text-align:center}
.tag{font-size:8px;padding:1px 4px;border-radius:2px;white-space:nowrap}
.tag.dir{background:rgba(37,99,235,.08);color:var(--bl)}
.tag.tg{background:rgba(22,163,74,.08);color:var(--gr)}
.tag.hf{background:rgba(217,119,6,.08);color:var(--go)}
.tag.cs{background:rgba(124,58,237,.08);color:var(--pu)}
.tag.pk{background:rgba(8,145,178,.1);color:var(--cy);border:1px solid rgba(8,145,178,.2)}
.td-odds{font-family:var(--mono);font-weight:700;font-size:13px;white-space:nowrap}
.td-pl{text-align:center;font-weight:600;font-family:var(--mono)}
.td-pl.plus{color:var(--gr)}
.td-pl.minus{color:var(--rd)}
.td-cum{text-align:center;font-weight:700;font-family:var(--mono)}
.match-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:6px;margin-top:16px;padding-top:12px;border-top:1px solid var(--bd)}
.match-card{padding:8px 12px;background:var(--surface);border:1px solid var(--bd);border-radius:6px}
.match-card.warn{border-left:3px solid var(--rd);background:rgba(220,38,38,.02)}
.match-card .mc-mid{font-size:9px;color:var(--t3);font-family:var(--mono);margin-bottom:2px}
.match-card .mc-label{font-size:12px;font-weight:600}
.match-card .mc-dir{font-size:10px;margin-top:2px;color:var(--t2)}
.match-card .mc-dir .hl{color:var(--go);font-weight:600}
.match-card .mc-fit{font-size:9px;color:var(--t3)}
.match-card .mc-fund{font-size:9px;margin-top:4px;padding:3px 6px;background:rgba(0,0,0,.02);border-radius:3px;line-height:1.3}
.match-card .mc-fund.warn{color:var(--rd)}.match-card .mc-fund.good{color:var(--gr)}
.legs-toggle{display:flex;align-items:center;gap:6px;padding:8px 12px;background:var(--surface);border:1px solid var(--bd);border-radius:6px;cursor:pointer;font-size:11px;color:var(--t2);margin-top:16px}
.legs-toggle:hover{background:var(--s2)}
.legs-body{display:none;padding-bottom:12px}
.legs-body.open{display:block}
.legs-table{width:100%;border-collapse:collapse;font-size:11px;background:var(--surface);border-radius:6px;overflow:hidden}
.legs-table thead th{padding:5px 6px;text-align:left;font-weight:600;color:var(--t3);background:var(--s2);border-bottom:1px solid var(--bd);font-size:9px;white-space:nowrap}
.legs-table tbody td{padding:5px 6px;border-bottom:1px solid rgba(0,0,0,.04);color:var(--t2)}
.legs-table tbody tr:hover{background:rgba(0,0,0,.02)}
.lt-rank{font-family:var(--mono);color:var(--t3);width:20px;font-size:9px}
.lt-match{font-size:11px;color:var(--t1);font-weight:500}
.lt-odds{font-family:var(--mono);font-weight:600}
.lt-mp{font-family:var(--mono)}.lt-mp.high{color:var(--gr)}.lt-mp.mid{color:var(--go)}.lt-mp.low{color:var(--t3)}
.legs-filter{display:flex;gap:4px;flex-wrap:wrap;padding-bottom:6px}
.lf-btn{padding:2px 8px;font-size:9px;border-radius:10px;cursor:pointer;border:1px solid var(--bd);background:transparent;color:var(--t3)}
.lf-btn.active{background:rgba(8,145,178,.08);border-color:rgba(8,145,178,.2);color:var(--cy)}
.fund-section{background:var(--surface);border:1px solid var(--bd);border-radius:6px;padding:12px 16px;margin-top:16px}
.fund-section h3{font-size:12px;font-weight:700;margin-bottom:8px}
.fni{font-size:10px;padding:4px 10px;margin:3px 0;border-radius:4px;line-height:1.4}
.fni.warn{background:rgba(220,38,38,.04);color:var(--rd);border-left:3px solid var(--rd)}
.fni.info{background:rgba(37,99,235,.04);color:var(--bl);border-left:3px solid var(--bl)}
.fni.ok{background:rgba(22,163,74,.04);color:var(--gr);border-left:3px solid var(--gr)}
.fni .fmid{font-family:var(--mono);font-size:9px;font-weight:600;margin-right:6px;min-width:50px;display:inline-block}
.logic{background:var(--surface);border:1px solid var(--bd);border-radius:6px;padding:12px 16px;margin-top:16px;font-size:11px;color:var(--t2);line-height:1.6}
.logic h3{font-size:12px;font-weight:700;color:var(--t1);margin-bottom:6px}
.logic .fml{background:rgba(0,0,0,.02);padding:6px 10px;border-radius:4px;margin:4px 0;font-family:var(--mono);font-size:10px;border-left:3px solid var(--cy)}
.logic .disc{margin-top:8px;padding:6px 10px;background:rgba(220,38,38,.04);border-radius:4px;border:1px solid rgba(220,38,38,.1);font-size:10px}
.empty{padding:24px;text-align:center;color:var(--t3);font-size:12px}
"""

JS_TEMPLATE = """function _disp(leg){return leg.display_option||leg.option}function _dodds(leg){return leg.display_odds||leg.odds}function _tag(l){var m={"方向":"dir","总进球":"tg","半全场":"hf","比分":"cs"};var b=l.type.replace("打包","");var c=m[b]||"";if(l.type.indexOf("打包")>=0)return'<span class="tag pk">'+l.type.replace('打包','')+'</span>';return'<span class="tag '+c+'">'+l.type+'</span>';}
function fmt(v,d){return(v===null||v===undefined||v==="")?(d||"-"):v;}
function pc(v){return (v*100).toFixed(1)+"%";}
function fitCls(f){return f>=6?"green":(f>=4?"gold":"red");}

var DATA = {data_json};

function render(){
  var d=DATA,h="",fund=d.fundamental||{};
  var groups=d.date_groups||[];
  if(!groups.length){document.getElementById("app").innerHTML='<div class="empty">无数据</div>';return;}

  var today='{today_date}';var selIdx=groups.length-1;groups.forEach(function(g,i){if(g.date===today)selIdx=i;});
  var cur=groups[selIdx];

  function setDate(i){
    selIdx=parseInt(i);cur=groups[i];
    var ids=cur.match_ids||[];
    curLegs=DATALEGS.filter(function(l){return ids.indexOf(l.mid)>=0;});
    curPlan2=cur.plan_2||[];
    curPlan3=cur.plan_3||[];
    refresh();
  }

  var DATALEGS=d.legs;
  var curLegs=[],curPlan2=[],curPlan3=[];
  setDate(selIdx);

  function refresh(){
    var ids=cur.match_ids||[];
    h="";

    // Topbar
    h+='<select class="date-select" onchange="pickDate(this.value)">';
    groups.forEach(function(g,i){
      var d=new Date(g.date+"T00:00:00");
      var wd=["日","一","二","三","四","五","六"][d.getDay()];
      h+='<option value="'+i+'"'+(i===selIdx?' selected':'')+'>'+g.date.substring(5)+' '+wd+' '+g.match_ids.length+'场</option>';
    });
    h+='</select>';

    // Stats
    h+='<div class="stats">';
    h+='<div class="stat-card"><span class="sc-num gr">'+ids.length+'</span>场比赛</div>';
    h+='<div class="stat-card"><span class="sc-num cy">'+curLegs.length+'</span>条腿</div>';
    h+='<div class="stat-card"><span class="sc-num bl">'+(curPlan2.length>0?'TOP '+Math.min(5,curPlan2.length):'0')+'</span>个2.0方案</div>';
    h+='<div class="stat-card"><span class="sc-num go">'+(curPlan3.length>0?'TOP '+Math.min(5,curPlan3.length):'0')+'</span>个3.0方案</div>';
    h+='</div>';

    // Two columns
    h+='<div class="cols"><div class="col-left">';
    if(curPlan2.length>0){
      var tp=curPlan2[0];
      h+='<div class="top-pick">';
      h+='<div class="tp-badge">&#11088; 最稳推荐</div>';
      h+='<div class="tp-title">'+tp.l1.match+' &times; '+tp.l2.match+'</div>';
      h+='<div class="tp-sub">EV '+tp.ev.toFixed(2)+'</div>';
      h+='<div class="tp-legs">';
      h+='<div class="tp-leg"><div class="tpl-match">'+tp.l1.match+'</div><div class="tpl-detail">'+_tag(tp.l1)+' <span class="hl">'+_disp(tp.l1)+'</span> @<span class="hl2">'+_dodds(tp.l1)+'</span><br>命中率 '+pc(tp.l1.mp)+'</div></div>';
      h+='<div class="tp-leg"><div class="tpl-match">'+tp.l2.match+'</div><div class="tpl-detail">'+_tag(tp.l2)+' <span class="hl">'+_disp(tp.l2)+'</span> @<span class="hl2">'+_dodds(tp.l2)+'</span><br>命中率 '+pc(tp.l2.mp)+'</div></div>';
      h+='</div>';
      h+='<div class="tp-total"><span class="tpt-odds">赔率 '+(tp.l1.odds*tp.l2.odds).toFixed(2)+'</span></div>';
      h+='<div class="tp-reason">排序: 命中率优先, 同档按EV</div></div>';
    }
    h+='</div>';

    h+='<div class="col-right">';
    h+='<div class="tabs">';
    h+='<button class="tab active" onclick="sw(\\'p2\\')">2.0计划 (2.0~3.5)</button>';
    h+='<button class="tab" onclick="sw(\\'p3\\')">3.0计划 (3.0~5.0)</button>';
    h+='</div>';
    h+='<div class="tab-content show" id="p2">'+renderCombos(curPlan2)+'</div>';
    h+='<div class="tab-content" id="p3">'+renderCombos(curPlan3)+'</div>';
    h+='</div></div>';

    // Match cards
    h+='<div class="match-list">';
    var matches=d.matches||{};
    ids.forEach(function(mid){
      var m=matches[mid]||{};
      if(!m.home&&!m.away)return;
      var fnotes=fund[mid]||[];
      var fc="";
      fnotes.forEach(function(n){if(n.indexOf("默契球")>=0||n.indexOf("轮换")>=0)fc="warn";});
      h+='<div class="match-card '+fc+'"><div class="mc-mid">'+mid+'</div>';
      h+='<div class="mc-label">'+fmt(m.home)+' vs '+fmt(m.away)+'</div>';
      h+='<div class="mc-dir"><span class="hl">'+fmt(m.direction)+'</span>';
      if(m.actual_score){h+=' <span style="font-size:9px;font-weight:700;color:var(--go)">'+m.actual_score+'</span>';}
      if(m.hit===1){h+=' <span style="font-size:9px;font-weight:700;color:var(--gr)">命中</span>';}
      else if(m.hit===0){h+=' <span style="font-size:9px;font-weight:700;color:var(--rd)">偏离</span>';}
      h+='</div>';
      fnotes.forEach(function(n){
        var cl=n.indexOf("默契球")>=0||n.indexOf("轮换")>=0?"warn":"good";
        h+='<div class="mc-fund '+cl+'">'+n+'</div>';
      });
      h+='</div>';
    });
    h+='</div>';


    // Leg pool
    h+='<div class="legs-toggle" onclick="tl()" id="lt"><span>&#9654;</span> 腿池 &mdash; '+curLegs.length+' 条</div>';
    h+='<div class="legs-body" id="lb">';
    h+='<div class="legs-filter">';
    var flts=["全部","方向","总进球","半全场","比分","打包"];
    flts.forEach(function(f,i){h+='<button class="lf-btn'+(i===0?' active':'')+'" onclick="fl(\\''+f+'\\')">'+f+'</button>';});
    h+='</div>';
    h+='<table class="legs-table" id="ltbl"><thead><tr><th>#</th><th>比赛</th><th>类型</th><th>选项</th><th>优化赔率</th><th>命中率</th></tr></thead><tbody>';
    curLegs.sort(function(a,b){return b.mp-a.mp;}).forEach(function(l,i){
      var mc=l.mp>0.65?"high":(l.mp>0.45?"mid":"low");
      h+='<tr data-typ="'+(l.type.indexOf("打包")>=0?"打包":l.type)+'"><td class="lt-rank">'+(i+1)+'</td>';
      h+='<td class="lt-match">'+l.match+'</td><td>'+_tag(l)+'</td><td>'+l.option+'</td>';
      h+='<td class="lt-odds">'+l.odds+'</td>';
      h+='<td class="lt-mp '+mc+'">'+pc(l.mp)+'</td></tr>';
    });
    h+='</tbody></table></div>';

    // Fundamental
    var relevantF={};
    ids.forEach(function(mid){if(fund[mid])relevantF[mid]=fund[mid];});
    var fkeys=Object.keys(relevantF);
    if(fkeys.length>0){
      h+='<div class="fund-section"><h3>基本面分析要点</h3>';
      fkeys.forEach(function(mid){
        var notes=relevantF[mid];
        var mn=(matches[mid]||{});var ml=fmt(mn.home)+" vs "+fmt(mn.away);
        notes.forEach(function(n){
          var cl=n.indexOf("默契球")>=0||n.indexOf("轮换")>=0?"warn":(n.indexOf("生死战")>=0||n.indexOf("必须赢球")>=0?"ok":"info");
          h+='<div class="fni '+cl+'"><span class="fmid">'+mid+'</span>'+ml+' - '+n+'</div>';
        });
      });
      h+='</div>';
    }

    // Logic
    h+='<div class="logic"><h3>排序规则</h3>';
    h+='<p>1. <b>综合评分</b> = √(腿类命中率) / 最高赔率 降序</p>';
    h+='<p>2. 同分按 <b>期望回报 EV</b> (命中率 x 赔率) 降序</p>';
    h+='<p style="margin-top:6px">mp = 模型概率 x 基本面调整因子(默契球/轮换/已淘汰等)</p>';
    h+='<div class="disc">&#9888; 以上内容由数据分析系统自动生成,仅供参考,不构成投注建议。</div></div>';

    document.getElementById("app").innerHTML=h;
  }

  function parseScore(s){
    if(!s)return null;
    var parts=s.split(/[-:]/);
    if(parts.length!==2)return null;
    var h=parseInt(parts[0]),a=parseInt(parts[1]);
    if(isNaN(h)||isNaN(a))return null;
    return [h,a];
  }
  function judgeLegHit(leg){
    var m=DATA.matches[leg.mid];
    if(!m||!m.actual_score)return null;
    var sc=parseScore(m.actual_score);
    if(!sc)return null;
    var hg=sc[0],ag=sc[1],total=hg+ag;
    var typ=leg.type,opt=leg.option;
    var hcp=m.handicap||0;
    if(typ==="方向"){
      if(opt==="主胜"||opt==="胜")return hg>ag;
      if(opt==="客胜"||opt==="负")return hg<ag;
      if(opt==="平局"||opt==="平")return hg===ag;
      var adj=hg+hcp-ag;
      if(opt==="让胜")return adj>0;
      if(opt==="让平")return adj===0;
      if(opt==="让负")return adj<0;
      return false;
    }
    if(typ==="方向打包"){
      var parts=opt.split("/");var ihcp=false;for(var ip=0;ip<parts.length;ip++){if(parts[ip].indexOf("让")>=0)ihcp=true;}
      for(var p=0;p<parts.length;p++){
            var po=parts[p];
            var adj2=hg+hcp-ag;
            if(po==="胜"&&hg>ag)return true;
            if(po==="平"&&(ihcp?adj2===0:hg===ag))return true;
            if(po==="负"&&(ihcp?adj2<0:hg<ag))return true;
            if(po==="让胜"&&adj2>0)return true;
            if(po==="让平"&&adj2===0)return true;
            if(po==="让负"&&adj2<0)return true;}
      return false;
    }
    if(typ==="总进球"||typ==="总进球打包"){
      var ranges=opt.replace(/球/g,"").split("/");
      for(var r=0;r<ranges.length;r++)if(total===parseInt(ranges[r]))return true;
      return false;
    }
    if(typ==="半全场"){
      var hf=m.half_full||"";
      return hf===opt;
    }
    if(typ==="半全场打包"){
      var hf2=m.half_full||"";
      if(opt.indexOf("主不败")>=0)return hf2==="胜胜"||hf2==="平胜";
      if(opt.indexOf("客不败")>=0)return hf2==="负负"||hf2==="平负";
      return false;
    }
    if(typ==="比分打包"){
      var packs=opt.split("+");
      var scStr=m.actual_score;
      for(var pk=0;pk<packs.length;pk++){
        if(packs[pk]===scStr)return true;
        if(packs[pk]===scStr.replace("-",":"))return true;
      }
      return false;
    }
    return null;
  }
  function judgeComboHit(c){
    var legs=[c.l1,c.l2];
    if(c.l3)legs.push(c.l3);
    var anyNull=false;
    for(var i=0;i<legs.length;i++){
      var r=judgeLegHit(legs[i]);
      if(r===null){anyNull=true;continue;}
      if(!r)return false;
    }
    if(anyNull)return null;
    return true;
  }
  function comboHitLabel(c){
    var r=judgeComboHit(c);
    if(r===true)return'<span style="color:var(--gr);font-weight:700">&#10003;</span>';
    if(r===false)return'<span style="color:var(--rd);font-weight:700">&#10007;</span>';
    return'<span style="color:var(--yw)">等待</span>';
  }
  function renderCombos(list){
    if(!list||list.length===0)return'<div class="empty">暂无方案</div>';
    // Show TOP-5
    var top5=list.slice(0,5);
    var h='<table class="ctable"><thead><tr><th>#</th><th>日期</th><th>比赛组合</th><th>优化赔率</th><th style="text-align:center">结果</th></tr></thead><tbody>';
    top5.forEach(function(c,i){
      var dt=(c.l1.date||c.l2.date||"").substring(5);
      var l1leg=_tag(c.l1)+' <span class="hl">'+_disp(c.l1)+'</span> @<span style="color:var(--cy);font-size:10px">'+_dodds(c.l1)+'</span> <span style="color:var(--t3);font-size:10px">'+c.l1.match+'</span>';
      var l2leg=_tag(c.l2)+' <span class="hl">'+_disp(c.l2)+'</span> @<span style="color:var(--cy);font-size:10px">'+_dodds(c.l2)+'</span> <span style="color:var(--t3);font-size:10px">'+c.l2.match+'</span>';
      var oddsStr = (c.min_odds||c.odds) == (c.max_odds||c.odds) ? String(c.min_odds||c.odds) : (c.min_odds||c.odds)+"~"+(c.max_odds||c.odds);
      // Optimized odds: use virtual odds (l1.odds * l2.odds) regardless of pack or single
      var optOdds = (c.l1.odds * c.l2.odds).toFixed(2);
      h+='<tr><td class="td-rank'+(i===0?' top1':'')+'">'+(i+1)+'</td>';
      h+='<td style="font-family:var(--mono);font-size:10px">'+dt+'</td>';
      h+='<td class="td-legs"><div class="lr">'+l1leg+'</div><div class="lr"><span class="leg-x">x</span>'+l2leg+'</div></td>';
      h+='<td class="td-odds">'+optOdds+'</td>';
      h+='<td style="text-align:center;font-size:14px">'+comboHitLabel(c)+'</td></tr>';
    });
    h+='</tbody></table>';
    if(list.length>5){
      h+='<div style="padding:6px;text-align:center;font-size:10px;color:var(--t3)">仅显示 TOP 5，共 '+list.length+' 个方案</div>';
    }
    return h;
  }

  window.pickDate=setDate;
  window.render=render;
  window.sw=function(id){document.querySelectorAll(".tab").forEach(function(t){t.classList.remove("active");});document.querySelectorAll(".tab-content").forEach(function(t){t.classList.remove("show");});if(id==="p2"){document.querySelector(".tab").classList.add("active");document.getElementById("p2").classList.add("show");}else{document.querySelectorAll(".tab")[1].classList.add("active");document.getElementById("p3").classList.add("show");}};
  window.tl=function(){var b=document.getElementById("lb");var t=document.getElementById("lt");b.classList.toggle("open");t.classList.toggle("open");};
  window.fl=function(typ){document.querySelectorAll(".lf-btn").forEach(function(b){b.classList.remove("active");});var btns=document.querySelectorAll(".lf-btn");for(var i=0;i<btns.length;i++){if((typ==="全部"&&i===0)||btns[i].textContent.trim()===typ){btns[i].classList.add("active");}}document.querySelectorAll("#ltbl tr").forEach(function(r){r.style.display=(typ==="全部"||r.getAttribute("data-typ")===typ)?"":"none";});};

  refresh();
}

render();
"""

def build_html(data):
    from datetime import date
        # Use last date from data instead of system date
    today_str = data["date_groups"][-1]["date"] if data.get("date_groups") else date.today().strftime("%Y-%m-%d")
    js = JS_TEMPLATE.replace("{data_json}", json.dumps(data, ensure_ascii=False)).replace("{today_date}", today_str)
    return '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>计划池</title>\n<style>'+CSS+'</style>\n</head>\n<body>\n<div class="wrap" id="app"></div>\n<script>'+js+'</script>\n</body>\n</html>'

def main():
    data_path = sys.argv[1] if len(sys.argv)>1 and sys.argv[1]!="--out" else os.path.join(DATA_DIR,"plan_data.json")
    out_path = sys.argv[sys.argv.index("--out")+1] if "--out" in sys.argv else os.path.join(os.path.dirname(DATA_DIR),"static","plan.html")
    if not os.path.exists(data_path):
        print("[ERROR] "+data_path+" not found"); return
    data = load_json(data_path)
    html = build_html(data)
    with open(out_path,"w",encoding="utf-8") as f:f.write(html)
    gs = data.get("date_groups",[])
    total_p2 = sum(len(g.get("plan_2",[])) for g in gs)
    total_p3 = sum(len(g.get("plan_3",[])) for g in gs)
    print("已生成: "+out_path)
    print("  "+str(len(gs))+" 个比赛日, "+str(len(data.get("legs",[])))+" 条腿")
    for g in gs:
        print("  "+g["date"]+": "+str(len(g.get("plan_2",[])))+"+"+str(len(g.get("plan_3",[])))+" 方案")

if __name__=="__main__":
    main()
