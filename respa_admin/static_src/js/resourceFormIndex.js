import { initializeEventHandlers, setClonableItems }  from './resourceForm';
import { toggleCurrentLanguage }  from './resourceFormLanguage';

function start() {
  initializeEventHandlers();
  setClonableItems();
  toggleCurrentLanguage();
}

window.addEventListener('load', start, false);
