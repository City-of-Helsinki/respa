import {
  addNewImage,
  removeImage,
  updateImagesTotalForms,
} from './resourceFormImages';

import {
  initializePeriods,
} from './periods';

import {
  toggleLanguage,
} from './resourceFormLanguage';

let emptyImageItem = null;

export function initializeResourceForm() {
  initializeEventHandlers();
  initializePeriods();
  setImageItem();
}

/*
* Attach all the event handlers to their objects upon load.
* */
export function initializeEventHandlers() {
  enableLanguageButtons();
  enableAddNewImage();
  enableRemoveImage();
}

export function getEmptyImage() {
  return emptyImageItem;
}

/*
* Setter for the empty image item which is may
* be used for creating new image items in the DOM.
* */
function setImageItem() {
  //Get the last image.
  let $imageList = $('#images-list')[0].children;
  let $servedImageItem = $imageList[$imageList.length-1];

  //Clone it.
  emptyImageItem = $($servedImageItem).clone();

  //Remove it from the DOM.
  $servedImageItem.remove();

  //The image list is hidden by default in order to avoid
  //Image flashing when loading the page. Remove the hidden attribute.
  $('#images-list')[0].classList.remove('hidden');

  updateImagesTotalForms();
}

/*
* Bind event for adding images.
* */
function enableAddNewImage() {
  let imagePicker = document.getElementById('image-picker');
  imagePicker.addEventListener('click', addNewImage, false);
}

/*
* Bind events for removing an image.
* */
function enableRemoveImage() {
  let images = document.getElementById('images-list').children;

  for (let i = 0; i < images.length; i++) {
    let removeButton = document.getElementById('remove-image-' + i);
    let imageItem = $('#image-' + i);
    removeButton.addEventListener('click', () => removeImage(imageItem), false);
  }
}

/*
* Bind event for hiding/showing translated fields in form.
* */
function enableLanguageButtons() {
  let languageSwitcher = document.getElementsByClassName('language-switcher');
  let languagesAmount = languageSwitcher[0].children.length;

  for (let i = 0; i < languagesAmount; i++) {
    let languageButton = languageSwitcher[0].children[i];
    let language = languageButton.value;
    languageButton.addEventListener('click', () => toggleLanguage(language), false);
  }
}

export function calendarHandler() {
  // Copied from bootstrap-datepicker@1.8.0/js/locales/bootstrap-datepicker.fi.js
  // As it can not be imported as a module, and would need to be shimmed
  $.fn.datepicker.dates['fi'] = {
		days: ["sunnuntai", "maanantai", "tiistai", "keskiviikko", "torstai", "perjantai", "lauantai"],
		daysShort: ["sun", "maa", "tii", "kes", "tor", "per", "lau"],
		daysMin: ["su", "ma", "ti", "ke", "to", "pe", "la"],
		months: ["tammikuu", "helmikuu", "maaliskuu", "huhtikuu", "toukokuu", "kesäkuu", "heinäkuu", "elokuu", "syyskuu", "lokakuu", "marraskuu", "joulukuu"],
		monthsShort: ["tam", "hel", "maa", "huh", "tou", "kes", "hei", "elo", "syy", "lok", "mar", "jou"],
		today: "tänään",
		clear: "Tyhjennä",
		weekStart: 1,
		format: "d.m.yyyy"
	};
}

/*
* Inject class to display colored ball in a dropdown
*/
export function addDropdownColor() {
  let publicDropdown = document.getElementById('id_public');
  let publicDropdownValue = publicDropdown.options[publicDropdown.selectedIndex].value;
  let publicDropdownIcon = document.getElementById('public-dropdown-icon');

  let reservableDropdown = document.getElementById('id_reservable');
  let reservableDropdownValue = reservableDropdown.options[reservableDropdown.selectedIndex].value;
  let reservableDropdownIcon = document.getElementById('reservable-dropdown-icon');

  if(publicDropdownValue === 'True') {
    publicDropdownIcon.className = 'shape-success'
  }
  else {
    publicDropdownIcon.className = 'shape-warning';
  }

  if(reservableDropdownValue === 'True') {
    reservableDropdownIcon.className = 'shape-success'
  }
  else {
    reservableDropdownIcon.className = 'shape-danger';
  }
}

/*
* Listener to change the color of the color-coding ball when change happens
*/
export function coloredDropdownListener(event) {
  let publicDropdown = document.getElementById('id_public');
  let reservableDropdown = document.getElementById('id_reservable');
  publicDropdown.addEventListener('change', addDropdownColor, false);
  reservableDropdown.addEventListener('change', addDropdownColor, false);
}
