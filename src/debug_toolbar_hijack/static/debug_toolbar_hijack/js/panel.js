// User search combobox for the django-debug-toolbar hijack panel.
//
// The toolbar inserts panel HTML with innerHTML, so this module is loaded
// through HijackPanel.scripts and binds on the "djdt.panel.render" event.

const PANEL_ID = "HijackPanel";
const DEBOUNCE_MS = 250;

// Same format as the toolbar's data-djdt-styles; set through the CSSOM so a
// strict style-src CSP doesn't block it.
function applyStyles(container) {
    const elements = [...container.querySelectorAll("[data-djdt-styles]")];
    if (container.dataset?.djdtStyles) {
        elements.push(container);
    }
    for (const element of elements) {
        for (const declaration of element.dataset.djdtStyles.split(";")) {
            const [name, value] = declaration.split(":");
            if (name && value) {
                element.style[name.trim()] = value.trim();
            }
        }
    }
}

function bind(panel) {
    const input = panel?.querySelector(".djdt-hijack-search");
    if (!input || input.dataset.djdtHijackBound) {
        return;
    }
    input.dataset.djdtHijackBound = "true";
    applyStyles(panel);

    const listbox = panel.querySelector(
        `#${input.getAttribute("aria-controls")}`
    );
    const status = panel.querySelector(".djdt-hijack-search-status");
    const truncatedNote = panel.querySelector(".djdt-hijack-truncated");
    // The server-rendered list, shown again when the search is cleared.
    const originalOptions = [...listbox.children];
    // Each result is a copy of the server-rendered option, which carries the
    // acquire URL, CSRF token and next URL; only the label and pk change.
    const optionTemplate = panel.querySelector(
        ".djdt-hijack-option-template"
    ).content.firstElementChild;

    let activeIndex = -1;
    let timer;
    let controller;

    const options = () => [...listbox.querySelectorAll('[role="option"]')];

    function setActive(index) {
        const all = options();
        activeIndex = all.length === 0 ? -1 : index;
        for (const [i, option] of all.entries()) {
            const selected = i === activeIndex;
            option.setAttribute("aria-selected", String(selected));
            option.style.backgroundColor = selected
                ? "var(--djdt-highlighted-background-color)"
                : "";
        }
        if (activeIndex >= 0) {
            const option = all[activeIndex];
            input.setAttribute("aria-activedescendant", option.id);
            option.scrollIntoView({ block: "nearest" });
        } else {
            input.removeAttribute("aria-activedescendant");
        }
    }

    function showStatus(text) {
        status.textContent = text;
        status.classList.toggle("djdt-hidden", !text);
    }

    function restore() {
        clearTimeout(timer);
        controller?.abort();
        listbox.replaceChildren(...originalOptions);
        showStatus("");
        truncatedNote?.classList.remove("djdt-hidden");
        input.setAttribute("aria-expanded", "false");
        setActive(-1);
    }

    function render(data) {
        const results = data.users.map((user, i) => {
            const option = optionTemplate.cloneNode(true);
            option.id = `djdt-hijack-result-${i + 1}`;
            option.querySelector(".djdt-hijack-label").textContent = user.label;
            option.querySelector('input[name="user_pk"]').value = user.pk;
            applyStyles(option);
            return option;
        });
        listbox.replaceChildren(...results);
        truncatedNote?.classList.add("djdt-hidden");
        if (results.length === 0) {
            showStatus(input.dataset.noResultsText);
        } else if (data.truncated) {
            showStatus(input.dataset.truncatedText);
        } else {
            showStatus("");
        }
        input.setAttribute("aria-expanded", String(results.length > 0));
        setActive(-1);
    }

    async function search(term) {
        controller?.abort();
        controller = new AbortController();
        const url = new URL(input.dataset.searchUrl, globalThis.location);
        url.searchParams.set("q", term);
        try {
            const response = await fetch(url, {
                credentials: "same-origin",
                headers: { Accept: "application/json" },
                signal: controller.signal,
            });
            if (!response.ok) {
                throw new Error(`${response.status} ${response.statusText}`);
            }
            render(await response.json());
        } catch (error) {
            if (error.name !== "AbortError") {
                console.error("Hijack user search failed:", error);
            }
        }
    }

    input.addEventListener("input", () => {
        clearTimeout(timer);
        const term = input.value.trim();
        if (!term) {
            restore();
            return;
        }
        timer = setTimeout(() => search(term), DEBOUNCE_MS);
    });

    input.addEventListener("keydown", (event) => {
        const count = options().length;
        switch (event.key) {
            case "ArrowDown":
                event.preventDefault();
                if (count > 0) {
                    setActive((activeIndex + 1) % count);
                }
                break;
            case "ArrowUp":
                event.preventDefault();
                if (count > 0) {
                    setActive(activeIndex <= 0 ? count - 1 : activeIndex - 1);
                }
                break;
            case "Enter":
                if (activeIndex >= 0) {
                    event.preventDefault();
                    options()[activeIndex].querySelector("form").requestSubmit();
                }
                break;
            case "Escape":
                // Clear the search instead of letting the toolbar close the
                // panel; a second Escape on the empty box closes it as usual.
                if (input.value) {
                    event.preventDefault();
                    event.stopPropagation();
                    input.value = "";
                    restore();
                }
                break;
        }
    });
}

// django-debug-toolbar 6+ renders inside a shadow root on #djDebugRoot;
// older versions put #djDebug in the document.
function getDebugElement() {
    const host = document.getElementById("djDebugRoot");
    return (host?.shadowRoot ?? document).querySelector("#djDebug");
}

const djDebug = getDebugElement();
if (djDebug) {
    djDebug.addEventListener("djdt.panel.render", (event) => {
        if (event.detail.panelId === PANEL_ID) {
            bind(djDebug.querySelector(`#${PANEL_ID}`));
        }
    });
    // The module loads asynchronously and can miss the first render event.
    const panel = djDebug.querySelector(`#${PANEL_ID}`);
    if (panel) {
        bind(panel);
    }
}
