import '../styles/base.scss';

import { initializeEventHandlers, setClonableItems }  from './form';

function start() {
  initializeEventHandlers();
  setClonableItems();
}

window.addEventListener('load', start, false);
