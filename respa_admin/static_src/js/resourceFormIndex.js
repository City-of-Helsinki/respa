import { initializeResourceForm, calendarHandler, coloredDropdownListener, addDropdownColor }  from './resourceForm';
import { toggleCurrentLanguage, calculateTranslatedFields }  from './resourceFormLanguage';

function start() {
  initializeResourceForm();
  toggleCurrentLanguage();
  calculateTranslatedFields();
  calendarHandler();
  addDropdownColor();
  coloredDropdownListener();
}

window.addEventListener('load', start, false);
