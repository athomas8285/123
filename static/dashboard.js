// V3.3.3-Core Dashboard - Modular entry point
import { overview } from "./panels/overview.js";
import { loadConsole, showFetchDataModal, submitFetchData, showDataResultModal, showResultModal, closeDataResultModal, closeResultModal, showFetchJczqModal, refreshConsoleAfterFetch } from "./panels/console.js";
import { loadMatches, loadPrediction, navigateToMatches, filterMatches } from "./panels/matches.js";
import { loadFundamental, toggleFaDateGroup, toggleFaCard } from "./panels/fundamental.js";
import { loadPlans } from "./panels/plans.js";
import { loadReview } from "./panels/review.js";
import { loadSystem } from "./panels/system.js";
import { fmt, fmt1, fmtSp, enc } from "./panels/utils.js";

// ===== Global state =====
const panelLoaded = {};
window.panelLoaded = panelLoaded;
const WEEKDAYS = ["周日","周一","周二","周三","周四","周五","周六"];
let currentMatchFilter = "all";

// ===== Make functions available for HTML onclick handlers =====
window.toggleFaDateGroup = toggleFaDateGroup;
window.toggleFaCard = toggleFaCard;
window.closeResultModal = closeResultModal;
window.submitFetchData = submitFetchData;
window.closeDataResultModal = closeDataResultModal;
window.currentMatchFilter = "all";
window.navigateToMatches = navigateToMatches;
window.filterMatches = filterMatches;
window.fmt = fmt;
window.fmt1 = fmt1;
window.fmtSp = fmtSp;
window.enc = enc;

// ===== Panel loaders =====
const loaders = {
  overview, console: loadConsole, matches: loadMatches,
  prediction: loadPrediction, fundamental: loadFundamental,
  plans: loadPlans, featured: function(){
    var fIframe = document.getElementById('featured-iframe');
    if (fIframe) fIframe.src = '/api/dashboard/featured?_t=' + Date.now();
  },
  review: loadReview, system: loadSystem
};

async function loadPanel(name) {
  if (panelLoaded[name]) return;
  panelLoaded[name] = true;
  if (loaders[name]) {
    try { await loaders[name](); }
    catch(e) { console.error("Panel '" + name + "' error:", e); }
  }
}

// ===== Sidebar time =====
function updateSidebarTime() {
  document.getElementById("sidebar-time").textContent = new Date().toLocaleString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
setInterval(updateSidebarTime, 1000);
updateSidebarTime();

// ===== Navigation setup =====
document.querySelectorAll(".nav-item").forEach(function(btn) {
  btn.addEventListener("click", function() {
    document.querySelectorAll(".nav-item").forEach(function(b) { b.classList.remove("active"); });
    document.querySelectorAll(".panel").forEach(function(p) { p.classList.remove("active"); });
    this.classList.add("active");
    var panel = document.getElementById("panel-" + this.dataset.panel);
    if (panel) panel.classList.add("active");
    loadPanel(this.dataset.panel);
  });
});

// Auto-load default active panel on page load
(function(){
  var active = document.querySelector(".nav-item.active");
  if (active) loadPanel(active.dataset.panel);
})();

document.getElementById("collapse-btn").addEventListener("click", function() {
  document.getElementById("sidebar").classList.toggle("collapsed");
});

// ===== Init =====
document.getElementById("loadingOverlay").style.display = "none";
try { overview(); } catch(e) { console.error("Init overview error:", e); }
lucide.createIcons();

