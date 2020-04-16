Weekly Trial Site Digest

Trial Sites Ending This Week:

% if not ending_items:
    No trial sites ending in the next 7 days.
% endif
% if ending_items:
    Total: ${len(ending_items)}
% for item in ending_items:

    Site Name : ${item['site_name']}
    Site Id: ${item['site_id']}
    Owner: ${item['owner']}
    Creator: ${item['creator']}
    Created Time: ${item['createdTime']}
    End Date: ${item['end_date']}
% endfor
% endif


Trial Sites Past Due:
% if not past_items:
    No trial sites past due.
% endif
% if past_items:
    Total: ${len(past_items)}
% for item in past_items:

    Site Name : ${item['site_name']}
    Site Id: ${item['site_id']}
    Owner: ${item['owner']}
    Creator: ${item['creator']}
    Created Time: ${item['createdTime']}
    End Date: ${item['end_date']}
% endfor
% endif