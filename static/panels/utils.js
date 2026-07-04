// Shared utility functions

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

function fmtSp(v) {
  if (v === null || v === undefined || v === "" || v === 0) return "-";
  var n = Number(v);
  return isNaN(n) ? String(v) : n.toFixed(2);
}

function enc(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function faDirBadge(dir, rating) {
  if (!dir) return '<span class="fa-c-wait">\u7b49\u5f85\u9884\u6d4b</span>';
  var cls = "win";
  if (dir === "\u8d1f" || dir === "\u8ba9\u8d1f") cls = "loss";
  return '<span class="fa-dir-badge ' + cls + '">' + dir + '</span>';
}

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

export { fmt, fmt1, rowClass, dirClass, rateClass, dirBadgeHTML, parseWeekday, fmtSp, enc, drawTrendChart };
