function saveItem (me, url) {
    var role_name = getValue("role_name");
    var email = getValue("role_email");
    var data = {
        "role_name": role_name,
        "email": email
    };
    data = JSON.stringify(data);

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
    $.ajax({
        url: url,
        method: 'DELETE',
        data: {},
        success: function (result) {
            showSuccessMessage("Deleted successfully.", '.success-deletion', '.error-deletion', 500, function(){
                document.getElementById('deletingModal').style.display = "none";
                window.location.reload();
            });
        },
        error: function (jqXHR, exception) {
            var res = JSON.parse(jqXHR.responseText);
            showErrorMessage(res['message'], '.success-deletion', '.error-deletion');
        }
    });
}
