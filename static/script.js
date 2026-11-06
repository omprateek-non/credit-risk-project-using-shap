const $ = (s) => document.querySelector(s);
const form = $("#form"), go = $("#go"), err = $("#err");
const fmt = (n) => Number(n).toLocaleString("en-US");

// --- loan grade chips
let grade = "B";
const gradesEl = $("#grades");
"ABCDEFG".split("").forEach((g) => {
  const b = document.createElement("button");
  b.type = "button"; b.textContent = g; b.setAttribute("aria-pressed", g === grade);
  b.onclick = () => {
    grade = g;
    gradesEl.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x.textContent === g));
  };
  gradesEl.append(b);
});

// --- cursor glow on the form border
form.addEventListener("pointermove", (e) => {
  const r = form.getBoundingClientRect();
  form.style.setProperty("--mx", e.clientX - r.left + "px");
  form.style.setProperty("--my", e.clientY - r.top + "px");
});

// --- live loan-to-income ratio (this is the loan_percent_income field)
const amnt = $("#amnt"), income = form.person_income;
function ratio() {
  const a = +amnt.value, i = +income.value;
  amnt.style.setProperty("--p", ((a - amnt.min) / (amnt.max - amnt.min)) * 100 + "%");
  $("#amntOut").textContent = fmt(a);
  const r = i > 0 ? a / i : 0, box = $(".ratio");
  $("#ratio").textContent = (r * 100).toFixed(1) + "%";
  $("#ratioBar").style.width = Math.min(r, 1) * 100 + "%";
  box.classList.toggle("over", r > 1);
  box.classList.toggle("high", r > 0.35 && r <= 1);
  $("#ratioNote").textContent = r > 1 ? "Loan is larger than annual income. The API rejects this." : r > 0.35 ? "High burden relative to income." : "";
  return r;
}
amnt.addEventListener("input", ratio);
income.addEventListener("input", ratio);
ratio();

// --- helpers
function countUp(el, to, ms = 1400) {
  const t0 = performance.now();
  (function step(t) {
    const p = Math.min((t - t0) / ms, 1), e = 1 - Math.pow(1 - p, 4);
    el.textContent = (to * e).toFixed(2);
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}
const showErr = (m) => { err.hidden = false; err.textContent = m; err.style.animation = "none"; void err.offsetWidth; err.style.animation = ""; };

function render(d) {
  const res = $("#result"), high = d.prediction === 1;
  res.classList.remove("ok", "bad"); res.classList.add(high ? "bad" : "ok");
  $("#arc").style.strokeDashoffset = 100 - d.default_probability_percentage;
  $("#needle").style.transform = `rotate(${-90 + d.default_probability * 180}deg)`;
  $("#thr").style.transform = `rotate(${-90 + d.threshold * 180}deg)`;
  countUp($("#pct"), d.default_probability_percentage);
  const v = $("#verdict");
  v.className = "verdict " + (high ? "bad" : "ok");
  v.textContent = high ? "High risk: likely to default" : "Low risk: likely to repay";
  $("#thrOut").textContent = d.threshold_percentage.toFixed(2) + "%";
  $("#okOut").textContent = d.no_default_probability_percentage.toFixed(2) + "%";
  const gap = d.default_probability_percentage - d.threshold_percentage;
  $("#gapOut").textContent = (gap > 0 ? "+" : "") + gap.toFixed(2) + " pts";
  $("#modelName").textContent = d.model;
  if (innerWidth < 880) res.scrollIntoView({ behavior: "smooth", block: "center" });
}

// --- submit
form.addEventListener("submit", async (e) => {
  e.preventDefault(); err.hidden = true;
  form.querySelectorAll(".bad").forEach((x) => x.classList.remove("bad"));
  const f = new FormData(form), r = ratio();
  if (r > 1) { income.classList.add("bad"); return showErr("Loan amount can't exceed annual income. Lower the loan or raise the income."); }
  const age = +f.get("person_age"), emp = +f.get("person_emp_length"), hist = +f.get("cb_person_cred_hist_length");
  if (emp > age - 14) { form.person_emp_length.classList.add("bad"); return showErr("Years employed is higher than the age allows."); }
  if (hist > age - 14) { form.cb_person_cred_hist_length.classList.add("bad"); return showErr("Credit history is longer than the age allows."); }

  const body = {
    person_age: age,
    person_income: +f.get("person_income"),
    person_home_ownership: f.get("person_home_ownership"),
    person_emp_length: emp,
    loan_intent: f.get("loan_intent"),
    loan_grade: grade,
    loan_amnt: +f.get("loan_amnt"),
    loan_int_rate: +f.get("loan_int_rate"),
    loan_percent_income: Math.round(r * 10000) / 10000,
    cb_person_default_on_file: f.get("cb_person_default_on_file"),
    cb_person_cred_hist_length: hist,
  };

  go.disabled = true; go.classList.add("load");
  try {
    const res = await fetch("/predict", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const d = data.detail;
      throw new Error(Array.isArray(d) ? d.map((x) => `${x.loc.slice(-1)}: ${x.msg}`).join("; ") : d || `Server error ${res.status}`);
    }
    render(data);
  } catch (x) {
    showErr(x.message === "Failed to fetch" ? "Can't reach the server. If it's on Render's free tier it may be waking up, so retry in 30-60 seconds." : x.message);
  } finally { go.disabled = false; go.classList.remove("load"); }
});

// --- server health badge
(async () => {
  const p = $("#status"), t = p.querySelector("em");
  try {
    const h = await (await fetch("/health")).json();
    p.className = "pill " + (h.model_loaded ? "on" : "off");
    t.textContent = h.model_loaded ? "Model online" : "Model not loaded";
  } catch { p.className = "pill off"; t.textContent = "Server unreachable"; }
})();
