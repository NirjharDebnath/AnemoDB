/**
 * AnemoDB Documentation Interactive Client Script
 * Handles lightbox zooming, clipboard copying, benchmark tab switching,
 * code language tab switching, architecture inspector interactions,
 * and scroll-triggered counter/bar animations.
 */

// ───────── 1. CLIPBOARD COPY INSTALLATION ─────────
function copyInstallCommand() {
    const installCommand = `git clone https://github.com/NirjharDebnath/AnemoDB.git
cd AnemoDB
make
sudo make install
anemo_db`;

    navigator.clipboard.writeText(installCommand).then(() => {
        const btn = document.getElementById('copyInstallBtn');
        const text = document.getElementById('copyBtnText');
        btn.classList.add('copied');
        text.innerText = '✓ Copied to Clipboard!';

        setTimeout(() => {
            btn.classList.remove('copied');
            text.innerText = 'Copy Commands';
        }, 2500);
    }).catch(err => {
        console.error('Failed to copy: ', err);
    });
}

// ───────── 2. INTERACTIVE PIPELINE INSPECTOR ─────────
const stages = [
    {
        title: "⚡ Stage 1: Non-Blocking Network Listener",
        desc: "The listener runs on a dedicated POSIX thread bound to port 8080. When a client connects, the listener immediately performs accept() and delegates the raw socket descriptor into the bounded task queue. Because reading is performed asynchronously by worker threads, slow or hanging clients can never stall the server's ability to accept new connections. If the queue is saturated, it replies with [ERROR] SERVER_BUSY_QUEUE_FULL instantly."
    },
    {
        title: "📦 Stage 2: Bounded Task Queue (ThreadSafeQueue)",
        desc: "An internal producer-consumer queue with a default capacity of 5,000 tasks. It uses std::mutex and std::condition_variable for sleep-wakeup signaling. Tasks are moved with C++17 move semantics (zero memory copies). When under peak burst pressure, excess requests are rejected fast, protecting the server against out-of-memory crashes."
    },
    {
        title: "🌪️ Stage 3: Request Coalescing (Single-Flight LRU Cache)",
        desc: "When multiple worker threads miss the cache on the exact same query concurrently (e.g., during a traffic spike), the first worker becomes the LEADER and marks the cache node IN_PROGRESS. All subsequent threads become FOLLOWERS and sleep on the node's condition variable. The leader queries PostgreSQL once, populates the value, and calls notify_all()—satisfying all 500 requests with a single database trip!"
    },
    {
        title: "🐘 Stage 4: Resilient PostgreSQL Connection Pool",
        desc: "A pre-warmed pool of persistent libpqxx connections matching the worker thread count. On misses, workers acquire a connection with a 5-second timeout. Connections are health-checked with auto-reconnection if idle sockets drop. Queries are executed strictly within a pqxx::read_transaction scope, ensuring complete read-only safety."
    }
];

function inspectStage(index) {
    document.querySelectorAll('.arch-node').forEach((node, i) => {
        node.classList.toggle('active', i === index);
    });
    document.getElementById('inspectorTitle').innerText = stages[index].title;
    document.getElementById('inspectorDesc').innerText = stages[index].desc;
}

// ───────── 3. BENCHMARK TABS SWITCHING ─────────
function switchBenchTab(index) {
    document.querySelectorAll('.bench-tab-btn').forEach((btn, i) => {
        btn.classList.toggle('active', i === index);
    });
    document.querySelectorAll('.bench-tab-pane').forEach((pane, i) => {
        const isActive = (i === index);
        pane.classList.toggle('active', isActive);
        if (isActive) {
            // Trigger or replay animation on all counters and bars in active tab
            pane.querySelectorAll('[data-counter]').forEach(el => {
                animateCounter(el, true);
            });
            pane.querySelectorAll('.latency-fill[data-width]').forEach(bar => {
                bar.dataset.animated = 'false';
                bar.style.width = '0%';
                setTimeout(() => {
                    animateLatencyBar(bar);
                }, 40);
            });
        }
    });
}

// ───────── 4. CLIENT INTEGRATION CODE TABS ─────────
function switchCodeTab(lang) {
    const tabs = ['python', 'node', 'go', 'bash'];
    document.querySelectorAll('.code-tab-btn').forEach((btn, i) => {
        btn.classList.toggle('active', tabs[i] === lang);
    });
    tabs.forEach(item => {
        const pane = document.getElementById(`codePane-${item}`);
        if (pane) {
            pane.classList.toggle('active', item === lang);
        }
    });
}

