function saveItem (me, url) {
    var role_name = getValue("role_name");
    var email = getValue("role_email");
    var data = {
        "role_name": role_name,
        "email": email
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
