"use strict";

function getValue(id) {
    var val = document.getElementById(id).value.trim();
    return val ? val : null;
}

function saveItem (me, url) {
    var email = getValue("customer_email");
    var name = getValue('customer_name');
    if(!name || !email){
        showErrorMessage("Please fill in required fields.", '.success-creation', '.error-creation');
        return
    }

    var phone = getValue("customer_phone");
    var organization = getValue("customer_organization");
    var data = {
        "email": email,
        "name": name,
        "phone": phone,
        "organization": organization,
        "MimeType": "application/vnd.nextthought.app.environments.customer"
    };
    data = JSON.stringify(data);
    doCreationRequest(me, url, data, '#newModal');
}

function saveItemViaHubspot (me, url) {
    var email = getValue("customer_email");
    if(!email){
        showErrorMessage("Please fill in email field.", '.success-creation', '.error-creation')
        return
    }

    var data = {
        "email": email
    };
    doCreationRequest(me, url, data, '#newModal');
}

function deleteItem (me) {
    var url = $(me).attr('delete_url');
    doDeletionRequest(me, url, {}, '#deletingModal');
}

function openDeletingModal(url, email) {
    var modal = document.getElementById("deletingModal");
    modal.style.display = "block";
    modal.getElementsByClassName('btnOK')[0].setAttribute('delete_url', url);
    modal.getElementsByClassName('deleting_email')[0].innerHTML = email;
}

function closeDeletingModal() {
    var modal = document.getElementById("deletingModal");
    modal.style.display = "none";
}

function openNewModal(me, creation_url, label) {
    clearMessages('.success-creation', '.error-creation');

    var modal = $('#newModal');
    $(modal.find('.modal-title')).text( $(me).text() );
    $(modal.find('.btnSave')).attr('onclick', "saveItem(this, '" + creation_url + "');")

    $('#customer_name').val('');
    $('#customer_email').val('');
    $('#customer_phone').val('');
    $('#customer_organization').val('');

    if(label==='hubspot'){
        $(modal.find('.input-row-name')).hide();
        $(modal.find('.input-row-email')).show();
        $(modal.find('.input-row-phone')).hide();
        $(modal.find('.input-row-organization')).hide();
        $(modal.find('.btnSave')).attr('onclick', "saveItemViaHubspot(this, '" + creation_url + "');")
    } else {
        $(modal.find('.input-row-name')).show();
        $(modal.find('.input-row-email')).show();
        $(modal.find('.input-row-phone')).show();
        $(modal.find('.input-row-organization')).show();
        $(modal.find('.btnSave')).attr('onclick', "saveItem(this, '" + creation_url + "');")
    }
    $(modal).css('display', 'block');
}