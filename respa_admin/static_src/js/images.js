import { emptyImageItem } from './form';

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

    //Update all input ids as well.
    $inputs.each(function (j, input) {
      $(input).attr('id', $(input).attr('id').replace(/-(\d+)-/,'-' + i + '-'));
      $(input).attr('name', $(input).attr('name').replace(/-(\d+)-/,'-' + i + '-'));
    });
  });
}

function getImageCount() {
  return $('#images-list')[0].children.length;
}

/*
* Add new images to the image formset and update increment images total forms.
* */
export function addNewImage() {
  let $imagesList = $('#images-list');
  let newImage = emptyImageItem.clone();

  $imagesList.append(newImage);

  attachImageEventHandlers(newImage);
  updateImagesTotalForms();
  updateImagesIndices();
}

export function removeImage(imageItem) {
  imageItem.remove();

  updateImagesTotalForms();
  updateImagesIndices();
}

function attachImageEventHandlers(imageItem) {
  let removeButton = imageItem.find('#remove-image')[0];
  removeButton.addEventListener('click', () => removeImage(imageItem), false);
}
