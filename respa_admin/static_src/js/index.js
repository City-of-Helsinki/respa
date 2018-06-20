import '../styles/base.scss';

import * as shortID from 'shortid';

function start() {
    enableNotificationHandling();
    enableAddingNewHour();
    enableRemovingHour();
}

function exit() {}

function enableNotificationHandling() {
    let notifications = document.getElementsByClassName('noti');
    Array.prototype.forEach.call(notifications, (noti) => {
        noti.getElementsByTagName('button')[0].addEventListener('click', () => noti.remove(), false);
    });
}

function addNewHour() {
    let hourList = $('.present-hours-list:first');
    let hourItem = hourList.find('.accordion-item:first');
    if (hourItem) {
        let newItem = hourItem.clone(true);
        const temporaryId = shortID.generate();
        newItem.attr('id', `accordion-item-${temporaryId}`);
        newItem.find('.dropdown-time').attr('id', `accordion${temporaryId}`);
        newItem.find('.panel-heading').attr({
            id: `heading${temporaryId}`
        });
        newItem.find('.panel-heading a').attr({
            href: `#collapse${temporaryId}`,
            "aria-controls": `#collapse${temporaryId}`
        });
        newItem.find('.panel-collapse').attr({
            "aria-labelledby": `heading${temporaryId}`,
            id: `collapse${temporaryId}`
        });
        newItem.find('button.delete-time').attr('id', `remove-hour-${temporaryId}`);
        hourList.append(newItem);
    }
}

function enableAddingNewHour() {
    let button = document.getElementById('add-new-hour');
    button.addEventListener('click', addNewHour, false);
}

function enableRemovingHour() {
    let buttons = document.getElementsByClassName('delete-time');
    Array.prototype.forEach.call(buttons, (button) => {
        let itemId = button.id.replace('remove-hour-', '');
        button.addEventListener('click', () => document.getElementById(`accordion-item-${itemId}`).remove(), false);
    });
}

window.addEventListener('load', start, false);
