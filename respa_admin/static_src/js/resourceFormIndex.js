import { initializeEventHandlers, setClonableItems }  from './resourceForm';
import { toggleStartupLanguage }  from './resourceLanguageSwitcher';

function start() {
  initializeEventHandlers();
  setClonableItems();
  toggleStartupLanguage();
}

window.addEventListener('load', start, false);
