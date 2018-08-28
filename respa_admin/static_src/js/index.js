import '../styles/base.scss';

import * as FormModule from './form.js';

function start() {
    const  {
      enableAddDaysByDate,
      enableAddNewPeriod,
      enableNotificationHandler,
      copyInitialDay,
      enableRemovePeriod,
    } = FormModule;
    enableAddDaysByDate();
    enableAddNewPeriod();
    enableNotificationHandler();
    copyInitialDay();
    enableRemovePeriod();

}

function exit() {}

window.addEventListener('load', start, false);
