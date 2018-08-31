import { addNewImage, removeImage, updateImagesTotalForms } from './images';
import { addNewPeriod, updateTotalDays, updatePeriodsTotalForms, removePeriod } from './periods';

//TODO: this might have to be sorted out. Global variables are not so good :/ Write getters instead.
export let emptyImageItem = null;
export let emptyPeriodItem = null;
export let emptyDayItem = null;

/*
* Attach all the event handlers to their objects upon load.
* */
export function initializeEventHandlers() {
  enableNotificationHandler();
  enableAddNewPeriod();
  enableRemovePeriod();
  enableAddDaysByDate();
  enableAddNewImage();
  enableRemoveImage();

  copyInitialItems();
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
* Copy the empty served period, day and image served from server
* for later cloning purposes.
* */

//TODO: break this out into smaller chunks.
function copyInitialItems() {
  //Get the last period in the list.
  let $periodList = $('#current-periods-list')[0].children;
  let $servedPeriodItem = $($periodList[$periodList.length-1]);

  //Get the last day from the period.
  let $daysList = $servedPeriodItem.find('#period-days-list')[0].children;
  let $servedDayItem = $daysList[$daysList.length-1];

  //Get the last image.
  let $imageList = $('#images-list')[0].children;
  let $servedImageItem = $imageList[$imageList.length-1];

  emptyDayItem = $($servedDayItem).clone();
  emptyPeriodItem = $($servedPeriodItem).clone();
  emptyImageItem = $($servedImageItem).clone();

  $servedDayItem.remove();
  $servedPeriodItem.remove();
  $servedImageItem.remove();

  //Iterate the existing days in all periods and remove the last one
  //which has been added from the backend.
  if ($periodList.length > 0) {
    for (let i = 0; i < $periodList.length; i++) {
      let $days = $($periodList[i]).find('#period-days-list');
      $days.children().last().remove();
      // updatePeriodDaysIndices(i); //TODO: might not be necessary to call this here since it's the last day.
      updateTotalDays(i);
    }
  }

  updateImagesTotalForms();
  updatePeriodsTotalForms();
}

/*
* Bind event for adding a new period to its corresponding button.
* */
function enableAddNewPeriod() {
  let button = document.getElementById('add-new-hour');
  button.addEventListener('click', addNewPeriod, false);
}

/*
* Bind event for removing a period to its corresponding button.
* */
function enableRemovePeriod() {
  let periods = document.getElementById('current-periods-list').children;

  for (let i = 0; i < periods.length; i++) {
    let removeButton = document.getElementById('remove-button-' + i);
    removeButton.addEventListener('click', () => removePeriod(i), false);
  }
}

/*
* Bind event for adding days to the date input fields.
* */
function enableAddDaysByDate() {
  let periods = document.getElementById('current-periods-list').children;

  for (let i = 0; i < periods.length; i++) {
    let inputDates = document.getElementById('date-inputs-' + i);
    inputDates.addEventListener('change', () => modifyDays(inputDates), false);
  }
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
export function enableRemoveImage() {
  let images = document.getElementById('images-list');

  for (let i = 0; i < images.length; i++) {
    let removeButton = document.getElementById('remove-image-' + i);
    removeButton.addEventListener('click', () => removeImage(i), false);
  }
}
