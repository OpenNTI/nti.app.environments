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
    $.ajax({
        url: url,
        method: 'POST',
        data: data,
        success: function (result) {
            showSuccessMessage("Save successfully.", '.success-creation', '.error-creation', 500, function(){
                document.getElementById('newModal').style.display = "none";
                window.location.reload();
            });
        },
        error: function (jqXHR, exception) {
            var res = JSON.parse(jqXHR.responseText);
            showErrorMessage(res['message'], '.success-creation', '.error-creation');
        }
    });
}


function deleteItem (me) {
    var url = $(me).attr('delete_url');
    $.ajax({
        url: url,
        method: 'DELETE',
        data: {},
        success: function (result) {
            showSuccessMessage("Deleted successfully.", '.success-deletion', '.error-deletion', 500, function(){
                closeDeletingModal();
                window.location.reload();
            });
        },
        error: function (jqXHR, exception) {
            var res = JSON.parse(jqXHR.responseText);
            showErrorMessage(res['message'], '.success-deletion', '.error-deletion');
        }
    });
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