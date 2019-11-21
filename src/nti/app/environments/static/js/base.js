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

function clearMessages() {
    success = $('.success');
    error = $('.error');
    $(success).html('');
    $(success).hide();
    $(error).html('');
    $(error).hide();
}