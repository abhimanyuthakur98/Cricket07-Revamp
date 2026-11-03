const layouts = new WeakMap();

// Shared by selection ratings and the broadcast. The canvas always fills the
// stage; put the broadcast below the native gauge without shrinking the game.
export function attachGameLayout(stage) {
  let layout = layouts.get(stage);
  if (!layout) {
    const resize = () => {
      if (!stage.clientHeight || !stage.clientWidth) return;
      // The gauge ends at y=406/480 after removing its ball icons. A 13%-high
      // strip with a 1% bottom inset starts at y=412.8, leaving it clear.
      stage.style.setProperty('--broadcast-height', `${stage.clientHeight * .13}px`);
      // Keep the type readable across the full width, and fit short/wide stages.
      const unit = Math.min(stage.clientWidth * .0096, stage.clientHeight * .0170667);
      stage.style.setProperty('--broadcast-unit', `${unit}px`);
    };
    const observer = new ResizeObserver(resize);
    stage.classList.add('revamp-stage');
    observer.observe(stage);resize();
    layout = {users:0, observer};layouts.set(stage, layout);
  }
  layout.users++;
  return () => {
    if (--layout.users) return;
    layout.observer.disconnect();layouts.delete(stage);
    stage.classList.remove('revamp-stage');
    stage.style.removeProperty('--broadcast-height');stage.style.removeProperty('--broadcast-unit');
  };
}
