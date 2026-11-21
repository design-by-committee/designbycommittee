// Comedy landing page (/comedy/): package pre-selection and the Netlify enquiry form.
// Runs as a module, so it is deferred and the DOM is parsed by now.

const form = document.getElementById('comedy-enquiry');

if (form) {
  initPackageLinks(form);
  initEnquiry(form);
}

/* "Choose Show" etc. preselect that package, scroll to the quote section and move focus there.
   A native hash jump would reset focus after this handler, so the scroll is done here instead. */
function initPackageLinks(form) {
  const select = form.elements.namedItem('package');
  for (const link of document.querySelectorAll('a[data-package]')) {
    link.addEventListener('click', (event) => {
      const target = document.querySelector(link.hash);
      if (!target) return;
      event.preventDefault();
      select.value = link.dataset.package;
      target.scrollIntoView(); // honours the stylesheet's smooth scrolling and reduced-motion setting
      history.pushState(null, '', link.hash);
      if (!target.hasAttribute('tabindex')) target.tabIndex = -1;
      target.focus({ preventScroll: true });
    });
  }
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

    submitButton.disabled = true;
    try {
      const response = await fetch(form.getAttribute('action'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(new FormData(form)),
      });
      if (!response.ok) throw new Error(`Form submission failed with status ${response.status}`);

      const name = form.elements.namedItem('name').value.trim().split(/\s+/)[0];
      if (name) thanks.querySelector('[data-name]').textContent = `, ${name}`;
      form.hidden = true;
      thanks.hidden = false;
      document.getElementById('enquiryThanksTitle').focus();
    } catch (error) {
      console.error(error);
      submitButton.disabled = false;
      errorMessage.textContent = 'Something went wrong sending your enquiry. Please try again.';
      submitButton.focus();
    }
  });
}

function setInvalid(el, isInvalid) {
  el.classList.toggle('invalid', isInvalid);
  if (el instanceof HTMLFieldSetElement) return; // the group is styled; its radios carry no aria-invalid
  if (isInvalid) el.setAttribute('aria-invalid', 'true');
  else el.removeAttribute('aria-invalid');
}
