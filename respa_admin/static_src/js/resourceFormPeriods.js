import { getEmptyDayItem, getEmptyPeriodItem, getPeriodsList } from "./resourceForm";

/*
* Iterate all periods and update their input indices.
* */
function updatePeriodInputIds() {
  let periods = $('#current-periods-list').children();

  periods.each(function (i, periodItem) {
    let inputs = $(periodItem).find('input');

    inputs.each(function (inputIndex, input) {
      $(input).attr('id', $(input).attr('id').replace(/-(\d+)-/, "-" + i + "-"));
      $(input).attr('name', $(input).attr('name').replace(/-(\d+)-/, "-" + i + "-"));
    });

    updatePeriodChildren($(periodItem), i);
    updatePeriodButtonsIds($(periodItem), i);
  });
}

/*
* Update all the button ids in the Period.
* */
function updatePeriodButtonsIds(periodItem, idNum) {
  periodItem.find('button.delete-time').attr('id', `remove-button-${idNum}`);
  periodItem.find('button.copy-time-btn').attr('id', `copy-time-period-${idNum}`);
}

/*
* Update children div ids of a period.
* */
function updatePeriodChildren(periodItem, idNum) {
  periodItem.attr('id', `accordion-item-${idNum}`);
  periodItem.find('.dropdown-time').attr('id', `accordion${idNum}`);
  periodItem.find('.date-input').attr('id', `date-inputs-${idNum}`);
  periodItem.find('.panel-heading').attr({id: `heading${idNum}`});
  periodItem.find('.period-input').attr({id: `period-input-${idNum}`});

  periodItem.find('.panel-heading a').attr({
    href: `#collapse${idNum}`,
    "aria-controls": `#collapse${idNum}`
  });

  periodItem.find('.panel-collapse').attr({
    "aria-labelledby": `heading${idNum}`,
    id: `collapse${idNum}`
  });
}

/*
* Sort period days based on day of week, beginning of the selection first.
*/
export function sortPeriodDays($periodItem) {
  let $daysListContainer = $periodItem.find('#period-days-list');
  let $daysList = $daysListContainer.children();
  let $dateInputs = $periodItem.find("[id^='date-input'] input");
  let startDate = new Date(convertDateFormat($dateInputs[0].value));
  let firstWeekday = getDayValuesInterval([startDate])[0];
  let daysInWeek = 7;

  $daysList.detach().sort(function (a, b) {
    let aDay = parseInt(a.querySelector("[id*='-weekday']").value);
    if (aDay < firstWeekday) {
      aDay = aDay + daysInWeek; // consider weekdays before firstWeekday as "next week" for sorting
    }
    let bDay = parseInt(b.querySelector("[id*='-weekday']").value);
    if (bDay < firstWeekday) {
      bDay = bDay + daysInWeek;
    }
    return aDay > bDay;
  });

  $daysListContainer.append($daysList);
}

/*
* Updates the indices of the various input boxes
* in the each day under a specific period.
*
* Django expects that existing items come first and new items come last in
* the formset. We index the originals first and new ones last.
* */
function updatePeriodDaysIndices($periodItem) {
  let originalDaysList = $periodItem.find('.weekday-row.original-day');
  let newDaysList = $periodItem.find('.weekday-row:not(.original-day)');
  let periodIdNum = $periodItem[0].id.match(/[0-9]/)[0];

  const setIndex = function (dayIndex, day) {
    $(day).attr('id', $(day).attr('id').replace(/-(\d+)-(\d+)/, '-' + periodIdNum + '-' + dayIndex));

    $(day).each(function (inputIndex, inputRow) {
      let $inputCells = $(inputRow).find('input');
      let $selectCells = $(inputRow).find('select');
      let $inputLabels = $(inputRow).find('label');

      $inputLabels.each(function (cellIndex, cellInput) {
        $(cellInput).attr('for', $(cellInput).attr('for').replace(/-(\d+)-(\d+)-/, '-' + periodIdNum + '-' + dayIndex + '-'));
      });

      $inputCells.each(function (cellIndex, cellInput) {
        $(cellInput).attr('id', $(cellInput).attr('id').replace(/-(\d+)-(\d+)-/, '-' + periodIdNum + '-' + dayIndex + '-'));
        $(cellInput).attr('name', $(cellInput).attr('name').replace(/-(\d+)-(\d+)-/, '-' + periodIdNum + '-' + dayIndex + '-'));
      });

      $selectCells.each(function (cellIndex, cellInput) {
        $(cellInput).attr('id', $(cellInput).attr('id').replace(/-(\d+)-(\d+)-/, '-' + periodIdNum + '-' + dayIndex + '-'));
        $(cellInput).attr('name', $(cellInput).attr('name').replace(/-(\d+)-(\d+)-/, '-' + periodIdNum + '-' + dayIndex + '-'));
      });
    })
  };

  let dayIndex = 0;
  for (let i = 0;i < originalDaysList.length; i++) {
    setIndex(dayIndex, originalDaysList[i]);
    dayIndex++;
  }
  for (let i = 0;i < newDaysList.length; i++) {
    setIndex(dayIndex, newDaysList[i]);
    dayIndex++;
  }
}

