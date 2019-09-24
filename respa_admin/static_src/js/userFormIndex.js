import { initializeUserFormEventHandlers, removePermission, enableAddNewPermission, setEmptyPermissionItem}  from './userForm';

function start() {
  initializeUserFormEventHandlers();
  removePermission();
  enableAddNewPermission();
  setEmptyPermissionItem();
}

window.addEventListener('load', start, false);
