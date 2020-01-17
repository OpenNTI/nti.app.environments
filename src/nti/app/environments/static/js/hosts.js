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

    var tr = $(me).closest('tr')[0];
    document.getElementById('host_name_edit').value = $($(tr).find("td.host")[0]).text();
    document.getElementById('host_capacity_edit').value = $($(tr).find("td.capacity")[0]).text();
}

function editItem(me) {
    var url = $(me).attr('edit_url');
    var host_name = getValue("host_name_edit"),
        capacity = getValue("host_capacity_edit");
    var data = {
        "host_name": host_name,
        "capacity": capacity
    };
    data = JSON.stringify(data);
    doUpdateRequest(me, url, data, '#editingModal');
}