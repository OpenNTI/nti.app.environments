"use strict";

function getValue(id) {
    var val = document.getElementById(id).value.trim();
    return val ? val : null;
}

function requestTrialSite (me, url) {
    var client_name = getValue("site_trial_client"),
              owner = getValue("site_trial_email"),
          dns_names = getValue('site_trial_url');
          dns_names = dns_names ? $.map(dns_names.split(","), $.trim) : null;

    var data = {
        "client_name": client_name,
        "owner": owner,
        "dns_names": dns_names,
    };
    data = JSON.stringify(data);

    doAjaxRequest(me, url, data, 'POST', '.success-request-trial-site', '.error-request-trial-site', null, function(result){
        if (result['redirect_url']) {
            window.location.href = result['redirect_url'];
        } else {
            showSuccessMessage("Save successfully.", '.success-request-trial-site', '.error-request-trial-site', 500, function(){
                window.location.reload();
            });
        }
    });
}


function formatInput(input, newValue, updatedLength) {
    var val = input.val();
    if (val === "") {
        return;
    }
    var caret_pos = input.prop("selectionStart");
    caret_pos = caret_pos + updatedLength;
    input.val(newValue);
    input[0].setSelectionRange(caret_pos, caret_pos);
}


/** make site url input always ends with a specific domain. */
function handle_domain_input(me){
    var current = $(me).val();
    var base_domain = $(me).attr('suggested_domain');
    if (!current){
        $(me).attr('old', '');
        return
    }

    if (current.endsWith(base_domain)) {
        var original_length = current.length,
            prefix = current.slice(0, current.length - base_domain.length - 1);

        prefix = prefix.replace(/\./g,'').replace(/\s/g,'');
        current = prefix.concat('.').concat(base_domain);

        formatInput($(me), current, current.length - original_length);
    } else {
        var old = $(me).attr('old') ? $(me).attr('old') : '';
        if (old.endsWith(base_domain)) {
            var updatedLength = old.length - current.length;
            current = old;
            formatInput($(me), current, updatedLength);
        } else{
            var original_length = current.length;
            current = current.replace(/\./g,'').replace(/\s/g,'');
            var updatedLength = current.length - original_length;
            current = current.concat('.').concat(base_domain);
            formatInput($(me), current, updatedLength);
        }
    }
    $(me).attr('old', current);
}