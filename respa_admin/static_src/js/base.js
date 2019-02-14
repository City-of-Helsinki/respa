// Base events that will be loaded in base.html

/*
* Bind the event handler for closing notification to the elements (buttons)
* since we cant do it directly in the html because of the scope
* */
function enableNotificationHandler() {
    let notifications = document.getElementsByClassName('noti');
    Array.prototype.forEach.call(notifications, (noti) => {
        noti.getElementsByTagName('button')[0].addEventListener('click', () => noti.remove(), false);
    });
}

/*
* Attach all the event handlers to their objects upon load.
* */
export function initializeBaseEventHandlers() {
    enableNotificationHandler();
  }