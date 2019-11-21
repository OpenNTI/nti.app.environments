function showSuccessMessage(message,timeout) {
    success = $('.success');
    error = $('.error');
    $(error).html('');
    $(error).hide();
    $(success).html(message);
    $(success).show();
    if (timeout) {
        setTimeout(function(){
        }, timeout);
    }
}

function showErrorMessage(message) {
    success = $('.success');
    error = $('.error');
    $(success).html('');
    $(success).hide();
    $(error).html(message);
    $(error).show();
}

function clearMessages() {
    success = $('.success');
    error = $('.error');
    $(success).html('');
    $(success).hide();
    $(error).html('');
    $(error).hide();
}