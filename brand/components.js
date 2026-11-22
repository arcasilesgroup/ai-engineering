/* scroll-spy: mark the nav link for the section in view.
   Lead matches scroll-margin-top (88px): the highlight flips when the
   heading clears the sticky nav. */
(function () {
  const lead = 88;
  const links = document.querySelectorAll('nav a[href^="#"]');
  function updateNav() {
    let current = "";
    for (const link of links) {
      const href = link.getAttribute("href");
      if (!href) continue;
      const section = document.getElementById(href.slice(1));
      if (!section) continue;
      if (section.getBoundingClientRect().top <= lead) current = href.slice(1);
    }
    for (const link of links) {
      const on = link.getAttribute("href") === "#" + current;
      link.classList.toggle("active", on);
      if (on) link.setAttribute("aria-current", "location");
      else link.removeAttribute("aria-current");
    }
  }
  window.addEventListener("scroll", updateNav, { passive: true });
  updateNav();
})();

/* components: progressive enhancement for tabs, copy, filters and expand-all.
   Every part of the page reads without this script; it only adds controls.
   It writes with textContent and reads nothing from the network. */
(function () {
  const live = document.getElementById("live");
  function announce(message) {
    if (!live) return;
    live.textContent = "";
    setTimeout(function () { live.textContent = message; }, 60);
  }

  /* Tabs, per the WAI-ARIA Authoring Practices tabs pattern (automatic activation).
     The tab list is built from each panel's data-tab label, so the markup stays one
     list of headed panels that also reads well with the script off. */
  document.querySelectorAll(".tabs").forEach(function (tabs, setIndex) {
    const panels = Array.from(tabs.querySelectorAll(":scope > .tabpanel"));
    if (panels.length < 2) return;
    const list = document.createElement("div");
    list.className = "tablist";
    list.setAttribute("role", "tablist");
    const buttons = panels.map(function (panel, i) {
      const button = document.createElement("button");
      button.type = "button";
      button.id = "tab-" + setIndex + "-" + i;
      button.setAttribute("role", "tab");
      button.setAttribute("aria-controls", panel.id);
      /* Label parts: an optional key ("A"), the name, an optional state chip ("chosen"). */
      if (panel.dataset.key) {
        const key = document.createElement("span");
        key.className = "tab-key";
        key.textContent = panel.dataset.key;
        button.appendChild(key);
      }
      const name = document.createElement("span");
      name.textContent = panel.dataset.tab || "Tab " + (i + 1);
      button.appendChild(name);
      if (panel.dataset.badge) {
        const badge = document.createElement("span");
        badge.className = "cat c-green";
        badge.textContent = panel.dataset.badge;
        button.appendChild(badge);
      }
      panel.setAttribute("role", "tabpanel");
      panel.setAttribute("aria-labelledby", button.id);
      panel.tabIndex = 0;
      list.appendChild(button);
      return button;
    });
    const indicator = document.createElement("span");
    indicator.className = "tab-ind";
    indicator.setAttribute("aria-hidden", "true");
    list.appendChild(indicator);
    let current = 0;
    /* The bar moves with transform only; a keyboard move is instant, because a
       motion repeated on every arrow press reads as lag. */
    function placeIndicator(isInstant) {
      const button = buttons[current];
      indicator.classList.toggle("is-instant", isInstant);
      indicator.style.transform = "translateX(" + button.offsetLeft + "px) scaleX(" + button.offsetWidth + ")";
    }
    function select(index, moveFocus) {
      current = index;
      buttons.forEach(function (button, i) {
        const isSelected = i === index;
        button.setAttribute("aria-selected", String(isSelected));
        button.tabIndex = isSelected ? 0 : -1;
        panels[i].hidden = !isSelected;
      });
      placeIndicator(moveFocus);
      /* Keep the chosen tab inside a row that scrolls, without moving the page. */
      const chosen = buttons[index];
      if (chosen.offsetLeft < list.scrollLeft || chosen.offsetLeft + chosen.offsetWidth > list.scrollLeft + list.clientWidth) {
        list.scrollLeft = chosen.offsetLeft - 16;
      }
      if (moveFocus) chosen.focus({ preventScroll: true });
      markOverflow();
    }
    /* A row that runs past the screen fades at the edge that hides more tabs. */
    function markOverflow() {
      list.classList.toggle("has-more", list.scrollLeft + list.clientWidth < list.scrollWidth - 1);
    }
    list.addEventListener("scroll", markOverflow, { passive: true });
    buttons.forEach(function (button, i) {
      button.addEventListener("click", function () { select(i, false); });
      button.addEventListener("keydown", function (event) {
        const last = buttons.length - 1;
        const next = { ArrowRight: i === last ? 0 : i + 1, ArrowLeft: i === 0 ? last : i - 1, Home: 0, End: last }[event.key];
        if (next === undefined) return;
        event.preventDefault();
        select(next, true);
      });
    });
    tabs.insertBefore(list, panels[0]);
    tabs.classList.add("is-enhanced");
    select(0, false);
    placeIndicator(true);
    if (window.ResizeObserver) new ResizeObserver(function () { placeIndicator(true); markOverflow(); }).observe(list);
  });

  /* Tables: on a narrow screen each row stacks as a block and each cell shows its
     column name. Explicit roles keep the table semantics that display:block drops. */
  document.querySelectorAll(".tbl-wrap table").forEach(function (table) {
    const heads = Array.from(table.querySelectorAll("thead th")).map(function (th) { return th.textContent.trim(); });
    table.setAttribute("role", "table");
    table.querySelectorAll("thead, tbody").forEach(function (group) { group.setAttribute("role", "rowgroup"); });
    table.querySelectorAll("tr").forEach(function (row) {
      row.setAttribute("role", "row");
      Array.from(row.children).forEach(function (cell, i) {
        cell.setAttribute("role", cell.tagName === "TH" ? "columnheader" : "cell");
        if (cell.tagName === "TD" && heads[i]) cell.dataset.label = heads[i];
      });
    });
    table.classList.add("is-stackable");
  });

  /* A region that scrolls sideways must take keyboard focus, or its hidden part is out
     of reach (WCAG 2.1.1). Only regions that overflow at the current width get a stop. */
  const scrollers = Array.from(document.querySelectorAll("pre, .canvas, .tbl-wrap"));
  function markScrollers() {
    scrollers.forEach(function (region) {
      if (region.scrollWidth > region.clientWidth + 1) region.tabIndex = 0;
      else region.removeAttribute("tabindex");
    });
  }
  markScrollers();
  window.addEventListener("resize", markScrollers, { passive: true });

  /* Copy: the button copies its block's code and says so in the status region. */
  document.querySelectorAll(".code .copy").forEach(function (button) {
    button.hidden = false;
    button.addEventListener("click", function () {
      const code = button.closest(".code").querySelector("pre").innerText;
      const done = function () { button.textContent = "Copied"; announce("Code copied"); setTimeout(function () { button.textContent = "Copy"; }, 2000); };
      const failed = function () { announce("Copy is blocked here: select the code and copy it by hand"); };
      if (navigator.clipboard) navigator.clipboard.writeText(code).then(done, failed);
      else failed();
    });
  });

  /* Filters: one pressed chip at a time narrows the rows tagged with its value. */
  document.querySelectorAll(".filters").forEach(function (bar) {
    const target = document.getElementById(bar.dataset.target);
    if (!target) return;
    const rows = Array.from(target.querySelectorAll("[data-tags]"));
    const chips = Array.from(bar.querySelectorAll(".chip"));
    bar.hidden = false;
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        const value = chip.dataset.filter;
        let shown = 0;
        chips.forEach(function (other) { other.setAttribute("aria-pressed", String(other === chip)); });
        rows.forEach(function (row) {
          const isMatch = value === "all" || row.dataset.tags.split(" ").includes(value);
          row.hidden = !isMatch;
          if (isMatch) shown += 1;
        });
        announce(shown + " of " + rows.length + " shown");
      });
    });
  });

  /* Expand all: opens or closes every item in the named list. */
  document.querySelectorAll("[data-expand]").forEach(function (button) {
    const list = document.getElementById(button.dataset.expand);
    if (!list) return;
    button.hidden = false;
    button.addEventListener("click", function () {
      const shouldOpen = button.dataset.state !== "open";
      list.querySelectorAll("details").forEach(function (item) { item.open = shouldOpen; });
      button.dataset.state = shouldOpen ? "open" : "closed";
      button.textContent = shouldOpen ? "Collapse all" : "Expand all";
    });
  });

  /* Print: a closed item prints as its title only, so printing opens them all. */
  window.addEventListener("beforeprint", function () {
    document.querySelectorAll("details").forEach(function (item) { item.open = true; });
  });
})();
