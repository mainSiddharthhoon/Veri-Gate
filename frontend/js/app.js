/**
 * ============================================================================
 * VeriGate — Application Routing & Bootstrap
 * View-state transitions with overlay support for processing and results.
 * ============================================================================
 */

let currentView = 'landing';

/**
 * Navigate between views.
 * 'landing' — scrollable page (default)
 * 'screen'  — scroll to the screening section within the page
 * 'processing' — full-screen overlay
 * 'results' — full-screen overlay
 */
function go(view) {
  if (view === 'screen') {
    closeOverlays();
    currentView = 'landing';
    const section = document.getElementById('screening');
    if (section) {
      section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setTimeout(() => {
        const slot = document.getElementById('slotDoc');
        if (slot && !session.doc) {
          gsap.fromTo(slot, { scale: 1.03 }, { scale: 1, duration: 0.4, ease: 'power2.out' });
        }
      }, 500);
    }
    return;
  }

  if (view === 'processing') {
    startScreeningProcess();
    const section = document.getElementById('screening');
    if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }

  if (view === 'results') {
    if (session.report && typeof renderDynamicResults === 'function') {
      renderDynamicResults(session.report);
      const section = document.getElementById('screening');
      if (section) section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    return;
  }

  if (view === 'landing') {
    closeOverlays();
    currentView = 'landing';
    window.scrollTo({ top: 0, behavior: 'smooth' });
    return;
  }
}

function closeOverlays() {
  document.body.style.overflow = '';
}

/**
 * Hero video fallback for missing mp4.
 */
function setupHeroVideo() {
  const video = document.getElementById('heroVideo');
  const fallback = document.getElementById('heroFallback');
  if (!video || !fallback) return;

  video.addEventListener('error', () => {
    video.style.display = 'none';
    fallback.style.display = 'flex';
  });
  fallback.style.display = 'none';
}

/**
 * Bootstrap on DOMContentLoaded.
 */
document.addEventListener('DOMContentLoaded', () => {
  setupHeroVideo();
  setupUploadPanels();

  if (typeof initAllAnimations === 'function') {
    initAllAnimations();
  }

  if (typeof checkServerConnection === 'function') {
    checkServerConnection();
  }
});