/*
* Update all ids for the days input boxes in each period.
* */
function updateAllPeriodDaysIndices() {
  let periodList = $('#current-periods-list').children();
  for (let i = 0; i < getPeriodCount(); i++) {
    updatePeriodDaysIndices($(periodList[i]));
  }
}

/*
* Update the indices in the management form of the days
* to match the current period.
* */
function updatePeriodDaysMgmtFormIndices(periodItem, index = null) {
  let $managementFormInputs = $(periodItem).find('#days-management-form').find('input');

  if (index === null) {
    index = getPeriodCount() - 1;
  }

  $managementFormInputs.each(function (id, input) {
    $(input).attr('id', $(input).attr('id').replace(/id_days-periods-(\d+)-/, 'id_days-periods-' + index + '-'));
    $(input).attr('name', $(input).attr('name').replace(/days-periods-(\d+)-/, 'days-periods-' + index + '-'));
  });
}

/*
* Get the amount of periods in the form.
* */
function getPeriodCount() {
  return $('#current-periods-list')[0].children.length;
}

/*
* Update all indices in the management form of the current periods.
* */
function updateAllDaysMgmtFormIndices() {
  let periodList = $('#current-periods-list').children();
  for (let i = 0; i < getPeriodCount(); i++) {
    updatePeriodDaysMgmtFormIndices(periodList[i], i);
  }
}

/*
* General function for restoring the values in the
* management form for the days in a period.
* */
function restoreDaysMgmtFormValues(periodItem) {
  periodItem.find('#days-management-form').find('[id$="-TOTAL_FORMS"]').val('0');
  periodItem.find('#days-management-form').find('[id$="-INITIAL_FORMS"]').val('0');
}

/*
* Update the TOTAL_FORMS value in the management form of the days
* in the corresponding period.
* */
export function updateTotalDays($periodItem) {
  let amountOfDays = $periodItem.find('#period-days-list').children().length;
  let amountOfOriginalDays = $periodItem.find('#period-days-list').children('.weekday-row.original-day').length;
  let daysMgmtForm = $periodItem.find('#days-management-form');
  daysMgmtForm.find("[id$='-TOTAL_FORMS']").val(amountOfDays);
  daysMgmtForm.find("[id$='-INITIAL_FORMS']").val(amountOfOriginalDays);
}

/*
* Returns the day values from dates between the dates.
* ret: array of integers.
* */
function getDayValuesInterval(dateArray) {
  let days = [];

  for (let i = 0; i < dateArray.length; i++) {

    let day = dateArray[i].getDay();

    //The Javascript getDays() function's output does not correspond
    //to the Django models weekday choices.
    if (day === 0) {
      day = 6;
    } else {
      day--;
    }

    days.push(day.toString());
  }

  if (days.length <= 7) {
    return days;
  }

  //Return array without duplicate values.
  return Array.from(new Set(days));
}

/*
* Gets a list of dates between the given date inputs.
* */
function getDateInterval(startDate, endDate) {
  let dateArray = [];

  while (startDate <= endDate) {
    dateArray.push(new Date(startDate));
    startDate.setDate(startDate.getDate() + 1);
  }

  return dateArray;
}

/*
* Handle either removing or adding new days based
* on the date input fields.
* */
export function modifyDays($periodItem, $dates) {
  let dateInputs = $dates.find('input');
  let $daysList = $periodItem.find('#period-days-list');
  let $currentWeekdayObjects = $daysList.children().find("[id*='-weekday']");

  let startDate = new Date(convertDateFormat(dateInputs[0].value));
  let endDate = new Date(convertDateFormat(dateInputs[1].value));
  let currentDays = [];

  if ((!startDate || !endDate) || (startDate > endDate)) {
    return;
  }

  for (let i = 0; i < $currentWeekdayObjects.length; i++) {
    currentDays.push($currentWeekdayObjects[i].value.toString());
  }

  let newDays = getDayValuesInterval(getDateInterval(startDate, endDate));

  //If a value exists in newDays but not in currentDays => it is a new day to be added.
  for (let i  = 0; i < newDays.length; i++) {
    if (!currentDays.includes(newDays[i])) {
      addDay($daysList, newDays[i]);
    }
  }

  //If a value does not exist in newDays but it does exist in currentDays => remove it.
  for (let i = currentDays.length - 1; i >= 0 ; i--) {
    if (!newDays.includes(currentDays[i])) {
      removeDay($periodItem, i);
    }
  }

  if (newDays.length > 0) {
    sortPeriodDays($periodItem);
  }
  updatePeriodDaysIndices($periodItem);
  updateTotalDays($periodItem);
}

