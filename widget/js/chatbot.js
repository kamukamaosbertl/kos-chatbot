/* KOS portfolio chatbot widget
 * Add to index.html, just before </body>:
 *   <link href="css/chatbot.css" rel="stylesheet">
 *   <script src="js/chatbot.js" data-api="https://YOUR-API.onrender.com"></script>
 */
(function () {
    "use strict";

    var script = document.currentScript;
    var API = ((script && script.getAttribute("data-api")) || "").replace(/\/+$/, "");
    var WHATSAPP = "https://wa.me/256793702186";
    var SUGGESTIONS = ["What are your skills?", "Show me your projects", "What linen products do you sell?", "How can I hire you?"];
    var history = [];      // [{role, content}] kept in memory for this visit only
    var busy = false;

    // ---------- build the widget ----------
    function el(tag, cls, text) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        if (text) e.textContent = text;
        return e;
    }

    var launcher = el("button", "kos-chat-launcher");
    launcher.type = "button";
    launcher.setAttribute("aria-label", "Open chat");
    launcher.innerHTML = '<i class="fa fa-comment-dots" aria-hidden="true"></i><i class="fa fa-times" aria-hidden="true"></i>';

    var panel = el("div", "kos-chat-panel");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Chat with Osbert's assistant");
    panel.hidden = true;

    var head = el("div", "kos-chat-head");
    var avatar = el("span", "kos-chat-avatar", "KOS");
    var titles = el("div", "kos-chat-titles");
    titles.appendChild(el("strong", "", "Ask Osbert's assistant"));
    titles.appendChild(el("span", "", "Usually replies in seconds"));
    var close = el("button", "kos-chat-close");
    close.type = "button";
    close.setAttribute("aria-label", "Close chat");
    close.innerHTML = '<i class="fa fa-times" aria-hidden="true"></i>';
    head.appendChild(avatar); head.appendChild(titles); head.appendChild(close);

    var log = el("div", "kos-chat-log");
    log.setAttribute("aria-live", "polite");

    var chips = el("div", "kos-chat-chips");
    SUGGESTIONS.forEach(function (s) {
        var c = el("button", "kos-chat-chip", s);
        c.type = "button";
        c.addEventListener("click", function () { send(s); });
        chips.appendChild(c);
    });

    var form = el("form", "kos-chat-form");
    var input = el("input", "kos-chat-input");
    input.type = "text";
    input.maxLength = 500;
    input.placeholder = "Type your question…";
    input.setAttribute("aria-label", "Your message");
    var sendBtn = el("button", "kos-chat-send");
    sendBtn.type = "submit";
    sendBtn.setAttribute("aria-label", "Send");
    sendBtn.innerHTML = '<i class="fa fa-paper-plane" aria-hidden="true"></i>';
    form.appendChild(input); form.appendChild(sendBtn);

    var foot = el("div", "kos-chat-foot");
    var wa = el("a", "", "Prefer a human? Chat on WhatsApp");
    wa.href = WHATSAPP; wa.target = "_blank"; wa.rel = "noopener";
    foot.appendChild(wa);

    panel.appendChild(head); panel.appendChild(log); panel.appendChild(chips);
    panel.appendChild(form); panel.appendChild(foot);
    document.body.appendChild(panel);
    document.body.appendChild(launcher);

    // ---------- messages ----------
    // Bot text is inserted as plain text; only http(s) links are turned into real links.
    function addMessage(role, text) {
        var bubble = el("div", "kos-msg kos-msg-" + role);
        var parts = String(text).split(/(https?:\/\/[^\s)]+)/g);
        parts.forEach(function (part, i) {
            if (i % 2 === 1) {
                var url = part.replace(/[.,!?;:]+$/, "");
                var a = el("a", "", url.replace(/^https?:\/\/(www\.)?/, ""));
                a.href = url; a.target = "_blank"; a.rel = "noopener";
                bubble.appendChild(a);
                if (url.length < part.length) bubble.appendChild(document.createTextNode(part.slice(url.length)));
            } else if (part) {
                bubble.appendChild(document.createTextNode(part));
            }
        });
        log.appendChild(bubble);
        log.scrollTop = log.scrollHeight;
        return bubble;
    }

    function typing() {
        var t = el("div", "kos-msg kos-msg-bot kos-typing");
        t.innerHTML = "<span></span><span></span><span></span>";
        log.appendChild(t);
        log.scrollTop = log.scrollHeight;
        return t;
    }

    function setBusy(state) {
        busy = state;
        input.disabled = state;
        sendBtn.disabled = state;
    }

    function send(text) {
        text = (text || "").trim();
        if (!text || busy) return;
        chips.hidden = true;
        addMessage("user", text);
        input.value = "";
        setBusy(true);
        var dots = typing();

        // free hosting sleeps when idle; tell the visitor if the first reply is slow
        var slow = setTimeout(function () {
            dots.setAttribute("data-note", "Waking up the assistant, this can take up to a minute the first time…");
        }, 6000);
        var controller = window.AbortController ? new AbortController() : null;
        var timeout = setTimeout(function () { if (controller) controller.abort(); }, 70000);

        fetch(API + "/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text, history: history.slice(-6) }),
            signal: controller ? controller.signal : undefined
        })
            .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
            .then(function (data) {
                var reply = data && data.reply ? data.reply : "Sorry, I didn't get that.";
                dots.remove();
                addMessage("bot", reply);
                history.push({ role: "user", content: text }, { role: "assistant", content: reply });
            })
            .catch(function () {
                dots.remove();
                addMessage("bot", "Sorry, I can't connect right now. Please reach Osbert on WhatsApp: " + WHATSAPP);
            })
            .then(function () {
                clearTimeout(slow); clearTimeout(timeout);
                setBusy(false);
                input.focus();
            });
    }

    // ---------- open / close ----------
    var greeted = false;
    function open() {
        panel.hidden = false;
        launcher.classList.add("is-open");
        launcher.setAttribute("aria-label", "Close chat");
        document.body.classList.add("kos-chat-open");
        if (!greeted) {
            addMessage("bot", "Hi! 👋 I'm Osbert's assistant. Ask me about his skills, projects and services, or about Virtual Room Beddings & Comfort.");
            greeted = true;
            if (API) fetch(API + "/health").catch(function () {});   // wake the server early
        }
        setTimeout(function () { input.focus(); }, 50);
    }
    function shut() {
        panel.hidden = true;
        launcher.classList.remove("is-open");
        launcher.setAttribute("aria-label", "Open chat");
        document.body.classList.remove("kos-chat-open");
        launcher.focus();
    }

    launcher.addEventListener("click", function () { panel.hidden ? open() : shut(); });
    close.addEventListener("click", shut);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !panel.hidden) shut(); });
    form.addEventListener("submit", function (e) { e.preventDefault(); send(input.value); });

    if (!API) {
        console.warn("KOS chatbot: add data-api=\"https://your-api-url\" to the chatbot.js script tag.");
    }
})();
