import { initializeEventHandlers, setClonableItems }  from './resourceForm';

function start() {
  initializeEventHandlers();
  setClonableItems();
}

window.addEventListener('load', start, false);
