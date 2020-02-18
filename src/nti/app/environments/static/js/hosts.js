function saveItem (me, url) {
    var host_name = getValue("host_name"),
        capacity = getValue("host_capacity");
    var data = {
        "host_name": host_name,
        "capacity": capacity,
        "MimeType": "application/vnd.nextthought.app.environments.host"
    };
    data = JSON.stringify(data);
    doCreationRequest(me, url, data, '#newModal');
}


function openNewModal() {
    clearMessages('.success-creation', '.error-creation');
    document.getElementById('newModal').style.display = 'block';
}


function openDeletingModal(url, email) {
    clearMessages('.success-deletion', '.error-deletion');
    var modal = document.getElementById("deletingModal");
    modal.style.display = "block";
    modal.getElementsByClassName('btnOK')[0].setAttribute('delete_url', url);
    modal.getElementsByClassName('deleting_email')[0].innerHTML = email;
}

function deleteItem (me) {
    var url = $(me).attr('delete_url');
    doDeletionRequest(me, url, {}, '#deletingModal');
}


function openEditingModal(me, url) {
    clearMessages('.success-update', '.error-update');
    var modal = document.getElementById("editingModal");
    modal.style.display = "block";
    modal.getElementsByClassName('btnSave')[0].setAttribute('edit_url', url);

    var tr = $(me).closest('tr')[0],
        name_elem = $('#host_name_edit'),
        capacity_elem = $('#host_capacity_edit');

    name_elem.val($($(tr).find("td.host")[0]).text());
    name_elem.attr('original_value', name_elem.val());

    capacity_elem.val($($(tr).find("td.capacity")[0]).text());
    capacity_elem.attr('original_value', capacity_elem.val());
}

function _is_field_changed(field_selector) {
    var elem = $(field_selector);
    var original = $(elem).attr('original_value');
        incoming = $(elem).val().trim();

    original = original ? original : null;
    incoming = incoming ? incoming : null;
    return (original === incoming) ? null : incoming
}

function editItem(me) {
    var url = $(me).attr('edit_url'),
        data = {},
        updated = false,
        fields = [['host_name', '#host_name_edit'],
                  ['capacity', '#host_capacity_edit']];

    fields.forEach(function(field){
        var tmp = _is_field_changed(field[1]);
        if(tmp) {
            data[field[0]] = tmp;
            if(!updated){
                updated = true
            }
        }
    });
    if (!updated) {
        showSuccessMessage('No changes.', '.success-update', '.error-update', 1000);
        return
    }
    data = JSON.stringify(data);
    doUpdateRequest(me, url, data, '#editingModal');
}