/*
* Takes a date in string format dd.mm.yyy and converts it
* to yyyy-mm-dd
* */
function convertDateFormat(dateString) {
  let strMatch = '[0-9]{2}.[0-9]{2}.[0-9]{4}';

  if (dateString.match(strMatch)) {
    let parts = dateString.split('.');
    dateString = parts[2] + '-' + parts[1] + '-' + parts[0];
  }

  return dateString;
}

/*
* Helper function for modifyDays(). Removes the n'th day in the list.
* */
function removeDay(periodItem, index) {
  periodItem.find(".weekday-row")[index].remove();
}

/*
* Add a new day to the period with the integer part of the ID
* and the integer representation of a weekday.
* */
function addDay(daysList, weekday) {
  let emptyDayItem = getEmptyDayItem();

  if (emptyDayItem) {
    let newDayItem = emptyDayItem.clone();

    newDayItem.find("[id*='-weekday']").val(weekday);
    daysList.append(newDayItem);
  }
}

/*
* Removes all days from a period.
* */
function removePeriodExtraDays(periodItem) {
  let periodItemDays = periodItem.find('#period-days-list').children();
  for (let i = 0; i < periodItemDays.length; i++) {
    periodItemDays[i].remove();
  }

  restoreDaysMgmtFormValues(periodItem);
}

/*
* Adds a new period item and updates all the ids where necessary.
* */
export function addNewPeriod() {
  // Get the list or periods.
  let $periodList = $('#current-periods-list');
  let emptyPeriodItem = getEmptyPeriodItem();

  if (emptyPeriodItem) {
    let newItem = emptyPeriodItem.clone();
    $periodList.append(newItem);

    updatePeriodsTotalForms();
    removePeriodExtraDays(newItem);
    updatePeriodInputIds();
    attachPeriodEventHandlers(newItem);
  }
}

/*
* Attach the event handlers to a period objects' buttons.
* */
function attachPeriodEventHandlers(periodItem) {
  //Attach event handler for removing a period (these are not cloned by default).
  let removeButton = periodItem.find(".delete-time");
  removeButton.click(() => removePeriod(periodItem));

  //Attach event handler for copying time periods.
  let copyButton = periodItem.find(".copy-time-btn");
  copyButton.click(() => copyTimePeriod(periodItem));

  //Attach the event handler for the date pickers.
  let $dates = periodItem.find("[id^='date-input']");
  $dates.change(() => modifyDays(periodItem, $dates));
}

function removePeriodEventHandlers(periodItem) {
  periodItem.find(".delete-time").off();
  periodItem.find(".copy-time-btn").off();
  periodItem.find("[id^='date-input']").off();

}

export function removePeriod(periodItem) {
  if (periodItem) {
    periodItem.remove();

    updatePeriodsTotalForms();
    updatePeriodInputIds();
    updateAllPeriodDaysIndices();
    updateAllDaysMgmtFormIndices();

    //Re-attach event handlers.
    const periods = getPeriodsList();
    for (let period of periods) {
      removePeriodEventHandlers($(period));
      attachPeriodEventHandlers($(period));
    }
  }
}

export function updatePeriodsTotalForms() {
  document.getElementById('id_periods-TOTAL_FORMS').value = getPeriodCount();
}

/*
* Appends a copy of the given period element.
* */
export function copyTimePeriod(periodItem) {
  let $periodsList = $('#current-periods-list');
  let newItem = $(periodItem).clone();
  $periodsList.append(newItem);

  updatePeriodInputIds();
  updatePeriodsTotalForms();
  attachPeriodEventHandlers(newItem);

  updateAllPeriodDaysIndices();
  updateAllDaysMgmtFormIndices();

  //Remove the copied ID from the previous ID
  //which ties the DOM object to a Database object.
  newItem.find("[id$='-id']").removeAttr('value');

  //Remove the days ids as well.
  newItem.find('#day-db-ids').children().each(function(i, input) {
    $(input).removeAttr('value');
  });

  //Reset initial forms in case there are some days present in the previous period.
  newItem.find('#days-management-form').find('[id$="-INITIAL_FORMS"]').val('0');
}
