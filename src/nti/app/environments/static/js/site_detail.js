
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
function getSharedSelectors() {
    return [['.name_group_item', '.site_environment_name']];
}

function getDedicatedSelectors() {
    return [['.pod_group_item', '.site_environment_pod_id'],
            ['.load_group_item', '.site_environment_load_factor'],
            ['.host_group_item', '.site_environment_host']];
}

function showEnvironmentEditView() {
    var view = $('#view_environment');
    view.css('display', 'none');

    var edit = $('#edit_environment');
    edit.css('display', 'block');

    var _type = $(view.find('.site_environment_type')).text(),
        shared = getSharedSelectors(),
        dedicated = getDedicatedSelectors();

    $(edit.find('.site_environment_type')).val(_type);

    if (_type==='shared') {
        shared.forEach(function(selector){
            $(edit.find(selector[0])).css('display', 'block');
            var original = $(view.find(selector[1])).attr('original_value');
            var elem = $(edit).find(selector[1]);
            $(elem).css('display', 'inline-block');
            $(elem).val( original ? original : '' );
        });
        dedicated.forEach(function(selector){
            $(edit.find(selector[0])).css('display', 'none');
            var elem = $(edit).find(selector[1]);
            $(elem).css('display', 'none');
            $(elem).val('');
        });
    } else {
        shared.forEach(function(selector){
            $(edit.find(selector[0])).css('display', 'none');
            var elem = $(edit).find(selector[1]);
            $(elem).css('display', 'none');
            $(elem).val('');
        });
        dedicated.forEach(function(selector){
            $(edit.find(selector[0])).css('display', 'block');
            var original = $(view.find(selector[1])).attr('original_value');
            var elem = $(edit).find(selector[1]);
            $(elem).css('display', 'inline-block');
            $(elem).val( original ? original : '' );
        });
    }
}

function cancelEnvironmentEditView() {
    $('#view_environment').css('display', 'block');
    $('#edit_environment').css('display', 'none');
    clearMessages('.success-edit-environment', '.error-edit-environment');
}

function onEnvironmentChange () {
    var edit = $('#edit_environment');
    var _type = $(edit.find('.site_environment_type')).val(),
        shared = getSharedSelectors(),
        dedicated = getDedicatedSelectors();

    if (_type === "shared") {
        shared.forEach(function(selector){
            $(edit.find(selector[0])).css('display', 'block');
            $(edit.find(selector[1])).css('display', 'inline-block');
        });
        dedicated.forEach(function(selector){
            $(edit.find(selector[0])).css('display', 'none');
            $(edit.find(selector[1])).css('display', 'none');
        });
    } else if (_type === "dedicated") {
        shared.forEach(function(selector){
            $(edit.find(selector[0])).css('display', 'none');
            $(edit.find(selector[1])).css('display', 'none');
        });
        dedicated.forEach(function(selector){
            $(edit.find(selector[0])).css('display', 'block');
            $(edit.find(selector[1])).css('display', 'inline-block');
        });
    }
}

function getEnvDataByView(view_selector, original) {
    var view = $(view_selector);
    var _type = original ? $(view.find('.site_environment_type')).attr('original_value'): $(view.find('.site_environment_type')).val();
    if(!_type) {
        return null
    }

    var data = {'MimeType': getEnvMimeType(_type)};
    if(_type === 'shared') {
        var tmp = original ? $(view.find('.site_environment_name')).attr('original_value') : $(view.find('.site_environment_name')).val().trim();
        data['name'] = tmp ? tmp : null;
    } else {
        var names = ['pod_id', 'load_factor', 'host'];
        var klasses = ['.site_environment_pod_id', '.site_environment_load_factor', '.site_environment_host'];
        names.forEach(function(field, index){
            var tmp = original ? $(view.find(klasses[index])).attr('original_value'): $(view.find(klasses[index])).val().trim();
            data[field] = tmp ? tmp : null;
        });
    }
    return JSON.stringify(data)
}

