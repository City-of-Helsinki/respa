let emptyPermissionItem = null;

function enableRemovePermission() {
  $('#current-permissions-list').on('click', '.remove-permission', removePermission)
}

function enableAddNewPermission() {
  $('#add-new-permission').bind('click', addNewPermission);
}

function isStaffCheckboxListener() {
  let staff_input_elem = $("input#id_is_staff");
  $('.select-dropdown, .custom-checkbox').change(function() {
    if(!staff_input_elem.is(":checked")) {
      staff_input_elem.prop("checked", true);
    }
  });
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
  let permissionValue = $(this).closest('.permission-item').find('[type="hidden"]').first().val();
  if(permissionValue) {
    $(this).next('span.hidden-delete-checkbox').find('input').prop("checked", true);
    $(this).closest('.permission-item').hide();
  }
  else {
    $(this).closest('.permission-item').remove();
  }
  initializeUserForm();
}

function initializeUserForm() {
  updatePermissionsTotalForms();
  updatePermissionInputIds();
  updateAllPermissionMgmtFormIndices();
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
    let selects = $(permissionItem).find('select');
    let inputs = $(permissionItem).find('input');
    let labels = $(permissionItem).find('label');

    selects.each(function (selectIndex, select) {
      $(select).attr('id', $(select).attr('id').replace(/-(\d+)-/, "-" + i + "-"));
      $(select).attr('name', $(select).attr('name').replace(/-(\d+)-/, "-" + i + "-"));
    });

    inputs.each(function (inputIndex, input) {
      $(input).attr('id', $(input).attr('id').replace(/-(\d+)-/, "-" + i + "-"));
      $(input).attr('name', $(input).attr('name').replace(/-(\d+)-/, "-" + i + "-"));
    });

    labels.each(function (labelIndex, label) {
      $(label).attr('for', $(label).attr('for').replace(/-(\d+)-/, "-" + i + "-"));
    });
  });
}

function updatePermissionMgmtFormIndices(periodItem, index = null) {
  let $managementFormInputs = $(periodItem).find('#permission-management-form').find('input');

  if (index === null) {
    index = getPermissionsCount() - 1;
  }

  $managementFormInputs.each(function (id, input) {
    $(input).attr('id', $(input).attr('id').replace(/id_unit_authorizations-(\d+)-/, 'id_unit_authorizations-' + index + '-'));
    $(input).attr('name', $(input).attr('name').replace(/unit_authorizations-(\d+)-/, 'unit_authorizations-' + index + '-'));
  });
}

function updateAllPermissionMgmtFormIndices() {
  let periodList = $('#current-permissions-list').children();
  for (let i = 0; i < getPermissionsCount(); i++) {
    updatePermissionMgmtFormIndices(periodList[i], i);
  }
}

export function initializeUserFormEventHandlers() {
  enableRemovePermission();
  enableAddNewPermission();
  setEmptyPermissionItem();
  isStaffCheckboxListener();
}