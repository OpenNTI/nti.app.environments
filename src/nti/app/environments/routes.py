def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('dashboards','/onboarding/dashboards/*traverse',
                     factory='nti.app.environments.resources.DashboardsResource')
