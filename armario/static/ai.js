// Progressive enhancement only: normal links and forms remain fully functional.
const statusNode = document.querySelector("[data-ai-poll]");
if (statusNode) {
  let remaining = 120;
  const poll = async () => {
    if (remaining-- <= 0) return;
    try {
      const response = await fetch(statusNode.dataset.aiPoll, {
        credentials: "same-origin",
        cache: "no-store",
        signal: AbortSignal.timeout(4000),
      });
      if (!response.ok) return;
      const result = await response.json();
      if (result.status !== statusNode.dataset.aiStatus) {
        window.location.reload();
        return;
      }
    } catch {
      // An unavailable server does not prevent manual refresh or navigation.
    }
    window.setTimeout(poll, 5000);
  };
  window.setTimeout(poll, 5000);
}
