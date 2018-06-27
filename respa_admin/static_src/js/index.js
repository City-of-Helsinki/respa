import '../styles/base.scss';

import * as FormModule from './form.js';

function start() {
    const  {
        enableAddingNewHour,
        enableRemovingHour,
        enableNotificationHandler
    } = FormModule;

    enableNotificationHandler();
    enableAddingNewHour();
    enableRemovingHour();
}

function exit() {}

window.addEventListener('load', start, false);
