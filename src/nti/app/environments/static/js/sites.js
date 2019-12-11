"use strict";

function getValue(id) {
    var val = document.getElementById(id).value.trim();
    return val ? val : null;
}

function saveItem (me, url) {
    var owner = getValue("site_owner");
    var owner_username = getValue("site_owner_username");
    var environment = {
            "type": getValue("site_environment_type"),
            "name": getValue("site_environment_name"),
            "containerId": getValue("site_environment_containerid")
        };
    var license = getValue("site_license");
    var status = getValue("site_status");
    var created = getValue("site_created");
    var dns_names = getValue("site_dns_names");
    dns_names = dns_names ? dns_names.split('\n') : null;

    var data = {
        "owner": owner,
        "owner_username": owner_username,
        "environment": environment,
        "license": license,
        "dns_names": dns_names,
        "status": status,
        "created": created
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


function onEnvironmentChange () {
    var value = document.getElementById("site_environment_type").value;
    if (value === "shared") {
        document.getElementById("site_environment_details").style.display = "flex";
        document.getElementById("site_environment_name").style.display = "inline-block";
        document.getElementById("site_environment_containerid").style.display = "none";
    } else if (value === "dedicated") {
        document.getElementById("site_environment_details").style.display = "flex;";
        document.getElementById("site_environment_name").style.display = "none";
        document.getElementById("site_environment_containerid").style.display = "inline-block";
    } else {
        document.getElementById("site_environment_details").style.display = "none";
    }
}


function openDeletingModal(url, email) {
    var modal = document.getElementById("deletingModal");
    modal.style.display = "block";
    modal.getElementsByClassName('btnOK')[0].setAttribute('delete_url', url);
    modal.getElementsByClassName('deleting_email')[0].innerHTML = email;
}
