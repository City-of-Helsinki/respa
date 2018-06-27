import * as shortID from 'shortid';

// bind the event handler for closing notification to the elements (buttons)
// since we cant do it directly in the html because of the scope
export function enableNotificationHandler() {
    let notifications = document.getElementsByClassName('noti');
    Array.prototype.forEach.call(notifications, (noti) => {
        noti.getElementsByTagName('button')[0].addEventListener('click', () => noti.remove(), false);
    });
}

// event handler to add new hour accordion to the hours list
export function addNewHourHandler() {
    let hourList = $('.present-hours-list:first');
    let hourItem = hourList.find('.accordion-item:first');
    if (hourItem) {
        // clone an existing item in the DOM, a hack to reuse the template
        let newItem = hourItem.clone();
        const temporaryId = shortID.generate();

        // use the new id to re assign attributes of the cloned element
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

        // cloning doesn't include eventlistener binding so we do it manually here
        newItem.find('button.delete-time').click(() => removeHourHandler(temporaryId));
        hourList.append(newItem);
    }
}

// bind the event handler for adding new hour to the element (button)
export function enableAddingNewHour() {
    let button = document.getElementById('add-new-hour');
    button.addEventListener('click', addNewHourHandler, false);
}

// bind the event handler for removing an hour item to its delete button
export function enableRemovingHour() {
    let buttons = document.getElementsByClassName('delete-time');
    Array.prototype.forEach.call(buttons, (button) => {
        let itemId = button.id.replace('remove-hour-', '');
        button.addEventListener('click', () => removeHourHandler(itemId), false);
    });
}

// event handler to remove an hour accordion item
// take the Id of that arcordion-item as argument
export function removeHourHandler(id) {
    let hourItem = document.getElementById(`accordion-item-${id}`);
    hourItem.remove();
}
