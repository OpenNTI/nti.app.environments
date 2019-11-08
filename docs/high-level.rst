Initial Discussions and Thoughts
================================

Supporting the business and sales direction has a number of technical
implications. It requires the ability to:

- Rapidly spin up and provision client sites in real time by the end user.

- Provide appropriate safe guards around usage and resources for trial sites.

- Easily spin down and reclaim resources for non converted clients.

- Feed sales and marketing with intelligence on what client sites exists and how they are being used.

- Support for user facing subscription of basic access.

- Ability to scale users from initial trial up to full blow enterprise solution
  without losing data or requiring mountains of work for NextThought (or the client).

An initial implementation is focused on speed to market and the ability
to iterate rapidly as we chart this new path forward. While we would
prefer not to paint ourselves in to a corner with any of our
technical decisions, we need to move quickly so that we can start
testing the business and marketing theories that are driving this initiative.

.. containerized-approach-label_

Single Tenant Containerized Approach
------------------------------------

As noted in :ref:`motivation-label` the current process for creating
and deploying client sites has friction with the aforementioned
requirements. Initial discussions and research has suggested that
moving site deployments to an isolated container based approach solves
a number of these problems, while setting us up to more easily scale
sites as needed. A site per container approach has the following benefits.

- Sites are isolated and can more easily have their resources
  constrained at the OS / container level.

- Building out a new site, at a high level, involves deploying a new
  set of containers.

- Tearing down a site and all its resources involves tearing down one
  or more containers.

- Sites can be scaled up as needed including deployment to the cloud.

- Sites can more easily be moved around to different hardware,
  between local datacenter and the cloud, etc.

Of course there are trade offs to moving towards a single tenant
containerized deployment approach.

- Additional hardware overhead for each site as there are much fewer shared
  services.

- Requirement for additional tooling around monitoring and
  deployment of many environments. There are many open source tools
  and container management systems that can help with this.

- Shift in mindset for how we deploy and manage sites.

- Isolates sites entirely from one another. Any sort of coordination
  between sites (federated login for example) requires additional
  layers to be built out on top of the environments.

These are all solvable problems, many of which are accounted for via
tooling (most of which we hope to get from OSS).

.. note:: Due to the complexities of moving clients from a shared
          environment to their own environment, there are no plans to
          migrate existing clients at this time. Likewise, we don't
          intend to make any infrastructure or application changes
          that would prohibit us from leveraging shared environments in the future.

Trials
------

Trials for SaaS products can be structured in a number of ways. They
can be limited by time, by functionality, or some combination of
both. Some products require payment information upfront. Others don't
require payment information until the customer is converted.

.. note:: As a general philosophy we want a low barrier for starting a
          trial.

Initially we will time box the trial and enforce OS level
limitations via :ref:`containerized-approach-label`. This is the most
straightforward technical approach. We may enforce application limits
in the future (limit number of courses, number of users, etc). We will
not require any payment information initially.

As the business model evolves the specifics of the trial may be revisited.

.. note:: As a general philosophy the trial should limit the platform
          to mitigate additional costs incurred by NT (e.g. SCORM) and
          prevent clients from making money without buying a license.


Off-the-shelf subscriptions
---------------------------

Users should be able to convert to a basic, off-the-shelf,
subscription based product without intervention from
NextThought. Stripe has incredibly flexible subscription support which
could be leveraged to support what seems like any model that can be
come up with. Stripe also support very low effort (in terms of
integration required) subscriptions via their "Checkout" product. We
could leverage Checkout for subscriptions until we need a more
integrated solution.

Upgrading to a paid account will unlock some additional functionality
such as SCORM, further customization of domain name, etc. Users should
be able to upgrade their sites seamlessly with no loss of data and
ideally limited or no downtime.

Enterprise
----------

Users should be able to work with sales to upgrade their existing site
(either trial or subscription) to an enterprise license. This can be a
complex implementation. We need the ability to seamlessly transition
their sites data but this can be scheduled and doesn't necessarily
need to be downtime free. Enterprise sites should be extensible and
support custom code and configuration as most of our big sites do now.


..  LocalWords:  SCORM
