import { initializeEventHandlers, initialSortPeriodDays, setClonableItems }  from './resourceForm';
import { toggleCurrentLanguage, calculateTranslatedFields }  from './resourceFormLanguage';

function start() {
  initializeEventHandlers();
  setClonableItems();
  toggleCurrentLanguage();
  calculateTranslatedFields();
  initialSortPeriodDays();
}

window.addEventListener('load', start, false);
