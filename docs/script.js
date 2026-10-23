/**
 * AnemoDB Documentation Interactive Client Script
 * Handles lightbox zooming, clipboard copying, benchmark tab switching,
 * code language tab switching, architecture inspector interactions,
 * scroll-triggered counter/bar animations, the mobile navigation menu,
 * responsive table labels, and code snippet syntax highlighting.
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
        text.innerHTML = '<i class="bi bi-check-lg" aria-hidden="true"></i> Copied to Clipboard!';

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
        icon: "lightning-charge-fill",
        title: "Stage 1: Non-Blocking Network Listener",
        desc: "The listener runs on a dedicated POSIX thread bound to port 8080. When a client connects, the listener immediately performs accept() and delegates the raw socket descriptor into the bounded task queue. Because reading is performed asynchronously by worker threads, slow or hanging clients can never stall the server's ability to accept new connections. If the queue is saturated, it replies with [ERROR] SERVER_BUSY_QUEUE_FULL instantly."
    },
    {
        icon: "box-seam-fill",
        title: "Stage 2: Bounded Task Queue (ThreadSafeQueue)",
        desc: "An internal producer-consumer queue with a default capacity of 5,000 tasks. It uses std::mutex and std::condition_variable for sleep-wakeup signaling. Tasks are moved with C++17 move semantics (zero memory copies). When under peak burst pressure, excess requests are rejected fast, protecting the server against out-of-memory crashes."
    },
    {
        icon: "tornado",
        title: "Stage 3: Request Coalescing (Single-Flight LRU Cache)",
        desc: "When multiple worker threads miss the cache on the exact same query concurrently (e.g., during a traffic spike), the first worker becomes the LEADER and marks the cache node IN_PROGRESS. All subsequent threads become FOLLOWERS and sleep on the node's condition variable. The leader queries PostgreSQL once, populates the value, and calls notify_all()—satisfying all 500 requests with a single database trip!"
    },
    {
        icon: "database-fill-check",
        title: "Stage 4: Resilient PostgreSQL Connection Pool",
        desc: "A pre-warmed pool of persistent libpqxx connections matching the worker thread count. On misses, workers acquire a connection with a 5-second timeout. Connections are health-checked with auto-reconnection if idle sockets drop. Queries are executed strictly within a pqxx::read_transaction scope, ensuring complete read-only safety."
    }
];

function inspectStage(index) {
    document.querySelectorAll('.arch-node').forEach((node, i) => {
        node.classList.toggle('active', i === index);
    });
    const title = document.getElementById('inspectorTitle');
    title.innerHTML = `<i class="bi bi-${stages[index].icon}" aria-hidden="true"></i> `;
    title.append(stages[index].title);
    document.getElementById('inspectorDesc').innerText = stages[index].desc;

    // Restart the swap-in animation: drop the class, force a reflow, add it back
    const box = document.getElementById('inspectorBox');
    box.classList.remove('inspector-swap');
    void box.offsetWidth;
    box.classList.add('inspector-swap');
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
    const tabs = ['python', 'node', 'go', 'bash', 'cpp', 'java', 'rust'];
    document.querySelectorAll('.code-tab-btn').forEach((btn, i) => {
        const onclickAttr = btn.getAttribute('onclick') || '';
        btn.classList.toggle('active', onclickAttr.includes(`'${lang}'`) || tabs[i] === lang);
    });
    document.querySelectorAll('.code-pane').forEach(pane => {
        pane.classList.toggle('active', pane.id === `codePane-${lang}`);
    });
}

function copySnippet(snippetId, btn) {
    const el = document.getElementById(snippetId);
    if (!el) return;
    const textToCopy = el.innerText;
    navigator.clipboard.writeText(textToCopy).then(() => {
        const origText = btn.innerText;
        btn.innerHTML = '<i class="bi bi-check-lg" aria-hidden="true"></i> Copied!';
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
const imgWrapper = document.getElementById('imgWrapper');

function openLightbox() {
    currentZoom = 1.0;
    lightboxOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    // Size after the overlay is visible so the wrapper has real dimensions
    updateZoom();
}

function closeLightbox() {
    lightboxOverlay.classList.remove('active');
    document.body.style.overflow = '';
}

function closeLightboxOnBackdrop(e) {
    if (dragMoved) return;
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
    // At 1.0 the whole diagram fits inside the wrapper; zooming widens the image
    // itself so the overflow stays scrollable in every direction.
    const ratio = lightboxImg.naturalHeight ? lightboxImg.naturalWidth / lightboxImg.naturalHeight : 0;
    const fitWidth = ratio
        ? Math.min(imgWrapper.clientWidth, imgWrapper.clientHeight * ratio)
        : imgWrapper.clientWidth;
    lightboxImg.style.width = `${Math.round(fitWidth * currentZoom)}px`;
}

// Re-fit whenever the wrapper itself changes size (window resize, rotation,
// mobile browser chrome showing or hiding)
if ('ResizeObserver' in window) {
    new ResizeObserver(() => {
        if (lightboxOverlay.classList.contains('active')) updateZoom();
    }).observe(imgWrapper);
}

// Mouse drag-to-pan (touch devices scroll the wrapper natively)
let dragStart = null;
let dragMoved = false;

imgWrapper.addEventListener('mousedown', (e) => {
    dragStart = { x: e.clientX, y: e.clientY, left: imgWrapper.scrollLeft, top: imgWrapper.scrollTop };
    dragMoved = false;
    e.preventDefault();
});

window.addEventListener('mousemove', (e) => {
    if (!dragStart) return;
    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) dragMoved = true;
    imgWrapper.scrollLeft = dragStart.left - dx;
    imgWrapper.scrollTop = dragStart.top - dy;
});

window.addEventListener('mouseup', () => {
    dragStart = null;
    // Cleared after the click event that follows mouseup has been handled
    setTimeout(() => { dragMoved = false; }, 0);
});

// Keyboard Shortcut: Escape to close lightbox / mobile nav
document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (lightboxOverlay.classList.contains('active')) {
        closeLightbox();
    } else {
        closeNav();
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

        // Cards that share a grid reveal one after another instead of all at once
        document.querySelectorAll('.arch-flow-grid, .metrics-cards-grid, .features-grid, .db-grid').forEach(grid => {
            Array.from(grid.children).forEach((card, i) => {
                card.dataset.revealDelay = String(i * 80);
            });
        });

        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const delay = parseInt(el.dataset.revealDelay || '0', 10);
                    el.style.transitionDelay = `${delay}ms`;
                    el.classList.add('revealed');
                    observer.unobserve(el);
                    // Once revealed, hand the element back to its own hover transition
                    setTimeout(() => {
                        el.classList.remove('reveal-on-scroll', 'revealed');
                        el.style.transitionDelay = '';
                    }, delay + 800);
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

// ───────── 10. MOBILE NAVIGATION MENU ─────────
const siteHeader = document.getElementById('siteHeader');
const navToggle = document.getElementById('navToggle');

function toggleNav() {
    const isOpen = siteHeader.classList.toggle('nav-open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
}

function closeNav() {
    siteHeader.classList.remove('nav-open');
    navToggle.setAttribute('aria-expanded', 'false');
}

// Header gains a solid backdrop and shadow once the page leaves the top
function updateHeaderShadow() {
    siteHeader.classList.toggle('scrolled', window.scrollY > 8);
}

window.addEventListener('scroll', updateHeaderShadow, { passive: true });
updateHeaderShadow();

// Close the menu after picking a link or tapping outside the header
document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', closeNav);
});

document.addEventListener('click', (e) => {
    if (!siteHeader.contains(e.target)) closeNav();
});

// ───────── 11. RESPONSIVE TABLE LABELS ─────────
// Copies each column header onto its cells so the stacked mobile layout
// (see RESPONSIVE in style.css) can label every value.
function initTableLabels() {
    document.querySelectorAll('.comparison-table-wrap table').forEach(table => {
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        table.querySelectorAll('tbody tr').forEach(row => {
            Array.from(row.children).forEach((cell, i) => {
                cell.setAttribute('data-label', headers[i] || '');
            });
        });
    });
}

// ───────── 12. SYNTAX HIGHLIGHTING ─────────
// Each pattern captures, in order: (1) comment, (2) string, (3) number, (4) identifier.
// Colours come from the .tok-* classes in style.css.
const highlightLangs = {
    python: {
        pattern: /(#.*)|("""[\s\S]*?"""|[fbr]{0,2}(?:"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'))|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)/g,
        keywords: ['import', 'from', 'def', 'return', 'with', 'as', 'while', 'for', 'if', 'elif', 'else', 'not', 'in', 'and', 'or', 'break', 'continue', 'pass', 'True', 'False', 'None'],
        builtins: ['str', 'int', 'float', 'bytes', 'print', 'len']
    },
    node: {
        pattern: /(\/\/.*)|("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_$][\w$]*)/g,
        keywords: ['const', 'let', 'var', 'function', 'return', 'new', 'if', 'else', 'async', 'await', 'true', 'false', 'null', 'undefined'],
        builtins: ['require', 'Promise', 'console']
    },
    go: {
        pattern: /(\/\/.*)|("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`[^`]*`)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)/g,
        keywords: ['package', 'import', 'func', 'return', 'if', 'else', 'for', 'range', 'defer', 'var', 'const', 'type', 'struct', 'nil', 'true', 'false'],
        builtins: ['string', 'error', 'int', 'bool', 'byte']
    },
    bash: {
        pattern: /(#.*)|("(?:\\.|[^"\\\n])*"|'[^'\n]*')|(\b\d+\b)|([A-Za-z_][\w-]*)/g,
        keywords: [],
        builtins: ['echo'],
        commands: ['nc']
    },
    cpp: {
        pattern: /(\/\/.*)|("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')|(\b\d+(?:\.\d+)?\b)|(#\w+|[A-Za-z_]\w*)/g,
        keywords: ['#include', 'const', 'int', 'char', 'void', 'return', 'if', 'else', 'while', 'for', 'struct', 'sizeof', 'new', 'delete', 'true', 'false', 'nullptr'],
        builtins: ['std', 'string', 'cout', 'endl', 'size_t', 'socket', 'sockaddr_in', 'AF_INET', 'SOCK_STREAM', 'htons', 'inet_pton', 'connect', 'send', 'read', 'close']
    },
    java: {
        pattern: /(\/\/.*)|("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)/g,
        keywords: ['import', 'public', 'class', 'static', 'void', 'throws', 'try', 'catch', 'new', 'return', 'if', 'while', 'for', 'byte', 'int', 'true', 'false', 'null'],
        builtins: ['String', 'Socket', 'OutputStream', 'InputStream', 'StandardCharsets', 'StringBuilder', 'Exception', 'System']
    },
    rust: {
        pattern: /(\/\/.*)|("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)/g,
        keywords: ['use', 'fn', 'let', 'mut', 'loop', 'match', 'if', 'else', 'break', 'return', 'pub', 'struct', 'impl'],
        builtins: ['std', 'io', 'net', 'TcpStream', 'Result', 'String', 'Ok', 'Err', 'println', 'eprintln', 'format']
    }
};

function escapeHtml(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function highlightCode(source, lang) {
    const { pattern, keywords, builtins, commands = [] } = highlightLangs[lang];
    const wrap = (cls, text) => `<span class="${cls}">${escapeHtml(text)}</span>`;
    let html = '';
    let last = 0;

    pattern.lastIndex = 0;
    let match;
    while ((match = pattern.exec(source)) !== null) {
        html += escapeHtml(source.slice(last, match.index));
        last = pattern.lastIndex;

        const [text, comment, string, number, ident] = match;
        if (comment) {
            html += wrap('tok-comment', text);
        } else if (string) {
            html += wrap('tok-str', text);
        } else if (number) {
            html += wrap('tok-num', text);
        } else if (keywords.includes(ident)) {
            html += wrap('tok-kw', text);
        } else if (builtins.includes(ident)) {
            html += wrap('tok-builtin', text);
        } else if (commands.includes(ident) || source[last] === '(') {
            html += wrap('tok-fn', text);
        } else {
            html += escapeHtml(text);
        }
    }

    return html + escapeHtml(source.slice(last));
}

function initSyntaxHighlight() {
    Object.keys(highlightLangs).forEach(lang => {
        const code = document.querySelector(`#codeSnippet-${lang} code`);
        if (code) code.innerHTML = highlightCode(code.textContent, lang);
    });
}

// Initialize on DOM ready
function init() {
    initSyntaxHighlight();
    initTableLabels();
    initScrollAnimations();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
