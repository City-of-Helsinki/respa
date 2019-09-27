import { initializeUnitForm, calendarHandler }  from './unitForm';
import { toggleCurrentLanguage, calculateTranslatedFields }  from './resourceFormLanguage';

function start() {
  initializeUnitForm();
  toggleCurrentLanguage();
  calculateTranslatedFields();
  calendarHandler();
}

window.addEventListener('load', start, false);
