import {
  addNewImage,
  removeImage,
  updateImagesTotalForms,
} from './resourceFormImages';

import {
  addNewPeriod,
  updateTotalDays,
  updatePeriodsTotalForms,
  removePeriod,
  modifyDays,
  copyTimePeriod,
  sortPeriodDays,
} from './resourceFormPeriods';

import {
  toggleLanguage,
} from './resourceFormLanguage';

let emptyImageItem = null;
let emptyPeriodItem = null;
let emptyDayItem = null;

/*
* Attach all the event handlers to their objects upon load.
* */
export function initializeEventHandlers() {
  enablePeriodEventHandlers();
  enableAddNewPeriod();
  enableLanguageButtons();
  enableAddNewImage();
  enableRemoveImage();
}

export function setClonableItems() {
  setPeriodAndDayItems();
  setImageItem();
}

export function getEmptyImage() {
  return emptyImageItem;
}

export function getEmptyPeriodItem() {
  return emptyPeriodItem;
}

export function getEmptyDayItem() {
  return emptyDayItem;
}



/*
* Set empty day and period variables.
* */
function setPeriodAndDayItems() {
  //Get the last period in the list.
  let $periodList = $('#current-periods-list')[0].children;
  let $servedPeriodItem = $($periodList[$periodList.length-1]);

  //Get the last day from the period.
  let $daysList = $servedPeriodItem.find('#period-days-list')[0].children;
  let $servedDayItem = $daysList[$daysList.length-1];

  emptyDayItem = $($servedDayItem).clone();
  emptyDayItem.removeClass('original-day');  // added days are not original. used for sorting formset indices.
  emptyPeriodItem = $($servedPeriodItem).clone();

  $servedDayItem.remove();
  $servedPeriodItem.remove();

  //Iterate the existing days in all periods and remove the last one
  //which has been added from the backend.
  if ($periodList.length > 0) {
    for (let i = 0; i < $periodList.length; i++) {
      let $days = $($periodList[i]).find('#period-days-list');
      $days.children().last().remove();
      updateTotalDays($($periodList[i]));
    }
  }

  updatePeriodsTotalForms();
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
* Bind event for adding a new period to its corresponding button.
* */
function enableAddNewPeriod() {
  let button = document.getElementById('add-new-hour');
  button.addEventListener('click', addNewPeriod, false);
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

function enablePeriodEventHandlers() {
  let periods = getPeriodsList();

  for (let i = 0; i < periods.length; i++) {
    const copyButton = $('#copy-time-period-' + i);
    copyButton.click(() => copyTimePeriod(periods[i]));

    const $dates = $('#date-inputs-' + i);
    $dates.change(() => modifyDays($(periods[i]), $dates));

    const removeButton = $('#remove-button-' + i);
    removeButton.click(() => removePeriod(periods[i]));
  }
}

export function initialSortPeriodDays() {
  let periods = getPeriodsList();

  for (let i = 0; i < periods.length; i++) {
    sortPeriodDays($(periods[i]));
  }
}

export function getPeriodsList() {
  return document.getElementById('current-periods-list').children;
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