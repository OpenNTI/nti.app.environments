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
