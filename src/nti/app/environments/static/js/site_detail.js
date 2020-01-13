
function doUpdate(url, data, success, error, method) {
    method = method ? method : 'PUT';
    $.ajax({
        url: url,
        method: method,
        data: data,
        success: function (result) {
            showSuccessMessage("Save successfully.", success, error, 500, function(){
                window.location.reload();
            });
        },
        error: function (jqXHR, exception) {
            var res = JSON.parse(jqXHR.responseText);
            showErrorMessage(res['message'], success, error);
        }
    });
}

// environment.
function showEnvironmentEditView() {
    var view = $('#view_environment');
    view.css('display', 'none');

    var edit = $('#edit_environment');
    edit.css('display', 'block');

    var _type = $(view.find('.site_environment_type')[0]).text();

    $(edit.find('.site_environment_type')[0]).val(_type);

    if (_type==='shared') {
        $($(edit).find('.name_group_item')[0]).css('display', 'block');
        $($(edit).find('.pod_group_item')[0]).css('display', 'none');
        $($(edit).find('.host_group_item')[0]).css('display', 'none');

        var elem = $(edit).find('.site_environment_name')[0];
        $(elem).css('display', 'inline-block');
        $(elem).val($(view.find('.site_environment_name')[0]).text());

        var elem = $(edit).find('.site_environment_pod_id')[0];
        $(elem).css('display', 'none');
        $(elem).val('');

        var elem = $(edit).find('.site_environment_host')[0];
        $(elem).css('display', 'none');
        $(elem).val('');
    } else {
        $($(edit).find('.name_group_item')[0]).css('display', 'none');
        $($(edit).find('.pod_group_item')[0]).css('display', 'block');
        $($(edit).find('.host_group_item')[0]).css('display', 'block');

        var elem = $(edit).find('.site_environment_pod_id')[0];
        $(elem).css('display', 'inline-block');
        $(elem).val($(view.find('.site_environment_pod_id')[0]).text());

        var elem = $(edit).find('.site_environment_host')[0];
        $(elem).css('display', 'inline-block');
        $(elem).val($(view.find('.site_environment_host')[0]).text());

        var elem = $(edit).find('.site_environment_name')[0];
        $(elem).css('display', 'none');
        $(elem).val('');
    }
}

function cancelEnvironmentEditView() {
    $('#view_environment').css('display', 'block');
    $('#edit_environment').css('display', 'none');
    clearMessages('.success-edit-environment', '.error-edit-environment');
}

function onEnvironmentChange () {
    var edit = $('#edit_environment');
    var value = $(edit.find('.site_environment_type')[0]).val();
    if (value === "shared") {
        $($(edit).find('.name_group_item')[0]).css('display', 'block');
        $($(edit).find('.pod_group_item')[0]).css('display', 'none');
        $($(edit).find('.host_group_item')[0]).css('display', 'none');

        $(edit.find('.site_environment_name')[0]).css('display', 'inline-block');
        $(edit.find('.site_environment_pod_id')[0]).css('display', 'none');
        $(edit.find('.site_environment_host')[0]).css('display', 'none');
    } else if (value === "dedicated") {
        $($(edit).find('.name_group_item')[0]).css('display', 'none');
        $($(edit).find('.pod_group_item')[0]).css('display', 'block');
        $($(edit).find('.host_group_item')[0]).css('display', 'block');

        $(edit.find('.site_environment_pod_id')[0]).css('display', 'inline-block');
        $(edit.find('.site_environment_host')[0]).css('display', 'inline-block');
        $(edit.find('.site_environment_name')[0]).css('display', 'none');
    }
}

function saveEnvironmentView(me, url)  {
    var form = $(me).closest('.form-group')[0];
    var _type = $($(form).find('.site_environment_type')[0]).val();
    var data = {'MimeType': getEnvMimeType(_type)};
    if(!_type) {
        return;
    }
    if(_type==='shared') {
        data['name'] = $($(form).find('.site_environment_name')[0]).val().trim();
    } else {
        data['pod_id'] = $($(form).find('.site_environment_pod_id')[0]).val().trim();
        data['host'] = $($(form).find('.site_environment_host')[0]).val().trim();
    }

    data = JSON.stringify(data);
    doUpdate(url, data, '.success-edit-environment', '.error-edit-environment')
}


