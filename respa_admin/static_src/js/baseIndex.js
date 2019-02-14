import { initializeBaseEventHandlers }  from './base';

function start() {
  initializeBaseEventHandlers();
}

window.addEventListener('load', start, false);
