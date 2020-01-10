"use strict";

function getValue(id) {
    var val = document.getElementById(id).value.trim();
    return val ? val : null;
}

function saveItem (me, url) {
    var email = getValue("hubspot_email");
    var data = {
        "email": email
    };
    doCreationRequest(me, url, data, '#newModal');
}


function deleteItem (me) {
    var url = $(me).attr('delete_url');
    doDeletionRequest(me, url, {}, '#deletingModal');
}

function openDeletingModal(url, email) {
    var modal = document.getElementById("deletingModal");
    modal.style.display = "block";
    modal.getElementsByClassName('btnOK')[0].setAttribute('delete_url', url);
    modal.getElementsByClassName('deleting_email')[0].innerHTML = email;
}

function closeDeletingModal() {
    var modal = document.getElementById("deletingModal");
    modal.style.display = "none";
}

function openNewModal() {
    clearMessages('.success-creation', '.error-creation');
    document.getElementById('hubspot_email').value = '';
    document.getElementById('newModal').style.display = 'block';
}