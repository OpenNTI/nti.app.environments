def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=0)

    config.add_route('admin','/admin/*traverse',
                     factory='nti.app.environments.resources.admin_root_factory')