function saveEnvironmentView(me, url)  {
    var original = getEnvDataByView('#view_environment', true);
    var incoming = getEnvDataByView('#edit_environment', false);
    if (incoming === null) {
        return
    }

    var data = (incoming === original ? null : incoming);
    if (!data) {
        showSuccessMessage('No changes.', '.success-edit-environment', '.error-edit-environment', 1000);
        return
    }
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

function getLicenseDataByView(view_selector, target_method) {
    var view = $(view_selector);
    var _type = $(view.find('.site_license_type'))[target_method]();
    if(!_type) {
        return null
    }

    var data = {'MimeType': getLicenseMimeType(_type)},
        names = ['start_date', 'end_date'],
        klasses = ['.site_license_start_date', '.site_license_end_date'];

    names.forEach(function(field, index){
        var tmp = $(view.find(klasses[index]))[target_method]().trim();
        data[field] = tmp ? tmp : null;
    });
    return JSON.stringify(data)
}

function saveLicenseView(me, url) {
    var original = getLicenseDataByView('#view_license', 'text');
    var incoming = getLicenseDataByView('#edit_license', 'val');
    if (incoming === null) {
        return
    }

    var data = (incoming === original ? null : incoming);
    if (!data) {
        showSuccessMessage('No changes.', '.success-edit-license', '.error-edit-license', 1000);
        return
    }
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

function getSiteEditData() {
    var view = $('#view_site_info');
    var status = $(view.find('.site_status')).text();
    var dns_names = $(view.find('.site_dns_names')).attr('site_dns_names');
    dns_names = dns_names ? dns_names : '';

    var edit = $('#edit_site_info');
    var new_status = $(edit.find('.site_status')).val();
    var new_dns_names = $(edit.find('.site_dns_names')).val().trim();

    var data = {},
        updated = false;
    if(status !== new_status) {
        data['status'] = new_status;
        updated = true;
    }
    if(dns_names !== new_dns_names) {
        new_dns_names = new_dns_names ? $.map(new_dns_names.split(","), $.trim) : null;
        data['dns_names'] = new_dns_names;
        updated = true;
    }
    return updated ? data : null
}

function saveSiteEditView(me, url) {
    var data = getSiteEditData();
    if (!data) {
        showSuccessMessage('No changes.', '.success-edit-site-info', '.error-edit-site-info', 1000);
        return
    }
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

function getOwnerData() {
    var view = $('#view_owner_info');
    var email = $(view.find('.site_owner_email')).text().trim();

    var edit = $('#edit_owner_info');
    var new_email = $(edit.find('.site_owner_email')).val().trim();
    return email === new_email ? null : {'owner': new_email ? new_email : null}
}

function saveOwnerEditView(me, url) {
    var data = getOwnerData();
    if (!data) {
        showSuccessMessage('No changes.', '.success-edit-owner-info', '.error-edit-owner-info', 1000);
        return
    }
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

function getParentSiteData() {
    var view = $('#view_parent_site');
    var parent = $(view.find('.site_parent_id')).text().trim();

    var edit = $('#edit_parent_site');
    var new_parent = $(edit.find('.site_parent_id')).val().trim();
    return parent === new_parent ? null : {'parent_site': new_parent ? new_parent : null}
}

function saveParentSiteView(me, url) {
    var data = getParentSiteData();
    if (!data) {
        showSuccessMessage('No changes.', '.success-edit-parent-site', '.error-edit-parent-site', 1000);
        return
    }
    data = JSON.stringify(data);
    doUpdate(url, data, '.success-edit-parent-site', '.error-edit-parent-site')
}


function deleteItem (me, url, sites_list_link) {
    doDeletionRequest(me, url, {}, '#deletingModal', function(result){
        showSuccessMessage("Successfully.", '.success-deletion', '.error-deletion', 500, function () {
            $('#deletingModal').hide()
            window.location.href = sites_list_link;
        });
    });
}


/** token */


function getTimeout(id, errorSelector) {
    var input = $('#timeout');
    clearFieldError(input);
    var val = $(input).val().trim();
    val = val ? val : null;
    if(!val){
        showFieldError(input);
    } else {
        val = Number(val);
        if(val < 1 || val > 360) {
            val = null;
            showFieldError(input, "Time limit should be between 1 and 360 mins.");
        } else {
            val = val * 60;
        }
    }
    return val
}


function openSiteTokenModal() {
    document.getElementById('tokenModal').style.display = 'block';
    $('#token-result-wrapper').hide();
}

function closeSiteTokenModal() {
    document.getElementById('tokenModal').style.display = 'none';
}

function generateToken(me, url) {
    clearMessages('.success-token', '.error-token');
    var timeout = getTimeout();
    if(!timeout){
        return;
    }

    var data = timeout ? {'timeout': timeout} : {};
    doAjaxRequest(me, url, data, 'GET', '.success-token', '.error-token', null, function(result){
        $('#token-result-wrapper').show();
        $('#highlight').text(result['jwt']);
        hideTooltip();
    });
}

function copyToken(me) {
    copyToClipBoard('highlight');
    showTooltip();
}

function showTooltip() {
    var tooltip = $('#token-result-wrapper .tooltiptext');
    $(tooltip).css('visibility', 'visible');
    $(tooltip).css('opacity', 1);
}

function hideTooltip() {
    var tooltip = $('#token-result-wrapper .tooltiptext');
    $(tooltip).css('visibility', 'hidden');
    $(tooltip).css('opacity', 0);
}
