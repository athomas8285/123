// Shared utility functions

function fmt(v, d) { return (v === null || v === undefined || v === "") ? (d || "-") : v; }

function fmt1(v, d) { if (v === null || v === undefined || v === "") return d || "-"; var n = Number(v); return isNaN(n) ? (d || "-") : n.toFixed(1); }
function rowClass(m) {
  if (m.actual_score) return "row-done";
  if (m.direction) return "row-pred";
  return "row-wait";
}

function dirClass(direction) {
  if (direction === "负" || direction === "让负") return "lose";
  return "dir";
}

function rateClass(rating) {
  if (rating === "C") return "C";
  return "B";
}

function dirBadgeHTML(rating, direction) {
  return '<span class="dir-badge ' + (rating || "") + '">' + fmt(direction, "—") + '</span>';
}

function parseWeekday(mid) {
  for (const wd of WEEKDAYS) { if (mid && mid.startsWith(wd)) return wd; }
  return null;
}

function fmtSp(v) {
  if (v === null || v === undefined || v === "" || v === 0) return "-";
  var n = Number(v);
  return isNaN(n) ? String(v) : n.toFixed(2);
}

function enc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function faDirBadge(dir, rating) {
  if (!dir) return '<span class="fa-c-wait">等待预测</span>';
  var cls = "win";
  if (dir === "负" || dir === "让负") cls = "loss";
  return '<span class="fa-dir-badge ' + cls + '">' + dir + '</span>';
}

export { fmt, fmt1, rowClass, dirClass, rateClass, dirBadgeHTML, parseWeekday, fmtSp, enc };
