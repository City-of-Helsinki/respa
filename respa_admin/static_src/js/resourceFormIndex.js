import { initializeEventHandlers, setClonableItems }  from './resourceForm';
import { toggleCurrentLanguage, calculateTranslatedFields }  from './resourceFormLanguage';

function start() {
  initializeEventHandlers();
  setClonableItems();
  toggleCurrentLanguage();
  calculateTranslatedFields();
}

window.addEventListener('load', start, false);
