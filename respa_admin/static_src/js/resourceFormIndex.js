import { initializeEventHandlers, initialSortPeriodDays, setClonableItems, calendarHandler, coloredDropdownListener, addDropdownColor }  from './resourceForm';
import { toggleCurrentLanguage, calculateTranslatedFields }  from './resourceFormLanguage';

function start() {
  initializeEventHandlers();
  setClonableItems();
  toggleCurrentLanguage();
  calculateTranslatedFields();
  calendarHandler();
  initialSortPeriodDays();
  addDropdownColor();
  coloredDropdownListener();
}

window.addEventListener('load', start, false);
