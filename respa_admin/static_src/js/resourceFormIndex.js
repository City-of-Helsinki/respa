import { initializeEventHandlers, initialSortPeriodDays, setClonableItems, calendarHandler }  from './resourceForm';
import { toggleCurrentLanguage, calculateTranslatedFields }  from './resourceFormLanguage';

function start() {
  initializeEventHandlers();
  setClonableItems();
  toggleCurrentLanguage();
  calculateTranslatedFields();
  calendarHandler();
  initialSortPeriodDays();
}

window.addEventListener('load', start, false);
