// Loaded as a deferred ES module after tiny-slider and flatpickr (see <head>), so both globals exist here.

const prefersReducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

initFocusLinks();
initReveal();
initCarousel();
initForm();

/* In-page links: let the browser scroll (CSS handles smooth scrolling), and move focus to the target. */
function initFocusLinks() {
  for (const link of document.querySelectorAll('a[data-focus-target]')) {
    link.addEventListener('click', () => {
      const target = document.querySelector(link.hash);
      if (!target) return;
      if (!target.hasAttribute('tabindex')) target.tabIndex = -1;
      target.focus({ preventScroll: true });
    });
  }
}

/* Fade illustrations in as they scroll into view. Images load natively via loading="lazy". */
function initReveal() {
  if (prefersReducedMotion()) return;

  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add('is-visible');
      observer.unobserve(entry.target);
    }
  }, { rootMargin: '0px 0px -150px 0px' });

  document.querySelectorAll('.reveal').forEach((img) => observer.observe(img));
  document.documentElement.classList.add('has-reveal');
}

/* Testimonials become a slider below 1000px and a static row above it. */
function initCarousel() {
  const carousel = document.querySelector('.carousel');
  if (!carousel) return; // the page has no testimonial carousel
  if (typeof tns !== 'function') return; // CDN blocked or failed its integrity check: keep the static layout
  const mobile = matchMedia('(width < 1000px)');
  const host = carousel.parentElement;
  let slider = null;

  // tiny-slider measures the carousel's parent on init and throws if the page has no layout width yet
  // (e.g. loaded in a hidden iframe or a prerendered tab), so wait until the carousel has a width.
  // Look the carousel up each time: destroy() rebuilds it from HTML, replacing the element.
  const hasWidth = () => host.querySelector(':scope > .carousel').getBoundingClientRect().width > 0;

  const update = () => {
    if (mobile.matches && !slider && hasWidth()) {
      slider = tns({
        container: '.carousel',
        items: 1,
        slideBy: 'page',
        navPosition: 'bottom',
        controls: false,
      });
    } else if (!mobile.matches && slider) {
      slider.destroy();
      slider = null;
    }
  };

  update();
  mobile.addEventListener('change', update);
  new ResizeObserver(update).observe(host); // retry once a zero-width layout gets a real width
}

/* Two-step assessment form, posted to the page with fetch (handled by leads/views.py). */
function initForm() {
  const form = document.getElementById('landing-page-assessment');
  if (!form) return; // the page has no assessment form
  const container = document.getElementById('contactForm');
  const errorMessage = document.getElementById('errorMessage');
  const continueButton = document.getElementById('submitS1');
  const submitButton = document.getElementById('submitForm');
  const steps = {
    nav: container.querySelectorAll('.form__steps .step'),
    panels: form.querySelectorAll(':scope > section'),
  };
  const field = (name) => form.elements.namedItem(name);
  let currentStep = 0;

  field('timezone').value = Intl.DateTimeFormat().resolvedOptions().timeZone;

  // Without flatpickr (CDN blocked) the date and time fields still accept typed values
  if (typeof flatpickr === 'function') initPickers();

  function initPickers() {
    flatpickr('#date', {
      disableMobile: true,
      allowInput: true, // keyboard and screen reader users can type instead of using the popup
      dateFormat: 'm-d-Y',
      minDate: new Date().fp_incr(1), // tomorrow
      maxDate: new Date().fp_incr(14), // two weeks ahead
      disable: [(date) => date.getDay() === 0 || date.getDay() === 6], // weekdays only
      locale: { firstDayOfWeek: 1 },
    });

    flatpickr('#time', {
      disableMobile: true,
      allowInput: true,
      enableTime: true,
      noCalendar: true,
      dateFormat: 'H:i',
      minTime: '09:00',
      maxTime: '18:00',
      time_24hr: false,
    });
  }

  // Clear a field's error state as soon as the visitor edits it
  form.addEventListener('input', ({ target }) => markInvalid(target, false));

  continueButton.addEventListener('click', () => {
    const interests = [...form.querySelectorAll('input[type="checkbox"]')];
    const invalid = validate([field('url')]);
    if (!interests.some((box) => box.checked)) invalid.push(interests[0]);

    if (invalid.length) {
      showError('Please ensure your landing page URL is correct and you have at least one interest checked.', invalid[0]);
      return;
    }
    clearError();
    goToStep(1, field('first-name'));
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    // Enter in a step-one field submits the form implicitly: treat it as "Continue"
    if (currentStep === 0) {
      continueButton.click();
      return;
    }

    const invalid = validate(['first-name', 'last-name', 'email', 'date', 'time'].map(field));
    if (invalid.length) {
      showError('Please complete all the fields below before moving on to the next step.', invalid[0]);
      return;
    }
    clearError();

    submitButton.disabled = true; // prevent double submissions
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
        body: new URLSearchParams(new FormData(form)),
      });
      if (!response.ok) throw new Error(`Form submission failed with status ${response.status}`);

      form.querySelector('.firstName').textContent = field('first-name').value;
      form.querySelector('.thx-gif').src = 'https://media.giphy.com/media/WZ4M8M2VbauEo/source.gif';
      goToStep(2, document.getElementById('thanksHeading'));
    } catch (error) {
      console.error(error);
      submitButton.disabled = false;
      showError('Oops, something went wrong sending your request. Please try again.', submitButton);
    }
  });

  function goToStep(index, focusTarget) {
    steps.panels.forEach((panel, i) => { panel.hidden = i !== index; });
    steps.nav.forEach((step, i) => {
      step.classList.toggle('active', i === index);
      step.classList.toggle('complete', i < index);
      if (i === index) step.setAttribute('aria-current', 'step');
      else step.removeAttribute('aria-current');
    });
    currentStep = index;
    container.scrollIntoView();
    focusTarget.focus();
  }

  // Native constraint validation (required, type=url/email, pattern) decides what is valid
  function validate(fields) {
    return fields.filter((el) => {
      const isInvalid = !el.value.trim() || !el.checkValidity();
      markInvalid(el, isInvalid);
      return isInvalid;
    });
  }

  function markInvalid(el, isInvalid) {
    if (!(el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement)) return;
    el.classList.toggle('invalid', isInvalid);
    if (isInvalid) el.setAttribute('aria-invalid', 'true');
    else el.removeAttribute('aria-invalid');
  }

  // #errorMessage is a role="alert" live region: setting its text announces it
  function showError(message, focusTarget) {
    errorMessage.textContent = message;
    container.scrollIntoView();
    focusTarget?.focus();
  }

  function clearError() {
    errorMessage.textContent = '';
  }
}
