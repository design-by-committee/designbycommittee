// Loaded as an ES module, so it runs after the page has been parsed.

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

/* Testimonials: on small screens CSS turns them into a swipeable row; add a dot for each one to jump to it. */
function initCarousel() {
  const carousel = document.querySelector('.carousel');
  const dots = carousel?.parentElement.querySelector('.carousel__dots');
  if (!dots) return; // the page has no testimonial carousel
  const slides = [...carousel.children];
  if (slides.length < 2) return;

  const buttons = slides.map((slide, index) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.setAttribute('aria-label', `Show testimonial ${index + 1} of ${slides.length}`);
    // CSS sets scroll-behavior: smooth unless the visitor prefers reduced motion
    button.addEventListener('click', () => carousel.scrollTo({ left: slide.offsetLeft }));
    dots.append(button);
    return button;
  });

  const setCurrent = (current) => {
    buttons.forEach((button, index) => button.setAttribute('aria-current', String(index === current)));
  };
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) setCurrent(slides.indexOf(entry.target));
    }
  }, { root: carousel, threshold: 0.6 });
  slides.forEach((slide) => observer.observe(slide));

  setCurrent(0);
  dots.hidden = false; // medium.css hides the dots on large screens, where the quotes sit side by side
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

  // Phones' URL keyboards don't type "https://", and type="url" needs it: add it to "example.com" for the visitor
  const url = field('url');
  const addScheme = () => {
    const value = url.value.trim();
    if (value && !/^[a-z][a-z\d+.-]*:\/\//i.test(value)) url.value = `https://${value}`;
  };
  url.addEventListener('change', addScheme);

  initSchedule();

  // Native date and time fields: a weekday from tomorrow to two weeks ahead, between 09:00 and 18:00 (see the HTML)
  function initSchedule() {
    const date = field('date');
    const isoDate = (days) => {
      const day = new Date();
      day.setDate(day.getDate() + days);
      // en-CA formats as YYYY-MM-DD in local time, which is what <input type="date"> uses
      return day.toLocaleDateString('en-CA');
    };
    date.min = isoDate(1);
    date.max = isoDate(14);

    // Native date pickers can't grey out weekends, so flag them when one is chosen
    const checkWeekday = () => {
      const day = date.valueAsDate?.getUTCDay();
      date.setCustomValidity(day === 0 || day === 6 ? 'Please choose a weekday.' : '');
    };
    date.addEventListener('input', checkWeekday);
    checkWeekday();
  }

  // Clear a field's error state as soon as the visitor edits it
  form.addEventListener('input', ({ target }) => markInvalid(target, false));

  continueButton.addEventListener('click', () => {
    const interests = [...form.querySelectorAll('input[type="checkbox"]')];
    addScheme(); // in case Continue is tapped straight from the field, before its change event
    const invalid = validate([url]);
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
      // A filled-in field that's still invalid (a weekend, a time outside office hours...) explains itself
      const [first] = invalid;
      const message = first.value.trim() && first.validationMessage;
      showError(message || 'Please complete all the fields below before moving on to the next step.', first);
      return;
    }
    clearError();

    setSending(submitButton, true);
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
        body: formBody(form),
      });
      if (!response.ok) throw new Error(`Form submission failed with status ${response.status}`);

      form.querySelector('.firstName').textContent = field('first-name').value;
      form.querySelector('.thx-gif').src = 'https://media.giphy.com/media/WZ4M8M2VbauEo/source.gif';
      goToStep(2, document.getElementById('thanksHeading'));
    } catch (error) {
      console.error(error);
      setSending(submitButton, false); // before focusing it: a disabled button can't take focus
      showError('Oops, something went wrong sending your request. Please try again.', submitButton);
    } finally {
      setSending(submitButton, false);
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

/* The form's fields plus "fill-time": whole seconds since the page opened. The server treats a missing or very short
   time as a sign of a bot (leads/spam.py); people take longer than a few seconds to fill in a form. */
function formBody(form) {
  const body = new URLSearchParams(new FormData(form));
  body.set('fill-time', String(Math.floor(performance.now() / 1000)));
  return body;
}

/* While the form is being sent: the button says "Sending…" with a spinner (small.css) and can't be pressed twice. */
function setSending(button, sending) {
  if (sending) {
    button.dataset.label = button.textContent;
    button.textContent = 'Sending…';
  } else if (button.dataset.label) {
    button.textContent = button.dataset.label;
  }
  button.disabled = sending;
  button.classList.toggle('is-sending', sending);
  button.form.setAttribute('aria-busy', String(sending));
}
