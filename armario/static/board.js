// Optional pointer interaction. Numeric fields remain the keyboard/no-script alternative.
document.querySelectorAll('[data-board-item]').forEach((item) => {
  const form = document.getElementById(`board-form-${item.dataset.boardItem}`);
  const handle = item.querySelector('.board-drag');
  if (!form || !handle) return;
  let start = null;
  handle.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    start = {x: event.clientX, y: event.clientY, left: Number(form.elements.x.value), top: Number(form.elements.y.value), moved: false};
    handle.setPointerCapture(event.pointerId);
  });
  handle.addEventListener('pointermove', (event) => {
    if (!start) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (Math.abs(dx) + Math.abs(dy) < 4 && !start.moved) return;
    start.moved = true;
    const x = Math.max(0, Math.min(2000, Math.round(start.left + dx)));
    const y = Math.max(0, Math.min(2000, Math.round(start.top + dy)));
    item.style.left = `${x}px`;
    item.style.top = `${y}px`;
    form.elements.x.value = x;
    form.elements.y.value = y;
  });
  handle.addEventListener('pointerup', () => {
    if (start && start.moved) form.requestSubmit();
    start = null;
  });
  handle.addEventListener('pointercancel', () => { start = null; });
});
