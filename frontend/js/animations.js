/**
 * ============================================================================
 * VeriGate — Animations & Particle System
 * GSAP timelines, ScrollTrigger, mouse-reactive particle canvas
 * ============================================================================
 */

if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

/* ── Particle System ── */
function initParticles() {
  const canvas = document.getElementById('particleCanvas');
  if (!canvas) return;

  // Respect reduced-motion preferences
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    canvas.style.display = 'none';
    return;
  }

  const ctx = canvas.getContext('2d');
  let w, h, particles = [], mouse = { x: -1000, y: -1000 };
  let isParticleLoopActive = true;
  let animFrameId = null;

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
  }
  resize();

  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(resize, 150);
  }, { passive: true });

  document.addEventListener('mousemove', e => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
  }, { passive: true });

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x = Math.random() * w;
      this.y = Math.random() * h;
      this.size = Math.random() * 1.5 + 0.3;
      this.speedX = (Math.random() - 0.5) * 0.3;
      this.speedY = (Math.random() - 0.5) * 0.3;
      this.opacity = Math.random() * 0.3 + 0.05;
    }
    update() {
      this.x += this.speedX;
      this.y += this.speedY;

      const dx = mouse.x - this.x;
      const dy = mouse.y - this.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 150) {
        const force = (150 - dist) / 150;
        this.x -= dx * force * 0.01;
        this.y -= dy * force * 0.01;
        this.opacity = Math.min(0.6, this.opacity + force * 0.02);
      } else {
        this.opacity += (0.1 - this.opacity) * 0.01;
      }

      if (this.x < -10 || this.x > w + 10 || this.y < -10 || this.y > h + 10) {
        this.reset();
      }
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(248, 81, 73, ${this.opacity})`;
      ctx.fill();
    }
  }

  const count = Math.min(60, Math.floor((w * h) / 18000));
  for (let i = 0; i < count; i++) particles.push(new Particle());

  function animate() {
    if (!isParticleLoopActive) return;

    ctx.clearRect(0, 0, w, h);
    particles.forEach(p => { p.update(); p.draw(); });

    // Draw connections
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 110) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(248, 81, 73, ${0.04 * (1 - dist / 110)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    animFrameId = requestAnimationFrame(animate);
  }

  function startLoop() {
    if (!isParticleLoopActive) {
      isParticleLoopActive = true;
      animFrameId = requestAnimationFrame(animate);
    }
  }

  function stopLoop() {
    isParticleLoopActive = false;
    if (animFrameId) {
      cancelAnimationFrame(animFrameId);
      animFrameId = null;
    }
  }

  // Pause when tab is inactive
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stopLoop();
    else if (window.scrollY < window.innerHeight * 1.5) startLoop();
  });

  // Pause when user scrolled past hero section
  window.addEventListener('scroll', () => {
    if (window.scrollY > window.innerHeight * 1.8) {
      if (isParticleLoopActive) stopLoop();
    } else {
      if (!isParticleLoopActive && !document.hidden) startLoop();
    }
  }, { passive: true });

  animate();
}

/* ── Navbar Scroll Response ── */
function initNavbarScroll() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;
  const links = navbar.querySelectorAll('.nav-links a[data-section]');
  const sections = document.querySelectorAll('section[id]');

  let isScrollTicking = false;
  window.addEventListener('scroll', () => {
    if (!isScrollTicking) {
      requestAnimationFrame(() => {
        navbar.classList.toggle('scrolled', window.scrollY > 60);

        // Active section highlighting
        let current = '';
        const scrollPos = window.scrollY + 220;
        for (let i = 0; i < sections.length; i++) {
          const sec = sections[i];
          if (sec.offsetTop <= scrollPos) current = sec.id;
        }
        links.forEach(a => {
          a.classList.toggle('active-link', a.dataset.section === current);
        });
        isScrollTicking = false;
      });
      isScrollTicking = true;
    }
  }, { passive: true });
}

/* ── Apple Glass Water Physics & Magnetic Floating Buttons ── */
function initWaterButtons() {
  const buttons = document.querySelectorAll(
    '.btn-glass-primary, .btn-glass-secondary, .btn-nav-glass, .btn-primary, .btn-secondary, .btn-nav-cta, .nav-links a'
  );

  buttons.forEach(btn => {
    // Mouse movement inside button -> update liquid blob origin & magnetic tactile pull
    btn.addEventListener('mousemove', e => {
      const rect = btn.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Update liquid blob coordinates
      btn.style.setProperty('--mouse-x', `${x}px`);
      btn.style.setProperty('--mouse-y', `${y}px`);

      // Gentle magnetic tactile pull towards cursor (Apple VisionOS feel)
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const deltaX = (x - centerX) * 0.22;
      const deltaY = (y - centerY) * 0.22;

      if (typeof gsap !== 'undefined') {
        gsap.to(btn, {
          x: deltaX,
          y: deltaY,
          duration: 0.3,
          ease: 'power2.out',
          overwrite: 'auto'
        });
      }
    });

    // Mouse leave -> spring back to equilibrium smoothly
    btn.addEventListener('mouseleave', () => {
      if (typeof gsap !== 'undefined') {
        gsap.to(btn, {
          x: 0,
          y: 0,
          duration: 0.65,
          ease: 'elastic.out(1.1, 0.4)',
          overwrite: 'auto'
        });
      }
    });

    // Click -> Water droplet ripple wave radiating from pointer
    btn.addEventListener('click', e => {
      const rect = btn.getBoundingClientRect();
      const ripple = document.createElement('span');
      ripple.className = 'water-ripple';
      ripple.style.setProperty('--ripple-x', `${e.clientX - rect.left}px`);
      ripple.style.setProperty('--ripple-y', `${e.clientY - rect.top}px`);
      btn.appendChild(ripple);

      ripple.addEventListener('animationend', () => ripple.remove());
    });
  });
}

/* ── Hero Cinematic Entrance Animations ── */
function initHeroAnimations() {
  if (typeof gsap === 'undefined') return;

  const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

  // Floating Water Navbar entrance
  gsap.fromTo('.navbar', 
    { opacity: 0, y: -25, scale: 0.97 }, 
    { opacity: 1, y: 0, scale: 1, duration: 1.1, delay: 0.15, ease: 'power3.out' }
  );

  // Left-aligned hero entrance with razor-sharp stagger and blur dissipation
  const isMobileHero = typeof window !== 'undefined' && window.innerWidth <= 768;
  tl.fromTo('.hero-eyebrow', 
      { opacity: 0, x: isMobileHero ? 0 : -30, y: isMobileHero ? 16 : 0, filter: 'blur(8px)' }, 
      { opacity: 1, x: 0, y: 0, filter: 'blur(0px)', duration: 0.85, delay: 0.2 }
    )
    .fromTo('.hero h1 .line', 
      { opacity: 0, y: 40, filter: 'blur(10px)' }, 
      { opacity: 1, y: 0, filter: 'blur(0px)', duration: 1.05, stagger: 0.16 }, 
      '-=0.45'
    )
    .fromTo('.hero-description', 
      { opacity: 0, y: 24 }, 
      { opacity: 1, y: 0, duration: 0.85 }, 
      '-=0.55'
    )
    .fromTo('.hero-ctas > *', 
      { opacity: 0, y: 20, scale: 0.94 }, 
      { opacity: 1, y: 0, scale: 1, duration: 0.75, stagger: 0.12, ease: 'back.out(1.5)' }, 
      '-=0.45'
    )
    .fromTo('.hero-showcase', 
      { opacity: 0, x: isMobileHero ? 0 : 40, y: isMobileHero ? 24 : 0, scale: 0.92, filter: 'blur(10px)' }, 
      { opacity: 1, x: 0, y: 0, scale: 1, filter: 'blur(0px)', duration: 0.95, ease: 'back.out(1.2)' }, 
      '-=0.45'
    );

  // Smooth Parallax on hero video
  if (typeof ScrollTrigger !== 'undefined') {
    gsap.to('.hero-video-wrap', {
      yPercent: 12,
      ease: 'none',
      scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: 0.6 }
    });
  }
}

/* ═══════════════════════════════════════════════════════════════════
   HERO RIGHT — 3D Glossy Card Flip Logic & Interactive Telemetry
   ═══════════════════════════════════════════════════════════════════ */
const HERO_METRIC_SLIDES = [
  {
    badge: 'DEFENSE ARCHITECTURE',
    index: '01 / 03',
    value: 'Rules + AI',
    title: 'Deterministic & Generative Defense',
    desc: 'Combines deterministic validation rules with vision-language models to verify documents and facial identity.',
    fill: '85%',
    metaL: 'RULES: DETERMINISTIC',
    metaR: 'ARBITER: GEMMA'
  },
  {
    badge: 'PIPELINE ARCHITECTURE',
    index: '02 / 03',
    value: '7-Stage',
    title: 'Sequential Evidence Analysis',
    desc: 'Input qualification, OCR, MRZ validation, rule verification, ELA forensics, biometric matching, and final synthesis.',
    fill: '100%',
    metaL: 'PIPELINE: ACTIVE',
    metaR: 'MULTI-STAGE'
  },
  {
    badge: 'EXPLAINABLE INTELLIGENCE',
    index: '03 / 03',
    value: 'Evidence',
    title: 'Itemized Evidence & Risk Reports',
    desc: 'Generates itemized risk factors, forensic evidence metrics, and reasoned verdicts rather than opaque pass/fail scores.',
    fill: '90%',
    metaL: 'REASONING: EXPLAINABLE',
    metaR: 'SYNTHESIS: EVIDENCE'
  }
];

let currentCardIndex = 0;
let isCardFlipping = false;

function renderCardSlide(idx) {
  const slide = HERO_METRIC_SLIDES[idx];
  if (!slide) return;

  const badgeEl = document.getElementById('cardBadgeText');
  const indexEl = document.getElementById('cardIndexText');
  const valEl = document.getElementById('cardValue');
  const titleEl = document.getElementById('cardTitle');
  const descEl = document.getElementById('cardDesc');
  const fillEl = document.getElementById('cardBarFill');
  const metaLEl = document.getElementById('cardMetaL');
  const metaREl = document.getElementById('cardMetaR');

  if (badgeEl) badgeEl.textContent = slide.badge;
  if (indexEl) indexEl.textContent = slide.index;
  if (valEl) valEl.textContent = slide.value;
  if (titleEl) titleEl.textContent = slide.title;
  if (descEl) descEl.textContent = slide.desc;
  if (fillEl) fillEl.style.width = slide.fill;
  if (metaLEl) metaLEl.textContent = slide.metaL;
  if (metaREl) metaREl.textContent = slide.metaR;

  // Update dots
  document.querySelectorAll('#cardDots .card-dot').forEach((dot, i) => {
    dot.classList.toggle('active', i === idx);
  });
}

function flipHeroCard(direction) {
  if (isCardFlipping) return;
  isCardFlipping = true;

  const card = document.getElementById('heroMetricCard');
  if (!card) {
    isCardFlipping = false;
    return;
  }

  const nextIdx = direction === 'next'
    ? (currentCardIndex + 1) % HERO_METRIC_SLIDES.length
    : (currentCardIndex - 1 + HERO_METRIC_SLIDES.length) % HERO_METRIC_SLIDES.length;

  const flipOutAngle = direction === 'next' ? -85 : 85;
  const flipInAngle = direction === 'next' ? 85 : -85;

  if (typeof gsap !== 'undefined') {
    gsap.timeline()
      .to(card, {
        rotationY: flipOutAngle,
        scale: 0.9,
        filter: 'blur(3px)',
        duration: 0.28,
        ease: 'power2.in',
        onComplete: () => {
          currentCardIndex = nextIdx;
          renderCardSlide(currentCardIndex);
          gsap.set(card, { rotationY: flipInAngle });
        }
      })
      .to(card, {
        rotationY: 0,
        scale: 1,
        filter: 'blur(0px)',
        duration: 0.45,
        ease: 'back.out(1.25)',
        onComplete: () => {
          isCardFlipping = false;
        }
      });
  } else {
    currentCardIndex = nextIdx;
    renderCardSlide(currentCardIndex);
    isCardFlipping = false;
  }
}

function initHeroCardShowcase() {
  const btnPrev = document.getElementById('btnCardPrev');
  const btnNext = document.getElementById('btnCardNext');
  const card = document.getElementById('heroMetricCard');

  if (btnPrev) {
    btnPrev.addEventListener('click', (e) => {
      e.stopPropagation();
      flipHeroCard('prev');
    });
  }

  if (btnNext) {
    btnNext.addEventListener('click', (e) => {
      e.stopPropagation();
      flipHeroCard('next');
    });
  }

  // Dot clicks
  document.querySelectorAll('#cardDots .card-dot').forEach((dot) => {
    dot.addEventListener('click', (e) => {
      e.stopPropagation();
      const targetIdx = parseInt(dot.getAttribute('data-index'), 10);
      if (isNaN(targetIdx) || targetIdx === currentCardIndex || isCardFlipping) return;
      const dir = targetIdx > currentCardIndex ? 'next' : 'prev';
      flipHeroCard(dir);
    });
  });

  // 3D Mouse Tilt effect on Card
  if (card && typeof gsap !== 'undefined') {
    card.addEventListener('mousemove', (e) => {
      if (isCardFlipping) return;
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      const tiltX = (y / (rect.height / 2)) * -6;
      const tiltY = (x / (rect.width / 2)) * 6;

      gsap.to(card, {
        rotationX: tiltX,
        rotationY: tiltY,
        duration: 0.35,
        ease: 'power1.out',
        overwrite: 'auto'
      });
    });

    card.addEventListener('mouseleave', () => {
      if (isCardFlipping) return;
      gsap.to(card, {
        rotationX: 0,
        rotationY: 0,
        duration: 0.6,
        ease: 'elastic.out(1, 0.4)',
        overwrite: 'auto'
      });
    });
  }
}

/* ── Problem Section — Center Fan-Out & 3D Interactive Cards ── */
function initProblemAnimations() {
  if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') return;

  // Animate problem header elements with cinematic blur dissipation
  gsap.fromTo('.problem-eyebrow', 
    { opacity: 0, y: 20 }, 
    { opacity: 1, y: 0, duration: 0.75, scrollTrigger: { trigger: '.problem', start: 'top 85%' } }
  );

  gsap.fromTo('.problem-title', 
    { opacity: 0, y: 35, filter: 'blur(10px)' }, 
    { opacity: 1, y: 0, filter: 'blur(0px)', duration: 1, ease: 'power3.out', scrollTrigger: { trigger: '.problem', start: 'top 80%' } }
  );

  gsap.fromTo('.problem-lead', 
    { opacity: 0, y: 24 }, 
    { opacity: 1, y: 0, duration: 0.85, ease: 'power3.out', scrollTrigger: { trigger: '.problem', start: 'top 75%' } }
  );

  const grid = document.getElementById('problemThreatsGrid');
  if (!grid) return;
  const cards = grid.querySelectorAll('.threat-card');
  if (!cards.length) return;

  // Center-to-Position Soft Floating Fan-Out Animation:
  // 60fps pure GPU-composited transform/opacity interpolation with zero filter-blur thrashing
  ScrollTrigger.create({
    trigger: grid,
    start: 'top 82%',
    once: true,
    onEnter: () => {
      const gridRect = grid.getBoundingClientRect();
      const gridCenterX = gridRect.left + gridRect.width / 2;
      const gridCenterY = gridRect.top + gridRect.height / 2;

      cards.forEach((card, i) => {
        const cardRect = card.getBoundingClientRect();
        const cardCenterX = cardRect.left + cardRect.width / 2;
        const cardCenterY = cardRect.top + cardRect.height / 2;

        // Smooth organic offset from center
        const deltaX = (gridCenterX - cardCenterX) * 0.28;
        const deltaY = (gridCenterY - cardCenterY) * 0.28;

        // Subtle, elegant organic fan angle
        const fanRotation = (i - 2.5) * 1.6; // -4deg to +4deg

        gsap.fromTo(card,
          {
            x: deltaX,
            y: deltaY,
            scale: 0.94,
            rotation: fanRotation,
            opacity: 0,
            force3D: true
          },
          {
            x: 0,
            y: 0,
            scale: 1,
            rotation: 0,
            opacity: 1,
            duration: 1.15,
            delay: i * 0.065,
            ease: 'power3.out',
            force3D: true,
            onComplete: () => {
              // Clear transform properties cleanly so mouse interaction has absolute 0 base
              gsap.set(card, { clearProps: 'transform' });
            }
          }
        );
      });
    }
  });

  // 60fps Fluid 3D Interactive Mouse Tilt & Cursor Spotlight Tracking
  cards.forEach(card => {
    card.addEventListener('mousemove', e => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;

      // Update spotlight position CSS variables
      const mouseXPct = ((e.clientX - rect.left) / rect.width) * 100;
      const mouseYPct = ((e.clientY - rect.top) / rect.height) * 100;
      card.style.setProperty('--card-mouse-x', `${mouseXPct.toFixed(1)}%`);
      card.style.setProperty('--card-mouse-y', `${mouseYPct.toFixed(1)}%`);

      const tiltX = (y / (rect.height / 2)) * -4.5;
      const tiltY = (x / (rect.width / 2)) * 4.5;

      gsap.to(card, {
        rotationX: tiltX,
        rotationY: tiltY,
        y: -6,
        scale: 1.018,
        duration: 0.28,
        ease: 'power1.out',
        force3D: true,
        overwrite: 'auto'
      });
    });

    card.addEventListener('mouseleave', () => {
      gsap.to(card, {
        rotationX: 0,
        rotationY: 0,
        y: 0,
        scale: 1,
        duration: 0.65,
        ease: 'power3.out',
        force3D: true,
        overwrite: 'auto'
      });
    });
  });
}

/* ── Sense Section Feature Slides (Genuine Architectural Modules) ── */
const SENSE_FEATURE_SLIDES = [
  {
    badge: 'PRE-FLIGHT QUALIFICATION',
    index: '01 / 06',
    title: 'Pre-Flight Input Qualification',
    subtitle: 'Gemma visual inspection verifies document and selfie suitability',
    desc: 'Before running downstream extraction, Gemma inspects both uploaded images to confirm document visibility, detect image category, and ensure a clear, usable frontal portrait is present.',
    specTags: ['IMAGE SUITABILITY', 'FACE VISIBILITY', 'FAIL-EARLY'],
    fill: '88%',
    metaL: 'INPUT: QUALIFIED',
    metaR: 'STAGE 01 GATEWAY',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="m9 12 2 2 4-4"/></svg>`
  },
  {
    badge: 'DOCUMENT OCR',
    index: '02 / 06',
    title: 'OCR & Field Extraction',
    subtitle: 'Reading text fields from document surface',
    desc: 'Extracts textual identity credentials including full name, document number, date of birth, expiration date, and issuing authority for downstream rule checking.',
    specTags: ['FIELD EXTRACTION', 'TEXT NORMALIZATION', 'TYPOGRAPHIC SCAN'],
    fill: '92%',
    metaL: 'EXTRACTION: STRUCTURED',
    metaR: 'DATA ENGINE',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><circle cx="8" cy="10" r="1.5"/><path d="M2 16l4-4 4 4 6-6 4 4"/></svg>`
  },
  {
    badge: 'MRZ PARITY',
    index: '03 / 06',
    title: 'MRZ Check Digit Verification',
    subtitle: 'Mathematical check-digit validation when MRZ is present',
    desc: 'When an MRZ is present on passports or machine-readable IDs, VeriGate recalculates modular check digits on document numbers, dates of birth, and expiration dates.',
    specTags: ['CONDITIONAL MRZ', 'MOD-7 CHECK DIGITS', 'COMPOSITE INTEGRITY'],
    fill: '95%',
    metaL: 'MRZ: VERIFIED',
    metaR: 'CONDITIONAL AUDIT',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7V5a2 2 0 0 1 2-2h2M19 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M5 21H3a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/></svg>`
  },
  {
    badge: 'DETERMINISTIC RULE LAYER',
    index: '04 / 06',
    title: 'Deterministic Document Validation',
    subtitle: 'Mathematical checks on dates, ages, and chronological consistency',
    desc: 'Evaluates explicit business logic: confirms DOB is in the past, computes applicant calendar age, validates that issuance predates expiration, and flags expired credentials.',
    specTags: ['CALENDAR LOGIC', 'AGE COMPUTATION', 'EXPIRY EVALUATION'],
    fill: '100%',
    metaL: 'RULES: DETERMINISTIC',
    metaR: 'ZERO HALLUCINATIONS',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>`
  },
  {
    badge: 'COMPRESSION ANALYSIS',
    index: '05 / 06',
    title: 'Tampering Forensics (ELA)',
    subtitle: 'Error Level Analysis detecting image resave differentials',
    desc: 'Re-compresses the document image at fixed JPEG quality levels and computes residual pixel error maps to reveal localized splicing, cloned fields, or font tampering.',
    specTags: ['ERROR LEVEL ANALYSIS', 'SPLICING DETECTION', 'PIXEL RESIDUALS'],
    fill: '86%',
    metaL: 'FORENSICS: ELA METRICS',
    metaR: 'PIXEL RESIDUALS',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4"/></svg>`
  },
  {
    badge: 'MULTI-MODAL REASONING',
    index: '06 / 06',
    title: 'Biometric Matching & Gemma Reasoning',
    subtitle: 'Face feature vectors combined with unified evidence arbitration',
    desc: 'Dedicated biometric models compare the document portrait with the presented selfie using cosine similarity, while Gemma synthesizes all findings into a reasoned risk score.',
    specTags: ['FACIAL EMBEDDINGS', 'COSINE SIMILARITY', 'GEMMA ARBITER'],
    fill: '90%',
    metaL: 'ARBITER: MULTI-MODAL',
    metaR: 'EXPLAINABLE VERDICT',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="9" r="3"/><path d="M6 20c0-3 3-5 6-5s6 2 6 5"/><path d="m16 3 2 2-4 4"/></svg>`
  }
];

let currentSenseIndex = 0;
let isSenseFlipping = false;

function renderSenseSlide(idx) {
  const slide = SENSE_FEATURE_SLIDES[idx];
  if (!slide) return;

  const badgeEl = document.getElementById('senseCardBadge');
  const indexEl = document.getElementById('senseCardIndex');
  const titleEl = document.getElementById('senseCardTitle');
  const subtitleEl = document.getElementById('senseCardSubtitle');
  const descEl = document.getElementById('senseCardDesc');
  const specTagsEl = document.getElementById('senseCardSpecTags');
  const barFillEl = document.getElementById('senseCardBarFill');
  const metaLEl = document.getElementById('senseCardMetaLeft');
  const metaREl = document.getElementById('senseCardMetaRight');
  const iconEl = document.getElementById('senseCardIcon');

  if (badgeEl) badgeEl.textContent = slide.badge;
  if (indexEl) indexEl.textContent = slide.index;
  if (titleEl) titleEl.textContent = slide.title;
  if (subtitleEl) subtitleEl.textContent = slide.subtitle;
  if (descEl) descEl.textContent = slide.desc;
  if (metaLEl) metaLEl.textContent = slide.metaL;
  if (metaREl) metaREl.textContent = slide.metaR;
  if (barFillEl) barFillEl.style.width = slide.fill;
  if (iconEl) iconEl.innerHTML = slide.icon;

  if (specTagsEl) {
    specTagsEl.innerHTML = slide.specTags.map(tag => `<span class="spec-tag mono">${tag}</span>`).join('');
  }

  // Update dots
  document.querySelectorAll('#senseCardDots .sense-dot').forEach((dot, i) => {
    dot.classList.toggle('active', i === idx);
  });

  // Update feature pills
  document.querySelectorAll('#senseFeaturePills .feat-pill').forEach((pill, i) => {
    pill.classList.toggle('active', i === idx);
  });
}

function flipSenseCard(direction, targetIndex = null) {
  if (isSenseFlipping) return;
  isSenseFlipping = true;

  const card = document.getElementById('senseFeatureCard');
  if (!card) {
    isSenseFlipping = false;
    return;
  }

  let nextIdx;
  if (targetIndex !== null) {
    nextIdx = targetIndex;
  } else {
    nextIdx = direction === 'next'
      ? (currentSenseIndex + 1) % SENSE_FEATURE_SLIDES.length
      : (currentSenseIndex - 1 + SENSE_FEATURE_SLIDES.length) % SENSE_FEATURE_SLIDES.length;
  }

  const flipOutAngle = direction === 'next' ? -85 : 85;
  const flipInAngle = direction === 'next' ? 85 : -85;

  if (typeof gsap !== 'undefined') {
    gsap.timeline()
      .to(card, {
        rotationY: flipOutAngle,
        scale: 0.92,
        opacity: 0.7,
        duration: 0.28,
        ease: 'power2.in',
        force3D: true,
        onComplete: () => {
          currentSenseIndex = nextIdx;
          renderSenseSlide(currentSenseIndex);
          gsap.set(card, { rotationY: flipInAngle });
        }
      })
      .to(card, {
        rotationY: 0,
        scale: 1,
        opacity: 1,
        duration: 0.45,
        ease: 'power3.out',
        force3D: true,
        onComplete: () => {
          isSenseFlipping = false;
        }
      });
  } else {
    currentSenseIndex = nextIdx;
    renderSenseSlide(currentSenseIndex);
    isSenseFlipping = false;
  }
}

/* ── Sense Section Initialization ── */
function initSenseAnimations() {
  const sense = document.querySelector('.sense');
  if (!sense) return;

  // Entrance animation for Sense left & right columns
  if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
    const isMobileSense = typeof window !== 'undefined' && window.innerWidth <= 768;
    gsap.fromTo('.sense-left-col',
      { opacity: 0, x: isMobileSense ? 0 : -36, y: isMobileSense ? 24 : 0 },
      { opacity: 1, x: 0, y: 0, duration: 1, ease: 'power3.out', scrollTrigger: { trigger: '.sense', start: 'top 85%' } }
    );

    gsap.fromTo('.sense-right-col',
      { opacity: 0, x: isMobileSense ? 0 : 36, y: isMobileSense ? 24 : 0 },
      { opacity: 1, x: 0, y: 0, duration: 1, ease: 'power3.out', scrollTrigger: { trigger: '.sense', start: 'top 85%' } }
    );
  }

  const btnPrev = document.getElementById('btnSensePrev');
  const btnNext = document.getElementById('btnSenseNext');
  const card = document.getElementById('senseFeatureCard');

  if (btnPrev) {
    btnPrev.addEventListener('click', (e) => {
      e.stopPropagation();
      flipSenseCard('prev');
    });
  }

  if (btnNext) {
    btnNext.addEventListener('click', (e) => {
      e.stopPropagation();
      flipSenseCard('next');
    });
  }

  // Dot clicks
  document.querySelectorAll('#senseCardDots .sense-dot').forEach((dot) => {
    dot.addEventListener('click', (e) => {
      e.stopPropagation();
      const targetIdx = parseInt(dot.getAttribute('data-index'), 10);
      if (isNaN(targetIdx) || targetIdx === currentSenseIndex || isSenseFlipping) return;
      const dir = targetIdx > currentSenseIndex ? 'next' : 'prev';
      flipSenseCard(dir, targetIdx);
    });
  });

  // Feature quick-pills clicks
  document.querySelectorAll('#senseFeaturePills .feat-pill').forEach((pill) => {
    pill.addEventListener('click', (e) => {
      e.stopPropagation();
      const targetIdx = parseInt(pill.getAttribute('data-index'), 10);
      if (isNaN(targetIdx) || targetIdx === currentSenseIndex || isSenseFlipping) return;
      const dir = targetIdx > currentSenseIndex ? 'next' : 'prev';
      flipSenseCard(dir, targetIdx);
    });
  });

  // 60fps Interactive 3D Mouse Tilt on the card (Desktop only)
  if (card && typeof gsap !== 'undefined' && typeof window !== 'undefined' && window.innerWidth > 768) {
    card.addEventListener('mousemove', (e) => {
      if (isSenseFlipping) return;
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;

      const tiltX = (y / (rect.height / 2)) * -5;
      const tiltY = (x / (rect.width / 2)) * 5;

      gsap.to(card, {
        rotationX: tiltX,
        rotationY: tiltY,
        duration: 0.3,
        ease: 'power1.out',
        force3D: true,
        overwrite: 'auto'
      });
    });

    card.addEventListener('mouseleave', () => {
      if (isSenseFlipping) return;
      gsap.to(card, {
        rotationX: 0,
        rotationY: 0,
        duration: 0.6,
        ease: 'power3.out',
        force3D: true,
        overwrite: 'auto'
      });
    });
  }
}

/* ── Pipeline Section Stage Slides (Genuine Architectural Sequence) ── */
const PIPELINE_STAGE_SLIDES = [
  {
    accent: '#00f2fe',
    glow: 'rgba(0, 242, 254, 0.45)',
    badge: 'STAGE 01 • PRE-FLIGHT INPUT QUALIFICATION',
    index: 'PIPELINE 01 / 06',
    title: 'Pre-Flight Input Qualification',
    subtitle: 'Gemma visual inspection verifies document and selfie suitability',
    desc: 'Before running downstream extraction, Gemma inspects both uploaded images to confirm document visibility, detect image category, and ensure a clear, usable frontal portrait is present.',
    specTags: ['DOCUMENT SUITABILITY', 'PORTRAIT SUITABILITY', 'FAIL-EARLY GATING'],
    termTitle: 'QUALIFICATION AUDIT • STAGE 01',
    termLines: [
      '> QUALIFYING DOCUMENT IMAGE... [SUITABLE]',
      '> QUALIFYING PORTRAIT IMAGE... [SUITABLE]',
      '> CLASSIFICATION: VALID IDENTITY CREDENTIAL'
    ],
    fill: '88%',
    metaL: 'INPUT STATUS: QUALIFIED',
    metaR: 'PRE-FLIGHT GATEWAY',
    hudStatus: 'INPUTS QUALIFIED',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="m9 12 2 2 4-4"/></svg>`
  },
  {
    accent: '#10b981',
    glow: 'rgba(16, 185, 129, 0.45)',
    badge: 'STAGE 02 • OPTICAL OCR EXTRACTION',
    index: 'PIPELINE 02 / 06',
    title: 'OCR & Identity Field Extraction',
    subtitle: 'Reading text fields from document surface',
    desc: 'Locates and extracts textual credential data: full name, document number, nationality, date of birth, and expiry date for subsequent deterministic rule validation.',
    specTags: ['MULTI-FIELD OCR', 'TEXT NORMALIZATION', 'VALUE EXTRACTION'],
    termTitle: 'OCR AUDIT • STAGE 02',
    termLines: [
      '> LOCATING CREDENTIAL FIELDS... [OK]',
      '> EXTRACTED: SURNAME, GIVEN NAMES, DOC_NUM, DOB',
      '> NORMALIZING EXTRACTED VALUES... [COMPLETE]'
    ],
    fill: '92%',
    metaL: 'EXTRACTION: STRUCTURED',
    metaR: 'DATA ENGINE',
    hudStatus: 'FIELDS PARSED',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><circle cx="8" cy="10" r="1.5"/><path d="M2 16l4-4 4 4 6-6 4 4"/></svg>`
  },
  {
    accent: '#38bdf8',
    glow: 'rgba(56, 189, 248, 0.45)',
    badge: 'STAGE 03 • MRZ VERIFICATION',
    index: 'PIPELINE 03 / 06',
    title: 'MRZ Check Digit Verification',
    subtitle: 'Validating check digits when document format includes an MRZ',
    desc: 'When the document includes a machine-readable zone, VeriGate parses the lines and computes modular check digits on document number, DOB, and expiry.',
    specTags: ['CONDITIONAL AUDIT', 'ICAO 9303 FORMAT', 'CHECKSUM PARITY'],
    termTitle: 'MRZ AUDIT • STAGE 03',
    termLines: [
      '> PARSING MACHINE-READABLE ZONE... [FOUND]',
      '> VALIDATING LINE CHECKSUMS... [PASS]',
      '> COMPOSITE PARITY CONFIRMED'
    ],
    fill: '96%',
    metaL: 'MRZ STATUS: VERIFIED',
    metaR: 'CONDITIONAL VALIDATION',
    hudStatus: 'MRZ VALIDATED',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7V5a2 2 0 0 1 2-2h2M19 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M5 21H3a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/></svg>`
  },
  {
    accent: '#f59e0b',
    glow: 'rgba(245, 158, 11, 0.45)',
    badge: 'STAGE 04 • DETERMINISTIC VALIDATION',
    index: 'PIPELINE 04 / 06',
    title: 'Deterministic Document Validation',
    subtitle: 'Mathematical verification of dates, age, and validity',
    desc: 'Executes deterministic checks: verifies DOB is in the past, calculates applicant age, checks that issuance predates expiry, and flags expired credentials.',
    specTags: ['CALENDAR AUDIT', 'AGE CALCULATION', 'EXPIRY CHECK'],
    termTitle: 'STAGE 04 • DETERMINISTIC RULES',
    termLines: [
      '> VERIFYING DOB IN PAST... [PASS]',
      '> CALCULATING SUBJECT AGE: VALID',
      '> CHECKING EXPIRY STATUS... [NOT EXPIRED]'
    ],
    fill: '100%',
    metaL: 'RULES: DETERMINISTIC',
    metaR: 'MATHEMATICAL COHERENCE',
    hudStatus: 'RULES EVALUATED',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>`
  },
  {
    accent: '#ff2a54',
    glow: 'rgba(255, 42, 84, 0.45)',
    badge: 'STAGE 05 • TAMPERING FORENSICS',
    index: 'PIPELINE 05 / 06',
    title: 'Tampering Forensics (ELA)',
    subtitle: 'Error Level Analysis and compression discrepancy detection',
    desc: 'Re-compresses the document image at fixed quality to compute pixel-level error differences, highlighting localized splicing or altered text regions.',
    specTags: ['ELA FORENSICS', 'COMPRESSION RESIDUALS', 'SPLICING DETECTION'],
    termTitle: 'STAGE 05 • TAMPERING AUDIT',
    termLines: [
      '> EXECUTING ERROR LEVEL ANALYSIS... [DONE]',
      '> ANALYZING COMPRESSION ERROR RESIDUALS...',
      '> SUSPICIOUS REGIONS: 0 DETECTED'
    ],
    fill: '90%',
    metaL: 'FORENSICS: ELA METRICS',
    metaR: 'NO TAMPERING DETECTED',
    hudStatus: 'FORENSICS COMPLETE',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M2 12h4M18 12h4"/></svg>`
  },
  {
    accent: '#ff4365',
    glow: 'rgba(255, 67, 101, 0.45)',
    badge: 'STAGE 06 • BIOMETRICS & ARBITRATION',
    index: 'PIPELINE 06 / 06',
    title: 'Biometric Matching & Gemma AI Reasoning',
    subtitle: 'Dedicated face verification reconciled by Gemma AI',
    desc: 'Dedicated biometric models compare document portrait with presented person using cosine distance, while Gemma synthesizes all findings into a final risk decision.',
    specTags: ['FACE EMBEDDINGS', 'COSINE SIMILARITY', 'GEMMA ARBITER'],
    termTitle: 'STAGE 06 • ARBITRATION',
    termLines: [
      '> EXTRACTING BIOMETRIC EMBEDDINGS... [OK]',
      '> COSINE DISTANCE EVALUATION: MATCH',
      '> GEMMA GENERATING REASONED VERDICT... [DONE]'
    ],
    fill: '94%',
    metaL: 'ARBITER: MULTI-MODAL',
    metaR: 'EVIDENCE-BASED VERDICT',
    hudStatus: 'PIPELINE COMPLETED',
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>`
  }
];

let currentPipelineIndex = 0;
let isPipelineFlipping = false;

function renderPipelineSlide(idx) {
  const slide = PIPELINE_STAGE_SLIDES[idx];
  if (!slide) return;

  const card = document.getElementById('pipelineFeatureCard');
  const badgeEl = document.getElementById('pipelineCardBadge');
  const indexEl = document.getElementById('pipelineCardIndex');
  const titleEl = document.getElementById('pipelineCardTitle');
  const subtitleEl = document.getElementById('pipelineCardSubtitle');
  const descEl = document.getElementById('pipelineCardDesc');
  const specTagsEl = document.getElementById('pipelineCardSpecTags');
  const termTitleEl = document.getElementById('pipelineTerminalTitle');
  const termBodyEl = document.getElementById('pipelineTerminalBody');
  const barFillEl = document.getElementById('pipelineCardBarFill');
  const metaLEl = document.getElementById('pipelineCardMetaLeft');
  const metaREl = document.getElementById('pipelineCardMetaRight');
  const iconEl = document.getElementById('pipelineCardIcon');
  const hudStatusEl = document.getElementById('helixHudStatus');

  if (card) {
    card.style.setProperty('--card-accent', slide.accent);
  }

  if (badgeEl) {
    badgeEl.textContent = slide.badge;
    badgeEl.style.color = slide.accent;
    badgeEl.style.background = `${slide.accent}18`;
    badgeEl.style.borderColor = `${slide.accent}40`;
  }
  if (indexEl) indexEl.textContent = slide.index;
  if (titleEl) titleEl.textContent = slide.title;
  if (subtitleEl) {
    subtitleEl.textContent = slide.subtitle;
    subtitleEl.style.color = slide.accent;
  }
  if (descEl) descEl.textContent = slide.desc;
  if (metaLEl) metaLEl.textContent = slide.metaL;
  if (metaREl) metaREl.textContent = slide.metaR;
  if (hudStatusEl) hudStatusEl.textContent = slide.hudStatus;

  if (barFillEl) {
    barFillEl.style.width = slide.fill;
    barFillEl.style.background = `linear-gradient(90deg, ${slide.accent}, #ffffff)`;
    barFillEl.style.boxShadow = `0 0 12px ${slide.glow}`;
  }

  if (iconEl) {
    iconEl.innerHTML = slide.icon;
    iconEl.style.color = slide.accent;
    iconEl.style.background = `${slide.accent}1c`;
    iconEl.style.borderColor = `${slide.accent}55`;
    iconEl.style.boxShadow = `0 0 20px ${slide.glow}`;
  }

  if (termTitleEl) termTitleEl.textContent = slide.termTitle;
  if (termBodyEl) {
    termBodyEl.innerHTML = slide.termLines.map((line) => {
      const isSuccess = line.includes('OK') || line.includes('MATCH') || line.includes('APPROVED') || line.includes('PASSED');
      return `<span class="term-line ${isSuccess ? 'success' : ''}">${line}</span>`;
    }).join('');
  }

  if (specTagsEl) {
    specTagsEl.innerHTML = slide.specTags.map(tag =>
      `<span class="pipeline-spec-tag mono" style="color:${slide.accent}; border-color:${slide.accent}44; background:${slide.accent}10;">${tag}</span>`
    ).join('');
  }

  // Update dots
  document.querySelectorAll('#pipelineCardDots .pipeline-dot').forEach((dot, i) => {
    dot.classList.toggle('active', i === idx);
  });

  // Update stage quick-pills
  document.querySelectorAll('#pipelineStagePills .stage-pill').forEach((pill, i) => {
    pill.classList.toggle('active', i === idx);
  });

  // Update helix nodes
  document.querySelectorAll('#pipelineHelixTrack .helix-node').forEach((node, i) => {
    node.classList.toggle('active', i === idx);
  });
}

