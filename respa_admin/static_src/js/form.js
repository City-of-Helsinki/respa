import * as shortID from 'shortid';

// bind the event handler for closing notification to the elements (buttons)
// since we cant do it directly in the html because of the scope
export function enableNotificationHandler() {
  let notifications = document.getElementsByClassName('noti');
  Array.prototype.forEach.call(notifications, (noti) => {
    noti.getElementsByTagName('button')[0].addEventListener('click', () => noti.remove(), false);
  });
}

// event handler to add new hour accordion to the hours list
export function addNewPeriod() {
  let periodList = $('.present-hours-list:first');
  let periodItem = periodList.find('.accordion-item:first');
  if (periodItem) {
    // clone an existing item in the DOM, a hack to reuse the template
    let newItem = periodItem.clone();
    const temporaryId = shortID.generate();

    // use the new id to re assign attributes of the cloned element
    newItem.attr('id', `accordion-item-${temporaryId}`);
    newItem.find('.dropdown-time').attr('id', `accordion${temporaryId}`);
    newItem.find('.panel-heading').attr({
      id: `heading${temporaryId}`
    });
    newItem.find('.panel-heading a').attr({
      href: `#collapse${temporaryId}`,
      "aria-controls": `#collapse${temporaryId}`
    });
    newItem.find('.panel-collapse').attr({
      "aria-labelledby": `heading${temporaryId}`,
      id: `collapse${temporaryId}`
    });
    newItem.find('button.delete-time').attr('id', `remove-hour-${temporaryId}`);

    // cloning doesn't include eventlistener binding so we do it manually here
    newItem.find('button.delete-time').click(() => removeHourHandler(temporaryId));
    newItem.find('button.add-time').click(() => addNewDay(temporaryId));

    periodList.append(newItem);

    updatePeriodsTotalForms();
    updatePeriodIndices();
    updateDaysIndices(newItem.find('#period-days-list'), temporaryId);
    updateDaysMgmtFormIndices(temporaryId);
  }
}

export function updatePeriodsTotalForms() {
  document.getElementById('id_periods-TOTAL_FORMS').value =
    document.getElementById('current-periods-list').childElementCount;
}

/*
* Update the indices of the inputs in the period
* input boxes.
* */
function updatePeriodIndices() {
  let $periods = $('#current-periods-list').children();

  $periods.each(function (rowId, row) {
    let $periodRow = $(row).find('#period-input');

    $periodRow.children().each(function (cellIndex, cell) {
      let $inputCells = $(cell).find('input');

      $inputCells.each(function (cellIndex, cell) {
        $(cell).attr('id', $(cell).attr('id').replace(/-(\d+)-/, "-" + rowId + "-"));
        $(cell).attr('name', $(cell).attr('name').replace(/-(\d+)-/, "-" + rowId + "-"));
      })
    });
  });
}

/*
* Updates the indices of the various input boxes
* in the each day under a specific period.
* */
function updateDaysIndices(daysList, periodId) {
  let $inputPeriodId = $('#collapse' + periodId).find('#period-input').children().find('input')[0].id;
  let periodIdNumber = $inputPeriodId.match(/\d+/)[0];

  daysList.children().each(function (dayIndex, day) {
    $(day).each(function (inputIndex, inputRow) {

      let $inputCells = $(inputRow).find('input');
      let $selectCells = $(inputRow).find('select');

      $inputCells.each(function (cellIndex, cellInput) {
        $(cellInput).attr('id', $(cellInput).attr('id').replace(/-(\d+)-(\d+)-/, '-' + periodIdNumber + '-' + dayIndex + '-'));
        $(cellInput).attr('name', $(cellInput).attr('name').replace(/-(\d+)-(\d+)-/, '-' + periodIdNumber + '-' + dayIndex + '-'));
      });

      $selectCells.each(function (cellIndex, cellInput) {
        $(cellInput).attr('id', $(cellInput).attr('id').replace(/-(\d+)-(\d+)-/, '-' + periodIdNumber + '-' + dayIndex + '-'));
        $(cellInput).attr('name', $(cellInput).attr('name').replace(/-(\d+)-(\d+)-/, '-' + periodIdNumber + '-' + dayIndex + '-'));
      });
    })
  });
}

