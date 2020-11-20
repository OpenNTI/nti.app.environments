"use strict";


function saveItem (me, url) {
    var site_id = getValue("site_id");
    var owner = getValue("site_owner");
    var env_mimetype = getEnvMimeType(getValue("site_environment_type"));
    var environment = env_mimetype ? {
            "MimeType": env_mimetype,
            "name": getValue("site_environment_name"),
            "pod_id": getValue("site_environment_pod_id"),
            "host": getValue("site_environment_host"),
            "load_factor": getValue("site_environment_load_factor")
        } : null;

    var lic_mimetype = getLicenseMimeType(getValue("site_license"));
    var license = lic_mimetype? {
        "MimeType": lic_mimetype,
        "start_date": getValue("site_license_start_date"),
        "end_date": getValue("site_license_end_date"),
        "frequency": getValue("site_license_frequency"),
        "seats": getValue("site_license_seats"),
	"additional_instructor_seats": getValue("site_license_additional_instructor_seats")
    } : null;
    var status = getValue("site_status");
    var dns_names = getValue("site_dns_names");
    dns_names = dns_names ? $.map(dns_names.split(","), $.trim) : null;

    var data = {
        "id": site_id,
        "owner": owner,
        "environment": environment,
        "license": license,
        "dns_names": dns_names,
        "status": status,
        "MimeType": "application/vnd.nextthought.app.environments.site"
    };
    data = JSON.stringify(data);
    doCreationRequest(me, url, data, '#newModal');
}


function onEnvironmentChange () {
    var value = document.getElementById("site_environment_type").value;
    if (value === "shared") {
        document.getElementById("site_environment_details").style.display = "flex";
        document.getElementById("site_environment_name").style.display = "inline-block";
        document.getElementById("site_environment_pod_id").style.display = "none";
        document.getElementById("site_environment_host").style.display = "none";
        document.getElementById("site_environment_load_factor").style.display = "none";
    } else if (value === "dedicated") {
        document.getElementById("site_environment_details").style.display = "flex";
        document.getElementById("site_environment_pod_id").style.display = "inline-block";
        document.getElementById("site_environment_host").style.display = "inline-block";
        document.getElementById("site_environment_load_factor").style.display = "inline-block";
        document.getElementById("site_environment_name").style.display = "none";
    } else {
        document.getElementById("site_environment_details").style.display = "none";
    }
}


function onLicenseChange() {
    var value = document.getElementById("site_license").value;
    if (value === "trial" || value === "enterprise") {
        document.getElementById("site_license_details").style.display = "flex";
        document.getElementById("site_license_details").style.display = "flex";
        document.getElementById("site_license_start_date").style.display = "inline-block";
        document.getElementById("site_license_end_date").style.display = "inline-block";
        document.getElementById("site_license_frequency").style.display = "none";
        document.getElementById("site_license_seats").style.display = "none";
	document.getElementById("site_license_additional_instructor_seats").style.display = "none";
    } else if (value === "starter" || value === "growth") {
        document.getElementById("site_license_details").style.display = "flex";
        document.getElementById("site_license_start_date").style.display = "inline-block";
        document.getElementById("site_license_end_date").style.display = "none";
        document.getElementById("site_license_frequency").style.display = "inline-block";
        document.getElementById("site_license_seats").style.display = "inline-block";
	document.getElementById("site_license_additional_instructor_seats").style.display = "inline-block";
    } else {
        document.getElementById("site_license_details").style.display = "none";
    }
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

    doUploadFile(me, url, data, '.success-upload', '.error-upload', '#uploadModal')
}