function flipPipelineCard(direction, targetIndex = null) {
  if (isPipelineFlipping) return;
  isPipelineFlipping = true;

  const card = document.getElementById('pipelineFeatureCard');
  if (!card) {
    isPipelineFlipping = false;
    return;
  }

  let nextIdx;
  if (targetIndex !== null) {
    nextIdx = targetIndex;
  } else {
    nextIdx = direction === 'next'
      ? (currentPipelineIndex + 1) % PIPELINE_STAGE_SLIDES.length
      : (currentPipelineIndex - 1 + PIPELINE_STAGE_SLIDES.length) % PIPELINE_STAGE_SLIDES.length;
  }

  const flipOutAngle = direction === 'next' ? -85 : 85;
  const flipInAngle = direction === 'next' ? 85 : -85;

  if (typeof gsap !== 'undefined') {
    gsap.timeline()
      .to(card, {
        rotationY: flipOutAngle,
        scale: 0.92,
        opacity: 0.7,
        duration: 0.28,
        ease: 'power2.in',
        force3D: true,
        onComplete: () => {
          currentPipelineIndex = nextIdx;
          renderPipelineSlide(currentPipelineIndex);
          gsap.set(card, { rotationY: flipInAngle });
        }
      })
      .to(card, {
        rotationY: 0,
        scale: 1,
        opacity: 1,
        duration: 0.45,
        ease: 'power3.out',
        force3D: true,
        onComplete: () => {
          isPipelineFlipping = false;
        }
      });
  } else {
    currentPipelineIndex = nextIdx;
    renderPipelineSlide(currentPipelineIndex);
    isPipelineFlipping = false;
  }
}

