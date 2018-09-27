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
  enableNotificationHandler();
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
* Bind the event handler for closing notification to the elements (buttons)
* since we cant do it directly in the html because of the scope
* */
function enableNotificationHandler() {
  let notifications = document.getElementsByClassName('noti');
  Array.prototype.forEach.call(notifications, (noti) => {
    noti.getElementsByTagName('button')[0].addEventListener('click', () => noti.remove(), false);
  });
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

export function getPeriodsList() {
  return document.getElementById('current-periods-list').children;
}
