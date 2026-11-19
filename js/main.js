(function () {
  var slider,
    firstNavStep = document.querySelector('.form__steps .step__one'),
    secondNavStep = document.querySelector('.form__steps .step__two'),
    thirdNavStep = document.querySelector('.form__steps .step__three'),
    firstStep = document.querySelector('.form__wrapper .step__one'),
    secondStep = document.querySelector('.form__wrapper .step__two'),
    thirdStep = document.querySelector('.form__wrapper .step__three');

  scrollTo();
  initSlider();
  animateHTML().init();

  // wait for svg (skip the spinning wheels if the visitor prefers reduced motion)
  var checkForPiggy = setInterval(function() {
    if (prefersReducedMotion()) {
      clearInterval(checkForPiggy);
      return;
    }
    if (document.querySelector('.mopedPiggy')) {
       initWheelTurn('.mopedPiggy');
       clearInterval(checkForPiggy);
    }
  }, 100);

  // wait for flatpickr
  var checkForPicker = setInterval(function() {
    if (window.flatpickr) {
      initFlatpickr(flatpickr);
      clearInterval(checkForPicker);
    }
  }, 100);

  window.addEventListener('resize', function () {
    initSlider();
  });

  // form logic
  var form = {
    url: document.querySelector('#url'),
    interests: [],
    moreDetails: document.querySelector('#moreDetails'),
    firstName: document.querySelector('#firstName'),
    lastName: document.querySelector('#lastName'),
    email: document.querySelector('#email'),
    appDate: document.querySelector('#date'),
    appTime: document.querySelector('#time'),
    appTimezone: document.querySelector('#timezone'),
    //appTimezone: getTimezone().replace(/ /g, ''),
    // selectors
    stepOne: document.querySelector('#submitS1'),
    submit: document.querySelector('#submitForm'),
    messages: document.querySelector('#errorMessage')
    // hidden fields
    // csrf_name: document.querySelector('input[name="csrf_name"]'),
    // csrf_value: document.querySelector('input[name="csrf_value"]')
  };

  // Clear a field's error state as soon as the visitor edits it
  document.querySelectorAll('#landing-page-assessment input, #landing-page-assessment textarea').forEach(function (el) {
    el.addEventListener('input', function () {
      el.removeAttribute('aria-invalid');
      el.classList.remove('invalid');
    });
  });

  // Set the timezone field to the visitor's local timezone
  form.appTimezone.value = Intl.DateTimeFormat().resolvedOptions().timeZone;

  // on step one
  form.stepOne.addEventListener('click', function () {
    // validate fields
    var validFields = validateFields('one');

    if(validFields){
      // hide step one
      firstStep.classList.add('hidden');
      // move to step two
      secondStep.classList.remove('hidden');
      firstNavStep.classList.remove('active');
      firstNavStep.classList.add('complete');
      secondNavStep.classList.add('active');
      setCurrentStep(secondNavStep);
      document.getElementById('contactForm').scrollIntoView();
      form.firstName.focus();
    } else {
      // form.messages.style.display = 'block';
    }
  });

  // on step two
  form.submit.addEventListener('click', function () {

    // validate fields
    var validFields = validateFields('two');

    if (validFields){
      handleSubmit();
    }

  });

  
  // Send form data to Netlify
  const handleSubmit = () => {
    //e.preventDefault()
    let myForm = document.getElementById('landing-page-assessment');
    let formData = new FormData(myForm)
    fetch('/', {
      method: 'POST',
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(formData).toString()
    })
    .then(data => {

      // hide step two
      secondStep.classList.add('hidden');
      secondStep.classList.remove('active');
      secondNavStep.classList.add('complete');
      secondNavStep.classList.remove('active');
      thirdNavStep.classList.add('active');
      setCurrentStep(thirdNavStep);

      // display step three
      thirdStep.classList.remove('hidden');
      document.querySelector('.firstName').innerText = document.querySelector('#firstName').value; 
      document.querySelector('.thx-gif').setAttribute('src', 'https://media.giphy.com/media/WZ4M8M2VbauEo/source.gif');
      document.getElementById('contactForm').scrollIntoView();
      document.getElementById('thanksHeading').focus();

    }).catch(function () {
      showError('Oops, something went wrong sending your request. Please try again.', form.submit);
    })
  }

  // Listen for form submissions
  // document.querySelector("form").addEventListener("submit", handleSubmit);

  // on form submit
  /*
  form.submit.addEventListener('click', function () {

    // 1. validate fields
    var validFields = validateFields('two');

    if (validFields) {
      // 2. get interests array & other data
      document.querySelectorAll('input[type="checkbox"]').forEach(function (interest) {
        if (interest.checked) {
          form.interests.push(interest.value);
        }
      });

      form.interests = form.interests.join(); 
      
      var requestData = 'url=' + form.url.value +
      '&interests=' + form.interests +
      '&moreDetails=' + form.moreDetails.value +
      '&firstName=' + form.firstName.value +
      '&lastName=' + form.lastName.value +
      '&email=' + form.email.value +
      '&appDate=' + form.appDate.value +
      '&appTime=' + form.appTime.value +
      '&timezone=' + form.timezone;
      // '&csrf_name=' + form.csrf_name.value +
      // '&csrf_value=' + form.csrf_value.value;


  
      // 2.1 send request
      var request = new XMLHttpRequest();

      request.onload = function () {
         // update add to calendar button data
         var calendarDate = form.appDate.value.replace(/-/g, '/'),
             calendarTime = form.appTime.value,
             appDateAndTime = calendarDate + ' ' + calendarTime;

             // console.log(appDateAndTime);

         var myCalendar = createCalendar({
          options: {
            id: 'addToCalendar'
          },
          data: {
            title: 'Commitee appointment',
            start: new Date(appDateAndTime),
            duration: 60,
            // description: 'Get on the front page of HN, then prepare for world domination.'
          }
        });
        
        document.querySelector('.step__three fieldset').appendChild(myCalendar);

        // on step three
        var addToCalendarLabel = document.querySelector('#addToCalendar label.add-to-calendar-checkbox');
        addToCalendarLabel.innerText = 'Add to Calendar';
        addToCalendarLabel.classList.add('btn', 'btn-prim');

        var wrapperEl = document.createElement('div');
        wrapperEl.classList.add('options-wrapper');
        document.querySelector('#addToCalendar').append(wrapperEl);

        addToCalendarLabel.addEventListener('click', function (event) {
          event.preventDefault();

          document.querySelectorAll(".add-to-calendar a").forEach(function(el){
            wrapperEl.append(el);
          })

          wrapperEl.classList.toggle('active');

          thirdNavStep.classList.add('complete');
        });


      };


      request.open('post', '/');
      request.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');

      request.onreadystatechange = function() { 
        if (this.readyState === XMLHttpRequest.DONE && this.status === 200) {
          handleResponse(this.status);
        } 
      }

      request.send(requestData);
    }

  });
  */
  

})();


