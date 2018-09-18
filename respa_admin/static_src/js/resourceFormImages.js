import { getEmptyImage } from './resourceForm';
import { toggleCurrentLanguage } from './resourceFormLanguage';

export function updateImagesTotalForms() {
  $('#id_images-TOTAL_FORMS').val(getImageCount());
}

export function updateImagesIndices() {
  let $imagesList = $('#images-list').children();

  if (!$imagesList) {
    return;
  }

  //Update the image item ids.
  $imagesList.each(function (i, image) {
    $(image).attr('id', $(image).attr('id').replace(/-(\d+)/,'-' + i));

    let $inputs = $(image).find('input');
    let $buttons = $(image).find('button');
    let $dropDowns = $(image).find('select');

    //Update select drop down ids.
    $dropDowns.each(function (ddIndex, dropDown) {
      $(dropDown).attr('id', $(dropDown).attr('id').replace(/-(\d+)-/,'-' + i + '-'));
      $(dropDown).attr('name', $(dropDown).attr('name').replace(/-(\d+)-/,'-' + i + '-'));
    });

    //Update button ids.
    $buttons.each(function (buttonIndex, button) {
      $(button).attr('id', $(button).attr('id').replace(/(\d+)/, i));
    });

    //Update input ids (hidden included).
    $inputs.each(function (inputIndex, input) {
      $(input).attr('id', $(input).attr('id').replace(/-(\d+)-/,'-' + i + '-'));
      $(input).attr('name', $(input).attr('name').replace(/-(\d+)-/,'-' + i + '-'));
    });
  });
}

/*
* Add new images to the image formset and update increment images total forms.
* */
export function addNewImage() {
  let $imagesList = $('#images-list');
  let emptyImageItem = getEmptyImage();

  if (emptyImageItem) {
    let newImage = emptyImageItem.clone();

    $imagesList.append(newImage);

    attachImageEventHandlers(newImage);
    toggleCurrentLanguage(document.documentElement.lang, newImage);
    updateImagesTotalForms();
    updateImagesIndices();
  }
}

export function removeImage(imageItem) {
  imageItem.remove();

  updateImagesTotalForms();
  updateImagesIndices();
}

function getImageCount() {
  return $('#images-list')[0].children.length;
}

function attachImageEventHandlers(imageItem) {
  let imageIdNum = imageItem[0].id.match(/(\d+)/)[0];

  //Add remove image event.
  let removeButton = imageItem.find('#remove-image-' + imageIdNum)[0];
  removeButton.addEventListener('click', () => removeImage(imageItem), false);
}
