// Landing pages such as /comedy/: links to the quote form and the quote request form (handled by leads/views.py).
// Runs as a module, so it is deferred and the DOM is parsed by now.

const form = document.getElementById('comedy-enquiry');

if (form) {
  initQuoteLinks();
  initEnquiry(form);
}

/* "Choose Show" etc. scroll to the quote section and move focus there, and select the matching "I'm a…" option
   (data-client-type, set from the package code in the template). A native hash jump would reset focus after this
   handler, so the scroll is done here instead. */
function initQuoteLinks() {
  for (const link of document.querySelectorAll('a[data-package]')) {
    link.addEventListener('click', (event) => {
      selectClientType(link.dataset.clientType);
      const target = document.querySelector(link.hash);
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView(); // honours the stylesheet's smooth scrolling and reduced-motion setting
      history.pushState(null, '', link.hash);
      if (!target.hasAttribute('tabindex')) target.tabIndex = -1;
      target.focus({ preventScroll: true });
    });
  }
}

function selectClientType(value) {
  if (!value) return;
  const radio = form.querySelector(`input[name="client-type"][value="${CSS.escape(value)}"]`);
  if (!radio || radio.checked) return;
  radio.checked = true;
  radio.dispatchEvent(new Event('input', { bubbles: true })); // clears a "choose one" error (initEnquiry)
}

function initEnquiry(form) {
  const errorMessage = document.getElementById('enquiryError');
  const submitButton = document.getElementById('enquirySubmit');
  const thanks = document.getElementById('enquiryThanks');
  const typeGroup = document.getElementById('c-type');

  form.addEventListener('input', ({ target }) => {
    if (target.type === 'radio') setInvalid(typeGroup, false);
    else setInvalid(target, false);
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const invalid = [form.elements.namedItem('name'), form.elements.namedItem('email')].filter((el) => {
      const bad = !el.value.trim() || !el.checkValidity();
      setInvalid(el, bad);
      return bad;
    });

    const typeChosen = form.querySelector('input[name="client-type"]:checked');
    setInvalid(typeGroup, !typeChosen);
    if (!typeChosen) invalid.push(typeGroup.querySelector('input'));

    if (invalid.length) {
      errorMessage.textContent = 'Please add your name, a valid email address, and tell us what kind of act you are.';
      invalid[0].focus();
      return;
    }
    errorMessage.textContent = '';

    setSending(submitButton, true);
    try {
      const response = await fetch(form.getAttribute('action'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
        body: formBody(form),
      });
      if (!response.ok) throw new Error(`Form submission failed with status ${response.status}`);

      const name = form.elements.namedItem('name').value.trim().split(/\s+/)[0];
      if (name) thanks.querySelector('[data-name]').textContent = `, ${name}`;
      form.hidden = true;
      thanks.hidden = false;
      document.getElementById('enquiryThanksTitle').focus();
    } catch (error) {
      console.error(error);
      setSending(submitButton, false); // before focusing it: a disabled button can't take focus
      errorMessage.textContent = 'Something went wrong sending your enquiry. Please try again.';
      submitButton.focus();
    } finally {
      setSending(submitButton, false);
    }
  });
}

function setInvalid(el, isInvalid) {
  el.classList.toggle('invalid', isInvalid);
  if (el instanceof HTMLFieldSetElement) return; // the group is styled; its radios carry no aria-invalid
  if (isInvalid) el.setAttribute('aria-invalid', 'true');
  else el.removeAttribute('aria-invalid');
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
