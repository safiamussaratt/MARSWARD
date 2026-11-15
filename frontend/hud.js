// MARSWARD HUD: boot screen, clocks and keyboard shortcuts.
// Pure decoration and convenience; the app works without it.

(function () {
    const pad = (n) => String(n).padStart(2, "0");

    // ---------- boot screen ----------
    const boot = document.getElementById("boot");

    if (boot) {
        const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const remove = () => boot.classList.add("done");

        if (reduced) {
            remove();
        } else {
            setTimeout(remove, 2700);
            // Any key or click skips it.
            ["keydown", "pointerdown"].forEach((type) =>
                window.addEventListener(type, remove, { once: true })
            );
        }
    }

    // ---------- clocks ----------
    const utc = document.getElementById("clock-utc");
    const session = document.getElementById("clock-session");
    const started = Date.now();

    function tick() {
        const now = new Date();

        if (utc) {
            utc.textContent =
                `${pad(now.getUTCHours())}:${pad(now.getUTCMinutes())}:${pad(now.getUTCSeconds())} UTC`;
        }

        if (session) {
            const s = Math.floor((Date.now() - started) / 1000);
            session.textContent =
                `SESSION T+${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}`;
        }
    }

    tick();
    setInterval(tick, 1000);

    // ---------- keyboard shortcuts: 1-5 switch views ----------
    window.addEventListener("keydown", (event) => {
        if (event.ctrlKey || event.metaKey || event.altKey) {
            return;
        }

        const tag = (event.target.tagName || "").toLowerCase();

        if (["input", "select", "textarea"].includes(tag)) {
            return;
        }

        const items = document.querySelectorAll(".nav-item[data-view]");
        const index = Number(event.key) - 1;

        if (Number.isInteger(index) && items[index]) {
            items[index].click();
        }
    });

    // ---------- keep the scan sweep matched to the map height ----------
    const frame = document.getElementById("map-frame");

    if (frame && "ResizeObserver" in window) {
        new ResizeObserver(() => {
            frame.style.setProperty("--frame-h", `${frame.clientHeight}px`);
        }).observe(frame);
    }
})();
