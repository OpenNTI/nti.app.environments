function showSuccessMessage(success, successSelector, errorSelector, timeout, postHandler) {
    successSelector = successSelector ? successSelector : '.success';
    errorSelector = errorSelector ? errorSelector : '.error';
    $(errorSelector).html('');
    $(errorSelector).hide();
    $(successSelector).html(success);
    $(successSelector).show();
    if (timeout) {
        setTimeout(function(){
            clearMessages(successSelector, errorSelector);
            if (postHandler){
                postHandler();
            }
        }, timeout);
    }
}

function showErrorMessage(error, successSelector, errorSelector) {
    successSelector = successSelector ? successSelector : '.success';
    errorSelector = errorSelector ? errorSelector : '.error';
    $(successSelector).html('');
    $(successSelector).hide();
    $(errorSelector).html(error);
    $(errorSelector).show();
}

function clearMessages(successSelector, errorSelector) {
    successSelector = successSelector ? successSelector : '.success';
    errorSelector = errorSelector ? errorSelector : '.error';
    successSelector = $('.success');
    errorSelector = $('.error');
    $(successSelector).html('');
    $(successSelector).hide();
    $(errorSelector).html('');
    $(errorSelector).hide();
}


function getUrlParameter(name) {
    var url = window.location.search.substring(1),
        vars = url.split('&'),
        qname,
        i;
    for (i = 0; i < vars.length; i++) {
        qname = vars[i].split('=');
        if (qname[0] === name) {
            return qname[1] === undefined ? '' : decodeURIComponent(qname[1]);
        }
    }
};


function updateUrlParameter(name, value, url) {
    var prefix = window.location.href.split('?')[0],
        vars = window.location.search.substring(1).split('&'),
        i = 0;
        existing = false;
    prefix += '?';
    for (i = 0; i < vars.length; i++) {
        qname = vars[i].split('=');
        if (qname[0] === name) {
            qname[1] = encodeURIComponent(value);
            existing = true;
        }
        if (i > 0) {
            prefix = prefix.concat('&');
        }
        prefix = prefix.concat(qname[0] + '=' + qname[1]);
    }
    if (!existing) {
        if (i > 0){
            prefix = prefix.concat('&');
        }
        prefix = prefix.concat(name + '=' + value);
    }
    return prefix;
}
