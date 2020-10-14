import { initializeResourceForm, calendarHandler, coloredDropdownListener, addDropdownColor }  from './resourceForm';
import { toggleCurrentLanguage, calculateTranslatedFields }  from './resourceFormLanguage';

function start() {
  calendarHandler();
  initializeResourceForm();
  toggleCurrentLanguage();
  calculateTranslatedFields();
  addDropdownColor();
  coloredDropdownListener();
}

window.addEventListener('load', start, false);