/* ── Pipeline Section Initialization ── */
function initPipelineAnimations() {
  const pipeline = document.querySelector('.pipeline-section');
  if (!pipeline) return;

  // Entrance animation for Pipeline left & right columns
  if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
    const isMobilePipeline = typeof window !== 'undefined' && window.innerWidth <= 768;
    gsap.fromTo('.pipeline-left-col',
      { opacity: 0, x: isMobilePipeline ? 0 : -36, y: isMobilePipeline ? 24 : 0 },
      { opacity: 1, x: 0, y: 0, duration: 1, ease: 'power3.out', scrollTrigger: { trigger: '.pipeline-section', start: 'top 85%' } }
    );

    gsap.fromTo('.pipeline-right-col',
      { opacity: 0, x: isMobilePipeline ? 0 : 36, y: isMobilePipeline ? 24 : 0 },
      { opacity: 1, x: 0, y: 0, duration: 1, ease: 'power3.out', scrollTrigger: { trigger: '.pipeline-section', start: 'top 85%' } }
    );
  }

  const btnPrev = document.getElementById('btnPipelinePrev');
  const btnNext = document.getElementById('btnPipelineNext');
  const card = document.getElementById('pipelineFeatureCard');

  if (btnPrev) {
    btnPrev.addEventListener('click', (e) => {
      e.stopPropagation();
      flipPipelineCard('prev');
    });
  }

  if (btnNext) {
    btnNext.addEventListener('click', (e) => {
      e.stopPropagation();
      flipPipelineCard('next');
    });
  }

  // Dot clicks
  document.querySelectorAll('#pipelineCardDots .pipeline-dot').forEach((dot) => {
    dot.addEventListener('click', (e) => {
      e.stopPropagation();
      const targetIdx = parseInt(dot.getAttribute('data-index'), 10);
      if (isNaN(targetIdx) || targetIdx === currentPipelineIndex || isPipelineFlipping) return;
      const dir = targetIdx > currentPipelineIndex ? 'next' : 'prev';
      flipPipelineCard(dir, targetIdx);
    });
  });

  // Stage quick-pills clicks
  document.querySelectorAll('#pipelineStagePills .stage-pill').forEach((pill) => {
    pill.addEventListener('click', (e) => {
      e.stopPropagation();
      const targetIdx = parseInt(pill.getAttribute('data-index'), 10);
      if (isNaN(targetIdx) || targetIdx === currentPipelineIndex || isPipelineFlipping) return;
      const dir = targetIdx > currentPipelineIndex ? 'next' : 'prev';
      flipPipelineCard(dir, targetIdx);
    });
  });

  // Helix node clicks
  document.querySelectorAll('#pipelineHelixTrack .helix-node').forEach((node) => {
    node.addEventListener('click', (e) => {
      e.stopPropagation();
      const targetIdx = parseInt(node.getAttribute('data-index'), 10);
      if (isNaN(targetIdx) || targetIdx === currentPipelineIndex || isPipelineFlipping) return;
      const dir = targetIdx > currentPipelineIndex ? 'next' : 'prev';
      flipPipelineCard(dir, targetIdx);
    });
  });

  // 60fps Interactive 3D Mouse Tilt on the card (Desktop only)
  if (card && typeof gsap !== 'undefined' && typeof window !== 'undefined' && window.innerWidth > 768) {
    card.addEventListener('mousemove', (e) => {
      if (isPipelineFlipping) return;
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;

      const tiltX = (y / (rect.height / 2)) * -5;
      const tiltY = (x / (rect.width / 2)) * 5;

      gsap.to(card, {
        rotationX: tiltX,
        rotationY: tiltY,
        duration: 0.3,
        ease: 'power1.out',
        force3D: true,
        overwrite: 'auto'
      });
    });

    card.addEventListener('mouseleave', () => {
      if (isPipelineFlipping) return;
      gsap.to(card, {
        rotationX: 0,
        rotationY: 0,
        duration: 0.6,
        ease: 'power3.out',
        force3D: true,
        overwrite: 'auto'
      });
    });
  }
}

/* ── Generic Section Reveals ── */
function initSectionReveals() {
  gsap.utils.toArray('.fade-up:not(.hero .fade-up)').forEach(el => {
    gsap.fromTo(el, { opacity: 0, y: 30 }, {
      opacity: 1, y: 0, duration: 0.8, ease: 'power3.out',
      scrollTrigger: { trigger: el, start: 'top 88%' }
    });
  });
}

/* ── Master Init ── */
let isAnimationsInitialized = false;

function initAllAnimations() {
  if (isAnimationsInitialized) return;
  isAnimationsInitialized = true;

  initParticles();
  initNavbarScroll();
  initWaterButtons();
  initHeroAnimations();
  initHeroCardShowcase();
  initProblemAnimations();
  initSenseAnimations();
  initPipelineAnimations();
  initSectionReveals();
}
