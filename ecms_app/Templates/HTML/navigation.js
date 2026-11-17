(() => {
  "use strict";

  const htmlRoot = new URL(".", document.currentScript.src);
  const routes = {
    home: "[1] Landing and Sign-in/(0) Landing page-html/Main.dc.html",
    signIn: "[1] Landing and Sign-in/(1) Sign in-html/Login.dc.html",
    facultyLogin: "[1] Landing and Sign-in/(2) Faculty Adviser sign in-html/Faculty-Login.dc.html",
    evaluatorLogin: "[1] Landing and Sign-in/(3) Evaluator sign in-html/Evaluator-Login.dc.html",
    adminLogin: "[1] Landing and Sign-in/(4) Admin sign in-html/Admin-Login.dc.html",
    register: "[1] Landing and Sign-in/(5) Register group-html/Register.dc.html",
    student: "[2] Students/1 Student · My application copy-html/Main-3x08.dc.html",
    documentsStart: "[2] Students/2a Student · Submit documents (nothing uploaded yet) copy-html/DocumentsStart-mz3z.dc.html",
    documentsUploaded: "[2] Students/2b Student · Submit documents (some uploaded) copy-html/Documents-h6w4.dc.html",
    papers: "[4] Evaluators/5 Evaluator · My papers copy-html/Papers-dxay.dc.html",
    studioStart: "[4] Evaluators/6a Evaluator · Studio, not started copy-html/StudioStart-1fbx.dc.html",
    studioSheet1: "[4] Evaluators/6b Evaluator · Studio, sheet 1 of 2 (scroll view) copy-html/StudioScroll1-ka9p.dc.html",
    studioSheet1Details: "[4] Evaluators/6c Evaluator · Studio, sheet 1 of 2 (full details) copy-html/Studio-ih66.dc.html",
    studioSheet2: "[4] Evaluators/6d Evaluator · Studio, sheet 2 of 2 (scroll view) copy-html/StudioScroll2-szvb.dc.html",
    studioSheet2Details: "[4] Evaluators/6e Evaluator · Studio, sheet 2 of 2 (full details) copy-html/StudioConsent-n47h.dc.html",
    monitor: "[6] IF Tech Assist and Panel Chair SHARE the same screen/(1) Monitor copy-html/Monitor-jz46.dc.html",
    approvals: "[6] IF Tech Assist and Panel Chair SHARE the same screen/(2) Approvals copy-html/Decisions-8pt9.dc.html",
    screening: "[6] IF Tech Assist and Panel Chair SHARE the same screen/(3) Screening copy-html/Screening-qr8z-uqay.dc.html",
    assignment: "[6] IF Tech Assist and Panel Chair SHARE the same screen/(4) Assign evaluators copy-html/Assign-w2mb-dgk8.dc.html",
    advisees: "[7] Faculty Adviser Screen (Read-Only)/My Advisees (Read-Only) copy-html/Faculty-c4n6.dc.html"
  };

  const destination = key => new URL(routes[key], htmlRoot).href;
  const pagePath = decodeURIComponent(location.pathname).toLowerCase();
  const isPage = name => pagePath.includes(name.toLowerCase());
  const currentPage = () => {
    if (isPage("landing page-html")) return "home";
    if (isPage("faculty adviser sign in-html")) return "facultyLogin";
    if (isPage("evaluator sign in-html")) return "evaluatorLogin";
    if (isPage("admin sign in-html")) return "adminLogin";
    if (isPage("sign in-html")) return "signIn";
    if (isPage("register group-html")) return "register";
    if (isPage("2a student")) return "documentsStart";
    if (isPage("2b student")) return "documentsUploaded";
    if (isPage("1 student")) return "student";
    if (isPage("6a evaluator")) return "studioStart";
    if (isPage("6b evaluator")) return "studioSheet1";
    if (isPage("6c evaluator")) return "studioSheet1Details";
    if (isPage("6d evaluator")) return "studioSheet2";
    if (isPage("6e evaluator")) return "studioSheet2Details";
    if (isPage("5 evaluator")) return "papers";
    if (isPage("(1) monitor")) return "monitor";
    if (isPage("(2) approvals")) return "approvals";
    if (isPage("(3) screening")) return "screening";
    if (isPage("(4) assign evaluators")) return "assignment";
    if (isPage("faculty adviser screen")) return "advisees";
    return "";
  };

  const cleanText = element => (element.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();

  function linkDestination(anchor) {
    const text = cleanText(anchor);
    const page = currentPage();
    if (text.includes("ethicc") || text.includes("back to home")) return ["home"];
    if (text.includes("register")) return ["register"];
    if (text.includes("sign in")) return ["signIn"];
    if (text === "my application") return ["student"];
    if (text === "submit documents") return ["documentsStart"];
    if (text === "certificates") return ["student"];
    if (text === "my papers") return ["papers"];
    if (text === "evaluation studio") return ["studioStart"];
    if (text === "monitor") return ["monitor"];
    if (text === "approvals") return ["approvals"];
    if (text === "screening queue") return ["screening"];
    if (text === "evaluator assignment") return ["assignment"];
    if (text === "my advisees") return ["advisees"];
    if (text === "forgot password?") return [];
    if (page && text === "← my papers") return ["papers"];
    return [];
  }

  function wireLinks(root) {
    for (const anchor of root.querySelectorAll("a[href='#']")) {
      const target = linkDestination(anchor);
      if (!target.length) continue;
      anchor.href = destination(target[0]) + (target[1] ? `#${target[1]}` : "");
    }
  }

  function navigate(key, fragment) {
    location.href = destination(key) + (fragment ? `#${fragment}` : "");
  }

  function handleRoleTab(button) {
    const role = cleanText(button);
    if (role === "student") navigate("signIn");
    else if (role === "faculty/adviser") navigate("facultyLogin");
    else if (role === "evaluator") navigate("evaluatorLogin");
    else if (role === "admin") navigate("adminLogin");
  }

  function handleUpload(button) {
    const row = button.closest(".sl");
    if (!row) return false;
    let input = row.querySelector("input[type='file']");
    if (!input) {
      input = document.createElement("input");
      input.type = "file";
      input.accept = ".pdf,application/pdf";
      input.hidden = true;
      row.appendChild(input);
      input.addEventListener("change", () => {
        const label = row.querySelector("small");
        if (input.files && input.files[0] && label) label.textContent = input.files[0].name;
      });
    }
    input.click();
    return true;
  }

  function filterTable(button) {
    const card = button.closest(".cd");
    const table = card && card.querySelector("table");
    if (!table) return;
    const filter = cleanText(button).replace(/\s+\d+$/, "");
    for (const row of table.querySelectorAll("tr")) {
      if (row.querySelector("th")) continue;
      row.hidden = filter !== "all" && !cleanText(row).includes(filter);
    }
  }

  document.addEventListener("click", event => {
    const path = event.composedPath ? event.composedPath() : [event.target];
    const button = path.find(node => node instanceof HTMLButtonElement);
    const anchor = path.find(node => node instanceof HTMLAnchorElement);
    const page = currentPage();

    if (anchor && anchor.getAttribute("href") === "#") {
      const target = linkDestination(anchor);
      if (target.length) {
        event.preventDefault();
        navigate(target[0], target[1]);
      } else if (cleanText(anchor) === "forgot password?") {
        event.preventDefault();
        alert("Password recovery is not available in this static prototype.");
      }
      return;
    }
    if (!button || button.disabled) return;

    const text = cleanText(button);
    if (["student", "faculty/adviser", "evaluator", "admin"].includes(text) && button.closest("[role='tablist']")) {
      event.preventDefault();
      handleRoleTab(button);
      return;
    }
    if (text === "sign out") return navigate("home");
    if (text === "sign in") {
      if (page === "home") return navigate("signIn");
      if (page === "facultyLogin") return navigate("advisees");
      if (page === "evaluatorLogin") return navigate("papers");
      if (page === "adminLogin") return navigate("monitor");
      return navigate("student");
    }
    if (text === "register" || text.includes("register your group") ||
        (text === "register group" && page !== "register")) return navigate("register");
    if (text === "register group" && page === "register") return navigate("student");
    if (text === "continue" && page === "adminLogin") return navigate("monitor");
    if (text === "start review") return navigate("studioStart");
    if (text === "continue" && page === "papers") return navigate("studioSheet1");
    if (text === "start sheet 1") return navigate(page === "studioStart" ? "studioSheet1" : "studioSheet1Details");
    if (text === "re-upload form 12") return navigate("documentsUploaded");
    if (text === "submit application") return navigate("student");
    if (text === "pass to assignment" || text === "assign evaluators") {
      return navigate(page === "assignment" ? "monitor" : "assignment");
    }
    if (text === "proceed to sheet 2 of 2") {
      return navigate(page === "studioSheet1Details" ? "studioSheet2Details" : "studioSheet2");
    }
    if (text === "back to sheet 1") {
      return navigate(page === "studioSheet2Details" ? "studioSheet1Details" : "studioSheet1");
    }
    if (text === "submit evaluation") return navigate("papers");
    if (button.classList.contains("eye")) {
      const password = document.querySelector("#pw");
      if (password) {
        password.type = password.type === "password" ? "text" : "password";
        button.setAttribute("aria-label", password.type === "password" ? "Show password" : "Hide password");
      }
      return;
    }
    if (text === "upload" || text === "replace") {
      if (handleUpload(button)) return;
    }
    if (text === "save draft") {
      alert("Draft saving is not connected to a backend in this static prototype.");
      return;
    }
    if (text === "open pdf" || text === "view pdfs") {
      alert("No sample PDF is attached to this static prototype.");
      return;
    }
    if (text === "screen") {
      const detail = document.querySelector(".cd.y");
      if (detail) detail.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    if (text === "return with feedback" || text === "return" || text === "approve" ||
        text === "send for revision" || text === "issue certificate") {
      alert("This action requires the EthiCCIS application backend, which is not connected in this prototype.");
      return;
    }
    if (text === "+" || text === "−") {
      const zoom = button.parentElement && button.parentElement.querySelector("small");
      if (!zoom) return;
      const current = Number.parseInt(zoom.textContent, 10) || 100;
      const next = Math.max(50, Math.min(200, current + (text === "+" ? 10 : -10)));
      zoom.textContent = `${next}%`;
      const documentPane = document.querySelector(".vs");
      if (documentPane) documentPane.style.transform = `scale(${next / 100})`;
      return;
    }
    if (button.classList.contains("acc")) {
      const sheet = button.parentElement && button.parentElement.querySelector(".sf");
      if (sheet) {
        sheet.hidden = !sheet.hidden;
        button.setAttribute("aria-expanded", String(!sheet.hidden));
      }
      return;
    }
    if (button.classList.contains("tab") || button.closest(".chs")) {
      const group = button.parentElement;
      if (group) {
        for (const sibling of group.querySelectorAll("button")) sibling.classList.toggle("on", sibling === button);
      }
      if (button.closest(".chs")) filterTable(button);
      return;
    }
    if (page.startsWith("studioSheet") && button.closest(".sh")) {
      const group = button.parentElement;
      if (group) {
        for (const sibling of group.querySelectorAll("button")) {
          sibling.setAttribute("aria-pressed", String(sibling === button));
          sibling.classList.toggle("on", sibling === button);
        }
      }
    }
  });

  wireLinks(document);
  new MutationObserver(records => {
    for (const record of records) {
      for (const node of record.addedNodes) {
        if (node.nodeType === Node.ELEMENT_NODE) {
          if (node.matches("a[href='#']")) {
            const target = linkDestination(node);
            if (target.length) node.href = destination(target[0]) + (target[1] ? `#${target[1]}` : "");
          }
          wireLinks(node);
        }
      }
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
