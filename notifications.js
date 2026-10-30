// Polls a lightweight summary endpoint and toggles the red-dot badges next
// to "Messages" and "Requests" in the nav bar when there's something new.
document.addEventListener("DOMContentLoaded", () => {
    const messagesBadge = document.getElementById("messages-badge");
    const requestsBadge = document.getElementById("requests-badge");
    if (!messagesBadge && !requestsBadge) return;

    function setBadge(el, count) {
        if (!el) return;
        el.style.display = count > 0 ? "inline-block" : "none";
    }

    async function refresh() {
        try {
            const res = await fetch("/messages/notifications/summary");
            if (!res.ok) return;
            const data = await res.json();
            setBadge(messagesBadge, data.unread_messages);
            setBadge(requestsBadge, data.pending_requests);
        } catch (err) {
            // Ignore transient network errors; the next poll will retry.
        }
    }

    refresh();
    setInterval(refresh, 10000);
});
