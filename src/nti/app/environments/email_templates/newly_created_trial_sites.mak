Trial Sites Created This Week

% if not items:
No trial sites created in the last 7 days.
% endif
% if items:
    Total: ${len(items)}
% for item in items:

    Site Name : ${item['site_name']}
    Site Id: ${item['site_id']}
    Owner: ${item['owner']}
    Creator: ${item['creator']}
    Created Time: ${item['createdTime']}
% endfor
% endif