function addNewDay(periodId) {
  let $collapseItem = $('#collapse' + periodId);
  let $dayList = $collapseItem.find('#period-days-list');
  let firstElementId = $dayList.children()[0].id;
  let firstDayItem = $dayList.find('#' + firstElementId);
  let newItem = firstDayItem.clone();

  //Update the id of the newly cloned item.
  newItem.attr('id', `period-day-${getShortId()}`);

  //Update the id of the generated item to avoid collisions.
  firstDayItem.attr('id', `period-day-${getShortId()}`);

  //Attach the event handler to next item's remove button.
  newItem.find('button.remove-day').click(() => removeDay(newItem[0]));

  //Append the new day to current list.
  $dayList.append(newItem);

  updatePeriodIndices();
  updateDaysIndices($dayList, periodId);
  updateTotalDays($collapseItem);
}

/*
* Update the indices in the management form of the days
* to match the current period.
* */
export function updateDaysMgmtFormIndices(periodId) {
  let $collapseItem = $('#collapse' + periodId);
  let $inputPeriodId = $($collapseItem).find('#period-input').children().find('input')[0].id;
  let periodIdNumber = $inputPeriodId.match(/\d+/)[0];
  let $management_form_inputs = $($collapseItem).find('#days-management-form').find('input');

  $management_form_inputs.each(function (id, input) {
    $(input).attr('id', $(input).attr('id').replace(/id_days-periods-(\d+)-/, 'id_days-periods-' + periodIdNumber + '-'));
    $(input).attr('name', $(input).attr('id').replace(/days-periods-(\d+)-/, 'days-periods-' + periodIdNumber + '-'));
  });
}

/*
* Update the TOTAL_FORMS value in the management form of the days
* in the corresponding period.
* */
export function updateTotalDays(collapseItem) {
  let $inputPeriodId = $(collapseItem).find('#period-input').children().find('input')[0].id;
  let periodIdNumber = $inputPeriodId.match(/\d+/)[0];
  let $periodDaysList = $(collapseItem).find('#period-days-list');


  $(collapseItem).find('#id_days-periods-' + periodIdNumber + '-TOTAL_FORMS')[0].value =
    $periodDaysList[0].childElementCount;
}

function getShortId() {
  return shortID.generate();
}

export function removeDay(dayNode) {
  let daysList = dayNode.parentNode;
  dayNode.remove(dayNode);

  updatePeriodIndices(daysList);
  updateDaysIndices(daysList);
}


export function enableRemoveDay() {
  let button = document.getElementById('btn-remove-day');
  button.addEventListener('click', () => removeDay(button.parentNode), false);
}

export function enableAddNewDay() {
  let button = document.getElementById('btn-add-new-day');
  let baseIndex = 0;
  button.addEventListener('click', () => addNewDay(baseIndex), false);
}

// bind the event handler for adding new hour to the element (button)
export function enableAddingNewHour() {
  let button = document.getElementById('add-new-hour');
  button.addEventListener('click', addNewPeriod, false);
}

// bind the event handler for removing an hour item to its delete button
export function enableRemovingHour() {
  let buttons = document.getElementsByClassName('delete-time');
  Array.prototype.forEach.call(buttons, (button) => {
    let itemId = button.id.replace('remove-hour-', '');
    button.addEventListener('click', () => removeHourHandler(itemId), false);
  });
}

// event handler to remove an hour accordion item
// take the Id of that arcordion-item as argument
export function removeHourHandler(id) {
  let hourItem = document.getElementById(`accordion-item-${id}`);
  hourItem.remove();
  updatePeriodIndices();
}
