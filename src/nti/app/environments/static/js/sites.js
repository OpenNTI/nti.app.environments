"use strict";


function saveItem (me, url) {
    var site_id = getValue("site_id");
    var owner = getValue("site_owner");
    var env_mimetype = getEnvMimeType(getValue("site_environment_type"));
    var environment = env_mimetype ? {
            "MimeType": env_mimetype,
            "name": getValue("site_environment_name"),
            "pod_id": getValue("site_environment_pod_id"),
            "host": getValue("site_environment_host")
        } : null;

    var lic_mimetype = getLicenseMimeType(getValue("site_license"));
    var license = lic_mimetype? {
        "MimeType": lic_mimetype,
        "start_date": getValue("site_license_start_date"),
        "end_date": getValue("site_license_end_date")
    } : null;
    var status = getValue("site_status");
    var created = getValue("site_created");
    var dns_names = getValue("site_dns_names");
    dns_names = dns_names ? dns_names.split(',') : null;

    var data = {
        "id": site_id,
        "owner": owner,
        "environment": environment,
        "license": license,
        "dns_names": dns_names,
        "status": status,
        "created": created,
        "MimeType": "application/vnd.nextthought.app.environments.site"
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
        document.getElementById("site_environment_pod_id").style.display = "none";
        document.getElementById("site_environment_host").style.display = "none";
    } else if (value === "dedicated") {
        document.getElementById("site_environment_details").style.display = "flex";
        document.getElementById("site_environment_pod_id").style.display = "inline-block";
        document.getElementById("site_environment_host").style.display = "inline-block";
        document.getElementById("site_environment_name").style.display = "none";
    } else {
        document.getElementById("site_environment_details").style.display = "none";
    }
}


function onLicenseChange() {
    var value = document.getElementById("site_license").value;
    if (value === "trial" || value === "enterprise") {
        document.getElementById("site_license_details").style.display = "flex";
    } else {
        document.getElementById("site_license_details").style.display = "none";
    }
}


function openDeletingModal(url, email) {
    var modal = document.getElementById("deletingModal");
    modal.style.display = "block";
    modal.getElementsByClassName('btnOK')[0].setAttribute('delete_url', url);
    modal.getElementsByClassName('deleting_email')[0].innerHTML = email;
}

function openNewModal() {
    clearMessages('.success-creation', '.error-creation');
    document.getElementById('hubspot_email').value = '';
    document.getElementById('newModal').style.display = 'none';
}


function uploadFile(me, url) {
    var data = new FormData();
    var files = $('#sites_upload')[0].files;
    if (files.length == 0 || files[0].type !== 'text/csv'){
        return;
    }
    data.append('sites', files[0], files[0].name);
    $.ajax({
        url: url,
        type: 'post',
        data: data,
        dataType: 'json',
        cache: false,
        contentType: false,
        processData: false,
        success: function (result) {
            showSuccessMessage("Upload successfully.", '.success-upload', '.error-upload', 500, function(){
                document.getElementById('uploadModal').style.display = "none";
                window.location.reload();
            });
        },
        error: function (jqXHR, exception) {
            var res = JSON.parse(jqXHR.responseText);
            showErrorMessage(res['message'], '.success-upload', '.error-upload');
        }
    });
}
