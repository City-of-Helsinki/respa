import '../styles/base.scss';

import { initializeEventHandlers }  from './form';

// function start() {
//     const  {
//       // enableAddDaysByDate,
//       // enableAddNewPeriod,
//       // enableNotificationHandler,
//       // enableRemovePeriod,
//       // enableAddNewImage,
//       // // enableRemoveImage,
//       // copyInitialItems,
//     } = FormModule;
//     // enableAddDaysByDate();
//     // enableAddNewPeriod();
//     // enableNotificationHandler();
//     // enableRemovePeriod();
//     // enableAddNewImage();
//     // // enableRemoveImage();
//     // copyInitialItems();
// }

function exit() {}

window.addEventListener('load', initializeEventHandlers, false);
