def includeme(config):
    config.add_static_view('static', 'static', cache_max_age=3600)

    config.add_route('dashboards','/onboarding/dashboards/*traverse',
                     factory='nti.app.environments.resources.DashboardsResource')

    config.add_route('roles','/onboarding/roles/*traverse',
                     factory='nti.app.environments.resources.RolesResource')

    config.add_route('stripe.hooks', '/stripe/hooks')
