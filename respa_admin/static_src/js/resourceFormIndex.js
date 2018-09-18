import { initializeEventHandlers, setClonableItems }  from './resourceForm';
import { toggleStartupLanguage }  from './resourceFormLanguage';

function start() {
  initializeEventHandlers();
  setClonableItems();
  toggleStartupLanguage();
}

window.addEventListener('load', start, false);
