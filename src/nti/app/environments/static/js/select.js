function arrayEqual(x, y) {
    if(x.length != y.length){
        return false
    }
    x.forEach(item => {
        if (y.indexOf(item) <= -1){
            return false;
        }
    });
    return true;
}

$('.drop-select .drop-item').click(function () {
    var dropSelect = $(this).closest('.drop-select');
    var dropBtn = $(dropSelect).find('.drop-btn');
    var old = $(dropBtn).attr('value');
    var current = old ? old.split(",") : [];
    old = old ? old.split(",") : [];

    var tmp = $(this).attr("value");
    if (!tmp) {
        current = [];
        $(dropBtn).attr('value', '');
        $(dropBtn).text('Nothing selected');
        $(dropSelect).find('.drop-item').removeClass('selected');
    } else {
        var index = current.indexOf(tmp);
        if (index > -1) {
            current.splice(index, 1);
            $(this).removeClass('selected');
        } else {
            current.push(tmp);
            $(this).addClass('selected');
        }

        if (current.length > 0) {
            $(dropBtn).attr('value', current.join(','));
            $(dropBtn).text(current.join(','));
        } else {
            $(dropBtn).attr('value', '');
            $(dropBtn).text('Nothing selected');
        }
    }
    if(arrayEqual(old, current)){
        return
    }
    $(dropBtn).trigger('CustomSelectChanged');
});

$('.drop-select .drop-toggle').click(function(){
    var dropSelect = $(this).closest('.drop-select');
    var dropMenu = $(dropSelect).find('.drop-menu');
    if($(dropSelect).hasClass('show')){
        $(dropSelect).removeClass('show');
        $(dropMenu).css('display', 'none');
    } else {
        $(dropSelect).addClass('show');
        $(dropMenu).css('display', 'block');
    }
});

function update_drop_select(selector, value) {
    var dropSelect = $(selector);
    var current = [];
    $(dropSelect).find('.drop-item').each(function(index, elem){
        var tmp = $(elem).attr('value');
        if (tmp && value.includes(tmp)){
            $(elem).addClass('selected');
            current.push(tmp);
        }
    });
    var dropBtn = $(dropSelect).find('.drop-btn');
    if (current.length > 0) {
        $(dropBtn).attr('value', current.join(','));
        $(dropBtn).text(current.join(','));
    } else {
        $(dropBtn).attr('value', '');
        $(dropBtn).text('Nothing selected');
    }
}

function updateDropSelects(entries, filterBy) {
    filterBy = filterBy ? filterBy : getUrlParameter('filterBy');
    if(filterBy) {
        filterBy = filterBy.split(';');
        filterBy.forEach(function(item){
            var kv = item.split('=');
            for(var i = 0; i < entries.length; i++) {
                var entry = entries[i];
                if(kv[0] === entry[0]) {
                    var value = kv[1].split(',');
                    if(value) {
                        update_drop_select(entry[1], value);
                    }
                }
            }
        });
    }
}

function updateFilterBy(entry, current) {
    // current: "name1=value1;name2=value2"
    // entry: ['name1', 'value1']
    current = current ? current : getUrlParameter('filterBy');
    if(!current) {
        current = entry[0] + "=" + entry[1];
    } else {
        var  entries= current.split(';');
             isNewEntry = true;
        current = [];
        for(var i = 0; i < entries.length; i++) {
            var tmp = entries[i].split('=');
            if(tmp.length != 2) {
                continue;
            }
            if (tmp[0] !== entry[0]) {
                current.push(entries[i]);
            } else if(tmp[0] === entry[0]){
                isNewEntry = false;
                current.push(entry[0] + "=" + entry[1]);
            }
        }
        if (isNewEntry) {
            current.push(entry[0] + "=" + entry[1]);
        }
        current = current.join(";");
    }
    return current;
}
