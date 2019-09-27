import { initializeUserFormEventHandlers }  from './userForm';

function start() {
  initializeUserFormEventHandlers();
}

window.addEventListener('load', start, false);
