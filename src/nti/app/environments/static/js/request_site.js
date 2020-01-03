"use strict";

function getValue(id) {
    var val = document.getElementById(id).value.trim();
    return val ? val : null;
}

function requestTrialSite (me, url) {
    var client_name = getValue("site_trial_client"),
              owner = getValue("site_trial_email"),
          dns_names = getValue('site_trial_url');

    var data = {
        "client_name": client_name,
        "owner": owner,
        "dns_names": dns_names? [dns_names]: null,
    };
    data = JSON.stringify(data);

    $.ajax({
        url: url,
        method: 'POST',
        data: data,
        success: function (result) {
            if (result['redirect_url']) {
                window.location.href = result['redirect_url'];
            } else {
                showSuccessMessage("Save successfully.", '.success-request-trial-site', '.error-request-trial-site', 500, function(){
                    window.location.reload();
                });
            }
        },
        error: function (jqXHR, exception) {
            var res = JSON.parse(jqXHR.responseText);
            showErrorMessage(res['message'], '.success-request-trial-site', '.error-request-trial-site');
        }
    });
}