/* form functions */
function validateFields(step) {
  var invalid = [];

  switch(step){
    case 'one':
      var url = document.querySelector('#url'),
          interest = document.querySelector('input[type="checkbox"]:checked'),
          urlRegex = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/gi;

      markInvalid(url, !url.value.match(urlRegex), invalid);
      if (!interest) invalid.push(document.querySelector('#check__factors'));

      if (!invalid.length) {
        clearError();
        return true;
      }
      showError('Please ensure your landing page URL is correct and you have at least one interest checked.', invalid[0]);
    break;

    case 'two':
      var emailRegex = /^[a-zA-Z0-9.!#$%&’*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/,
          email = document.querySelector('#email');

      ['#firstName', '#lastName'].forEach(function (sel) {
        var el = document.querySelector(sel);
        markInvalid(el, !el.value.trim(), invalid);
      });
      markInvalid(email, !email.value.match(emailRegex), invalid);
      ['#date', '#time'].forEach(function (sel) {
        var el = document.querySelector(sel);
        markInvalid(el, !el.value, invalid);
      });

      if (!invalid.length && document.querySelector('#timezone').value) {
        clearError();
        return true;
      }
      showError('Please complete all the fields below before moving on to the next step.', invalid[0]);
    break;
  }
}

function markInvalid(el, isInvalid, list) {
  if (isInvalid) {
    el.setAttribute('aria-invalid', 'true');
    el.classList.add('invalid');
    list.push(el);
  } else {
    el.removeAttribute('aria-invalid');
    el.classList.remove('invalid');
  }
}

// #errorMessage is a role="alert" live region: setting its text announces it
function showError(message, focusTarget) {
  var errorMessage = document.querySelector('#errorMessage');
  errorMessage.textContent = message;
  errorMessage.classList.add('active');
  document.getElementById('contactForm').scrollIntoView();
  if (focusTarget) focusTarget.focus();
}

function clearError() {
  var errorMessage = document.querySelector('#errorMessage');
  errorMessage.textContent = '';
  errorMessage.classList.remove('active');
}

function setCurrentStep(stepEl) {
  document.querySelectorAll('.form__steps .step').forEach(function (el) {
    el.removeAttribute('aria-current');
  });
  stepEl.setAttribute('aria-current', 'step');
}

function prefersReducedMotion() {
  return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function handleResponse(requestStatus) {
 var secondStep = document.querySelector('.form__wrapper .step__two'),
     secondNavStep = document.querySelector('.form__steps .step__two'),
     thirdNavStep = document.querySelector('.form__steps .step__three'),
     thirdStep = document.querySelector('.form__wrapper .step__three');

  if (requestStatus === 200) {
    // hide step two
    secondStep.classList.add('hidden');
    secondStep.classList.remove('active');
    secondNavStep.classList.add('complete');
    secondNavStep.classList.remove('active');
    thirdNavStep.classList.add('active');

    // display step three
    thirdStep.classList.remove('hidden');
    document.querySelector('.firstName').innerText = document.querySelector('#firstName').value; 
    document.querySelector('.thx-gif').setAttribute('src', 'https://media.giphy.com/media/WZ4M8M2VbauEo/source.gif');
    document.getElementById('contactForm').scrollIntoView();
  } else {
    document.getElementById('contactForm').scrollIntoView();
    document.querySelector('#errorMessage').innerText = 'Oops, something went wrong. Please try again later.';
    document.querySelector('#errorMessage').classList.add('active');
  }
}

/*
function getTimezone() {
  return /\((.*)\)/.exec(new Date().toString())[1];
}
*/



/* other functions */

function animateHTML() {
  var elems, windowHeight;

  var init = function init() {
    elems = document.getElementsByClassName("hiddenE");
    windowHeight = window.innerHeight;

    _addEventHandlers();
  };

  var _addEventHandlers = function _addEventHandlers() {
    window.addEventListener("scroll", _checkPosition);
    window.addEventListener("resize", init);
  };

  var _checkPosition = function _checkPosition() {
    for (var i = 0; i < elems.length; i++) {
      var posFromTop = elems[i].getBoundingClientRect().top;

      if (posFromTop - windowHeight <= -150) {
        var actualSrc = elems[i].getAttribute('data-src');
        elems[i].setAttribute('src', actualSrc);

        if (elems[i].classList.contains('hiddenE')) {
          elems[i].classList.replace("hiddenE", "fade-in");
        }
      }
    }
  };

  return {
    init: init
  };
}

function initFlatpickr(flatpickr) {
  flatpickr("#date", {
    disableMobile: true,
    allowInput: true,
    dateFormat: "m-d-Y",
    minDate: new Date().fp_incr(1), // tomorrow
    maxDate: new Date().fp_incr(14), // 2 weeks ahead
    "disable": [function (date) {
      // exclude weekends
      return date.getDay() === 0 || date.getDay() === 6;
    }],
    "locale": {
      "firstDayOfWeek": 1 // start week on Monday
    }
  });

  flatpickr("#time", {
    disableMobile: true,
    allowInput: true,
    enableTime: true,
    noCalendar: true,
    dateFormat: "H:i",
    minDate: "09:00",
    maxDate: "18:00",
    time_24hr: false
  });
}

function initSlider() {
  // tiny-slider loads async; wait for it instead of throwing (which would stop the form from wiring up)
  if (typeof tns !== 'function') {
    clearTimeout(initSlider.retry);
    initSlider.retry = setTimeout(initSlider, 100);
    return;
  }
  // if mobile & the carousel hasn't been initiated
  if (window.innerWidth < 1000 && !document.querySelector('.tns-outer')) {
    slider = tns({
      container: '.carousel',
      items: 1,
      slideBy: 'page',
      navPosition: 'bottom',
      controls: false,
      // preventScrollOnTouch: 'auto'
    });
  } else if (window.innerWidth > 1000 && document.querySelector('.tns-outer')) {
    slider.destroy();
  }
}

function scrollTo() {
  var links = document.querySelectorAll('.scroll');
  links.forEach(function (each) {
    return each.onclick = scrollAnchors;
  });
}

function scrollAnchors(e) {
  var respond = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : null;

  var distanceToTop = function distanceToTop(el) {
    return Math.floor(el.getBoundingClientRect().top);
  };

  e.preventDefault();
  var targetID = respond ? respond.getAttribute('href') : this.getAttribute('href');
  var targetAnchor = document.querySelector(targetID);
  if (!targetAnchor) return;
  var originalTop = distanceToTop(targetAnchor);
  window.scrollBy({
    top: originalTop,
    left: 0,
    behavior: prefersReducedMotion() ? 'auto' : 'smooth'
  });
  // move keyboard/screen reader focus to the section we scrolled to
  if (!targetAnchor.hasAttribute('tabindex')) targetAnchor.setAttribute('tabindex', '-1');
  targetAnchor.focus({ preventScroll: true });
  var checkIfDone = setInterval(function () {
    var atBottom = window.innerHeight + window.pageYOffset >= document.body.offsetHeight - 2;

    if (distanceToTop(targetAnchor) === 0 || atBottom) {
      clearInterval(checkIfDone);
    }
  }, 100);
}

var mopedSVG;

function initWheelTurn(svgSelector) {
  if (window.svgDocument == null) {
    mopedSVG = document.querySelector(svgSelector).ownerDocument;
  }
  addRotateTransform(mopedSVG, '.wheel-1', 2, 1);
  addRotateTransform(mopedSVG, '.wheel-2', 2, 1);
}

function addRotateTransform(svg, targetSelector, dur, dir) {
  var my_element = svg.querySelector(targetSelector);
  var a = svg.createElementNS("http://www.w3.org/2000/svg", "animateTransform");
  var bb = my_element.getBBox();
  var cx = bb.x + bb.width/2;
  var cy = bb.y + bb.height/2;
  a.setAttributeNS(null, "attributeName", "transform");
  a.setAttributeNS(null, "attributeType", "XML");
  a.setAttributeNS(null, "type", "rotate");
  a.setAttributeNS(null, "dur", dur + "s");
  a.setAttributeNS(null, "repeatCount", "indefinite");
  a.setAttributeNS(null, "from", "0 "+cx+" "+cy);
  a.setAttributeNS(null, "to", 360*dir+" "+cx+" "+cy);
  my_element.appendChild(a);
  a.beginElement();
}