function copySnippet(snippetId, btn) {
    const el = document.getElementById(snippetId);
    if (!el) return;
    const textToCopy = el.innerText;
    navigator.clipboard.writeText(textToCopy).then(() => {
        const origText = btn.innerText;
        btn.innerText = '✓ Copied!';
        btn.style.color = 'var(--accent-green)';
        btn.style.borderColor = 'var(--accent-green)';
        setTimeout(() => {
            btn.innerText = origText;
            btn.style.color = '';
            btn.style.borderColor = '';
        }, 2200);
    }).catch(err => {
        console.error('Failed to copy code: ', err);
    });
}

// ───────── 5. DIAGRAM FORMAT SWITCHER (SVG vs PNG) ─────────
function switchDiagramFormat(format) {
    const previewImg = document.getElementById('previewDiagramImg');
    const lightboxImg = document.getElementById('lightboxImg');
    const btnSvg = document.getElementById('btnSvg');
    const btnPng = document.getElementById('btnPng');

    if (format === 'svg') {
        previewImg.src = 'assets/Anemo-system-design.svg';
        lightboxImg.src = 'assets/Anemo-system-design.svg';
        if (btnSvg) btnSvg.classList.add('active');
        if (btnPng) btnPng.classList.remove('active');
    } else {
        previewImg.src = 'assets/Anemo-system-design.png';
        lightboxImg.src = 'assets/Anemo-system-design.png';
        if (btnPng) btnPng.classList.add('active');
        if (btnSvg) btnSvg.classList.remove('active');
    }
}

// ───────── 6. LIGHTBOX MODAL & ZOOM CONTROLS ─────────
let currentZoom = 1.0;
const lightboxOverlay = document.getElementById('lightboxOverlay');
const lightboxImg = document.getElementById('lightboxImg');

function openLightbox() {
    currentZoom = 1.0;
    updateZoom();
    lightboxOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    lightboxOverlay.classList.remove('active');
    document.body.style.overflow = 'auto';
}

function closeLightboxOnBackdrop(e) {
    if (e.target === lightboxOverlay || e.target.id === 'imgWrapper') {
        closeLightbox();
    }
}

function zoomIn() {
    currentZoom = Math.min(currentZoom + 0.35, 4.0);
    updateZoom();
}

function zoomOut() {
    currentZoom = Math.max(currentZoom - 0.35, 0.4);
    updateZoom();
}

function resetZoom() {
    currentZoom = 1.0;
    updateZoom();
}

function updateZoom() {
    lightboxImg.style.transform = `scale(${currentZoom})`;
}

// Keyboard Shortcut: Escape to close lightbox
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && lightboxOverlay.classList.contains('active')) {
        closeLightbox();
    }
});

// ───────── 7. SCROLL-TRIGGERED NUMBER COUNTER ANIMATION ─────────
function animateCounter(el, force = false) {
    if (el.dataset.animated === 'true' && !force) return;
    el.dataset.animated = 'true';

    const targetVal = parseFloat(el.getAttribute('data-counter'));
    if (isNaN(targetVal)) return;

    const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
    const suffix = el.getAttribute('data-suffix') || '';
    const prefix = el.getAttribute('data-prefix') || '';
    const useSeparator = el.getAttribute('data-separator') === ',';
    const duration = parseInt(el.getAttribute('data-duration') || '1300', 10);

    const startTime = performance.now();

    function formatNumber(num) {
        let str = num.toFixed(decimals);
        if (useSeparator) {
            const parts = str.split('.');
            parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
            str = parts.join('.');
        }
        return prefix + str + suffix;
    }

    function update(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1.0);
        // easeOutCubic curve for smooth decelerating count-up
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const currentVal = targetVal * easeOut;

        el.textContent = formatNumber(progress === 1.0 ? targetVal : currentVal);

        if (progress < 1.0) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// ───────── 8. SCROLL-TRIGGERED LATENCY BAR ANIMATION ─────────
function animateLatencyBar(bar) {
    if (bar.dataset.animated === 'true') return;
    bar.dataset.animated = 'true';
    const targetWidth = bar.getAttribute('data-width') || '0%';
    requestAnimationFrame(() => {
        bar.style.width = targetWidth;
    });
}

// ───────── 9. INTERSECTION OBSERVER SETUP ─────────
function initScrollAnimations() {
    const counterElements = document.querySelectorAll('[data-counter]');
    const barElements = document.querySelectorAll('.latency-fill[data-width]');
    const revealElements = document.querySelectorAll('.reveal-on-scroll');

    if ('IntersectionObserver' in window) {
        const counterObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        counterElements.forEach(el => counterObserver.observe(el));

        const barObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateLatencyBar(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        barElements.forEach(bar => barObserver.observe(bar));

        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08 });

        revealElements.forEach(el => revealObserver.observe(el));
    } else {
        // Fallback for environments without IntersectionObserver
        counterElements.forEach(el => animateCounter(el));
        barElements.forEach(bar => animateLatencyBar(bar));
        revealElements.forEach(el => el.classList.add('revealed'));
    }
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initScrollAnimations);
} else {
    initScrollAnimations();
}
