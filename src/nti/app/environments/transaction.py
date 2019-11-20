
def default_commit_veto(request, response):
    xtm = response.headers.get('x-tm')
    if xtm is not None:
        return xtm != 'commit'
    if request.method == 'GET' or request.method == 'HEAD':
        return True
    return response.status.startswith(('4', '5'))
