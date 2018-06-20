import '../styles/base.scss';

function start() {
    enableNotificationHandling();
}

function exit() {}

function enableNotificationHandling() {
    let notifications = document.getElementsByClassName('noti');
    Array.prototype.forEach.call(notifications, (noti) => {
        noti.getElementsByTagName('button')[0].addEventListener('click', () => noti.remove(), false);
    });
}

window.addEventListener('load', start, false);