// license.
function showLicenseEditView() {
    var view = $('#view_license');
    view.css('display', 'none');

    var edit = $('#edit_license');
    edit.css('display', 'block');

    var _type = $(view.find('.site_license_type')[0]).text();
    var start_date = $(view.find('.site_license_start_date')[0]).text();
    var end_date = $(view.find('.site_license_end_date')[0]).text();

    $(edit.find('.site_license_type')[0]).val(_type);
    $(edit.find('.site_license_start_date')[0]).val(start_date);
    $(edit.find('.site_license_end_date')[0]).val(end_date);
}

function cancelLicenseEditView() {
    $('#view_license').css('display', 'block');
    $('#edit_license').css('display', 'none');
    clearMessages('.success-edit-license', '.error-edit-license');
}

function saveLicenseView(me, url) {
    var form = $(me).closest('.form-group')[0];
    var _type = $($(form).find('.site_license_type')[0]).val();
    var start_date = $($(form).find('.site_license_start_date')[0]).val();
    var end_date = $($(form).find('.site_license_end_date')[0]).val();
    if(!_type) {
        return;
    }
    var data = {
        'MimeType': getLicenseMimeType(_type),
        'start_date': start_date,
        'end_date': end_date
    };
    data = JSON.stringify(data);
    doUpdate(url, data, '.success-edit-license', '.error-edit-license')
}

// site info
function showSiteEditView() {
    var view = $('#view_site_info');
    view.css('display', 'none');

    var edit = $('#edit_site_info');
    edit.css('display', 'block');

    var status = $(view.find('.site_status')[0]).text();
    var dns_names = $(view.find('.site_dns_names')[0]).attr('site_dns_names');
    dns_names = dns_names ? dns_names : '';

    $(edit.find('.site_status')[0]).val(status);
    $(edit.find('.site_dns_names')[0]).val(dns_names);
}

function cancelSiteEditView() {
    $('#view_site_info').css('display', 'block');
    $('#edit_site_info').css('display', 'none');
    clearMessages('.success-edit-site-info', '.error-edit-site-info');
}

function saveSiteEditView(me, url) {
    var form = $(me).closest('.form-group')[0];
    var status = $($(form).find('.site_status')[0]).val();
    var dns_names = $($(form).find('.site_dns_names')[0]).val().trim();
    dns_names = dns_names ? $.map(dns_names.split(","), $.trim) : null;
    var data = {
        'status': status,
        'dns_names': dns_names
    };
    data = JSON.stringify(data);
    doUpdate(url, data, '.success-edit-site-info', '.error-edit-site-info')
}

// owner info
function showOwnerEditView() {
    var view = $('#view_owner_info');
    view.css('display', 'none');

    var edit = $('#edit_owner_info');
    edit.css('display', 'block');

    var email = $(view.find('.site_owner_email')[0]).text();
    $(edit.find('.site_owner_email')[0]).val(email);
}

function cancelOwnerEditView() {
    $('#view_owner_info').css('display', 'block');
    $('#edit_owner_info').css('display', 'none');
    clearMessages('.success-edit-owner-info', '.error-edit-owner-info');
}

function saveOwnerEditView(me, url) {
    var form = $(me).closest('.form-group')[0];
    var email = $($(form).find('.site_owner_email')[0]).val();
    var data = {
        'owner': email,
    };
    data = JSON.stringify(data);
    doUpdate(url, data, '.success-edit-owner-info', '.error-edit-owner-info')
}


// parent site info
function showParentSiteEditView() {
    var view = $('#view_parent_site');
    view.css('display', 'none');

    var edit = $('#edit_parent_site');
    edit.css('display', 'block');

    var term = $(view.find('.site_parent_id')[0]).text();
    $(edit.find('.site_parent_id')[0]).val(term);
}

function cancelParentSiteEditView() {
    $('#view_parent_site').css('display', 'block');
    $('#edit_parent_site').css('display', 'none');
    clearMessages('.success-edit-parent-site', '.error-edit-parent-site');
}

function saveParentSiteView(me, url) {
    var form = $(me).closest('.form-group')[0];
    var parent_site = $($(form).find('.site_parent_id')[0]).val();
    var data = {
        'parent_site': parent_site ? parent_site : null,
    };
    data = JSON.stringify(data);
    doUpdate(url, data, '.success-edit-parent-site', '.error-edit-parent-site')
}