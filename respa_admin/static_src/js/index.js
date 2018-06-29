import '../styles/base.scss';

import * as FormModule from './form.js';

function start() {
    const  {
        enableAddingNewHour,
        enableRemovingHour,
        enableNotificationHandler,
        updatePeriodsTotalForms,
        enableAddNewDay,
        enableRemoveDay,
    } = FormModule;

    enableAddNewDay();
    enableNotificationHandler();
    enableAddingNewHour();
    enableRemovingHour();
    updatePeriodsTotalForms();
    enableRemoveDay();
}

function exit() {}

window.addEventListener('load', start, false);
