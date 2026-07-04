import { apiGet } from "./api.js";

async function loadPlans() {
  document.getElementById("plan-content").innerHTML = '<iframe src="/static/plan.html?_t=' + Date.now() + '" style="width:100%;height:calc(100vh - 120px);border:none;border-radius:8px;background:#f5f6f8"></iframe>';
}

export { loadPlans };
