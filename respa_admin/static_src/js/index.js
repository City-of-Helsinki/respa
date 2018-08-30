import '../styles/base.scss';

import * as FormModule from './form.js';

function start() {
    const  {
      enableAddDaysByDate,
      enableAddNewPeriod,
      enableNotificationHandler,
      enableRemovePeriod,
      copyInitialPeriodAndDay
    } = FormModule;
    enableAddDaysByDate();
    enableAddNewPeriod();
    enableNotificationHandler();
    enableRemovePeriod();
    copyInitialPeriodAndDay();
}

function exit() {}

window.addEventListener('load', start, false);
