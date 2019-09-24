let emptyPermissionItem = null;

function enableRemovePermission() {
  $('.remove-permission').bind('click', removePermission);
}

function enableAddNewPermission() {
  $('#add-new-permission').bind('click', addNewPermission);
}

function setEmptyPermissionItem() {
  let $permissionList = $('#current-permissions-list')[0].children;
  let $lastPermissionItem = $($permissionList[$permissionList.length - 1])
  emptyPermissionItem = $($lastPermissionItem).clone()
}

function addNewPermission() {
  let $permissionList = $('#current-permissions-list')

  if (emptyPermissionItem) {
    let newItem = emptyPermissionItem.clone();
    $permissionList.append(newItem);
  }
  initializeUserForm();
}

function removePermission() {
  $(this).next('span.hidden-delete-checkbox').find('input').prop("checked", true);
  $(this).closest('.permission-item').hide()
}

function initializeUserForm() {
  updatePermissionsTotalForms();
  enableRemovePermission();
  updatePermissionInputIds();
  updateAllDaysMgmtFormIndices();
}

function getPermissionsCount() {
  return $('#current-permissions-list')[0].children.length;
}

function updatePermissionsTotalForms() {
  document.getElementById('id_unit_authorizations-TOTAL_FORMS').value = getPermissionsCount();
}

function updatePermissionInputIds() {
  let permissions = $('#current-permissions-list').children();

  permissions.each(function (i, permissionItem) {
    let inputs = $(permissionItem).find('select');

    inputs.each(function (inputIndex, input) {
      $(input).attr('id', $(input).attr('id').replace(/-(\d+)-/, "-" + i + "-"));
      $(input).attr('name', $(input).attr('name').replace(/-(\d+)-/, "-" + i + "-"));
    });
  });
}

function updatePeriodDaysMgmtFormIndices(periodItem, index = null) {
  let $managementFormInputs = $(periodItem).find('#permission-management-form').find('input');

  if (index === null) {
    index = getPermissionsCount() - 1;
  }

  $managementFormInputs.each(function (id, input) {
    $(input).attr('id', $(input).attr('id').replace(/id_unit_authorizations-(\d+)-/, 'id_days-periods-' + index + '-'));
    $(input).attr('name', $(input).attr('name').replace(/unit_authorizations-(\d+)-/, 'days-periods-' + index + '-'));
  });
}

function updateAllDaysMgmtFormIndices() {
  let periodList = $('#current-permissions-list').children();
  for (let i = 0; i < getPermissionsCount(); i++) {
    updatePeriodDaysMgmtFormIndices(periodList[i], i);
  }
}

export function initializeUserFormEventHandlers() {
  enableRemovePermission();
  enableAddNewPermission();
  setEmptyPermissionItem();
}