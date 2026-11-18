document.addEventListener("click", function (e) {
  const link = e.target.closest("a");
  if (link && link.getAttribute("href") === "#") {
    e.preventDefault();
    const text = (link.textContent || "").trim().toLowerCase();
    if (text.includes("back to home") || text.includes("ethiccis")) {
      window.location.href = "/";
    }
    return;
  }

  const btn = e.target.closest("button");
  if (!btn) return;

  const targetHref = btn.getAttribute("data-href");
  if (targetHref) {
    e.preventDefault();
    window.location.href = targetHref;
    return;
  }

  const label = (btn.textContent || "").trim().toLowerCase();
  if (label === "sign out") {
    e.preventDefault();
    window.location.href = "/logout";
  } else if (btn.classList.contains("tab")) {
    if (label === "student") window.location.href = "/login/student";
    else if (label.includes("faculty")) window.location.href = "/login/faculty";
    else if (label === "evaluator") window.location.href = "/login/evaluator";
    else if (label === "admin") window.location.href = "/login/admin";
  }
});