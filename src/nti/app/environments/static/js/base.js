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

function showFieldError(input, message) {
    var error = $(input).siblings('.field-error');
    if (error) {
        $(error).text(message || 'Please fill in this field.');
        $(error).show();
        return true
    }
}

function clearFieldError(input) {
    var error = $(input).siblings('.field-error');
    if (error) {
        $(error).hide();
    }
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
}


function updateUrlParameter(name, value, url) {
    var prefix = window.location.href.split('?')[0],
        vars = window.location.search.substring(1).split('&'),
        i = 0;
        existing = false;
    prefix += '?';
    if (vars.length > 1 || (vars.length == 1 && vars[0] !== '')) {
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
    }
    if (!existing) {
        if (i > 0){
            prefix = prefix.concat('&');
        }
        prefix = prefix.concat(name + '=' + encodeURIComponent(value));
    }
    return prefix;
}


function formatInput(input, newValue) {
    var val = input.val();
    if (val === "") {
        return;
    }
    var originalLength = val.length;
    var caret_pos = input.prop("selectionStart");

    input.val(newValue);
    var updatedLength = newValue.length;
    caret_pos = updatedLength - originalLength + caret_pos;
    input[0].setSelectionRange(caret_pos, caret_pos);
}


function positiveNumbersOnly (e) {
    var me = e.target;
    var newValue = me.value.replace(/\D/g,'');
    newValue = newValue.replace(/^0+/, "");
    formatInput($(me), newValue);
}

function positiveFloatOnly(e) {
    var me = e.target;
    var newValue = me.value.replace(/[^0-9.]/g, '');
    newValue = newValue.replace(/(\..*)\./g, '$1');
    formatInput($(me), newValue);
}


function getValue(id) {
    var val = document.getElementById(id).value.trim();
    return val ? val : null;
}

/** copy div content to clipboard. */
function copyToClipBoard(divSelector) {
    var elm = document.getElementById(divSelector);
    if(window.getSelection) {
        var selection = window.getSelection();
        var range = document.createRange();
        range.selectNodeContents(elm);
        selection.removeAllRanges();
        selection.addRange(range);
        document.execCommand("Copy");
    }
}


function getEnvMimeType(_type) {
    if (_type==="shared") {
        return "application/vnd.nextthought.app.environments.sharedenvironment";
    } else if (_type === "dedicated") {
        return "application/vnd.nextthought.app.environments.dedicatedenvironment";
    }
    return null
}


function getLicenseMimeType(_type) {
    if (_type==="trial") {
        return "application/vnd.nextthought.app.environments.triallicense";
    } else if (_type === "enterprise") {
        return "application/vnd.nextthought.app.environments.enterpriselicense";
    }
    return null
}


function preErrorHandle(xhr, exception) {
    var error = false;
    if(xhr.status === 403) {
        var content = $($.parseHTML(xhr.responseText.trim())).filter('main');
        $('body').html($(content));
        error = true;
    } else if (xhr.status === 401) {
        window.location.href = '/login';
        error = true;
    }
    return error;
}


/**
 *  Call this handler within the error method of ajax request.
 * @param {*} xhr
 * @param {*} exception
 */
function ajaxErrorHandler(xhr, exception, errorHandle, modal) {
    if(xhr.status !== 403 && xhr.status !== 401) {
        errorHandle();
    } else {
        if(modal) {
            $(modal).hide();
        }
        preErrorHandle(xhr, exception);
    }
}


/** do ajax request */
function doAjaxRequest(me, url, data, method, success, error, modal, postHandler, postErrorHandler) {
    // show spinner
    $($(me).find('.nonSpinnerText')[0]).hide();
    $($(me).find('.spinnerText')[0]).show();

    $.ajax({
        url: url,
        method: method,
        data: data,
        success: function (result) {
            if(postHandler) {
                postHandler(result);
            } else {
                showSuccessMessage("Successfully.", success, error, 500, function () {
                    if(modal) {
                        $(modal).hide()
                    }
                    window.location.reload();
                });
            }
        },
        error: function (jqXHR, exception) {
            // hide spinner
            $($(me).find('.spinnerText')[0]).hide();
            $($(me).find('.nonSpinnerText')[0]).show();

            ajaxErrorHandler(jqXHR, exception, function() {
                if (postErrorHandler) {
                    postErrorHandler(me, jqXHR, exception);
                } else {
                    var res = JSON.parse(jqXHR.responseText);
                    showErrorMessage(res['message'], success, error);
                }
            }, modal);
        }
    });
}

function doCreationRequest(me, url, data, modal, postHandler) {
    doAjaxRequest(me, url, data, 'POST', '.success-creation', '.error-creation', modal, postHandler);
}

function doUpdateRequest(me, url, data, modal, postHandler) {
    doAjaxRequest(me, url, data, 'PUT', '.success-update', '.error-update', modal, postHandler);
}

function doDeletionRequest (me, url, data, modal, postHandler) {
    doAjaxRequest(me, url, data, 'DELETE', '.success-deletion', '.error-deletion', modal, postHandler);
}


/** file upload request. */
function doUploadFile(me, url, data, success, error, modal) {
    // show spinner
    $($(me).find('.nonSpinnerText')[0]).hide();
    $($(me).find('.spinnerText')[0]).show();

    $.ajax({
        url: url,
        type: 'post',
        data: data,
        dataType: 'json',
        cache: false,
        contentType: false,
        processData: false,
        success: function (result) {
            showSuccessMessage("Successfully.", success, error, 500, function(){
                if(modal) {
                    $(modal).hide()
                }
                window.location.reload();
            });
        },
        error: function (jqXHR, exception) {
            $($(me).find('.spinnerText')[0]).hide();
            $($(me).find('.nonSpinnerText')[0]).show();
            ajaxErrorHandler(jqXHR, exception, function() {
                var res = JSON.parse(jqXHR.responseText);
                showErrorMessage(res['message'], success, error);
            }, modal);
        }
    });
}
