.. Auto Site Creation documentation master file, created by
   sphinx-quickstart on Wed Oct  9 13:03:06 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Auto Site Creation's documentation!
==============================================

This documentation describes the infrastructure, workflow, and
deployment processes to support the Auto Site Creation Initiative.

Motivation
------------

As a business, our current process for acquiring platform customers
isn't providing the type of grwoth we are looking for. We desire a
process that lets us quickly get potential users into the platform so
they can evaluate how the product meets their needs with minimal
intervention from NextThought. This helps not only with qualifying
inbound leads but also with setting the expectations that our clients
have of the product and our team going forward. The business is also
in a place where we desire the ability to quickly target and test out
new potential markets and customers.

We need a new approach to how we acquire, qualify, and convert leads
to paying customers, and these customers need to have better
expectations around the *product* they are purchasing and the level of
support, implementation, and customization they can expect to
receive. Ideally our low paying and low usage clients are treating the
platform as an off the shelf product with low acquisition and ongoing
support costs incurred by us. The initiative described by this
document is meant to facilitate servicing this type of client more
efficiently as well as providing a better qualified pipeline of
enterprise leads.

.. note:: There is *NO* plan to stop providing enterprise
          customization and service for clients that are in an
          enterprise tier. The intent is not to change or eliminate
          those types of clients. Our ability to customize and provide
          enterprise services is a great differentiator that we intend
          to continue to leverage.


We want to move to a model where clients can automatically spin up a
trial site that they own, in real time and without intervention from
NextThought. These users act as an immediate source of leads that can
then be converted to paying clients either by subscribing to the
platform directly (think typical off the shelf SaaS model) or by
working with sales to acquire an enterprise license. Non-enterprise
users would use the platform with as little intervention from
NextThought teams (ideally this is full self-service) but remain a
target for potential enterprise up-selling or service up-selling for sales.

.. _motivation-label:

A New Approach
--------------

NextThought's current site on-boarding involves a somewhat lengthy
(relatively speaking) implementation process that requires multiple
NextThought teams to be involved in spinning up a site for a
client. While we have made strides to streamline the current process
with tooling, the process remains largely unchanged. Setting up a site
involves the following series of steps:

 1. Client or sales requests a site be setup.
    
 2. Back-end and front-end packages are created to house client site
    specific assets, configuration and code.

 3. An environment is identified for where the site should be
    installed. Typically this is the shared environment known as ``prod``.

 4. The back-end and front-end packages are deployed to the environment.

This process has been streamlined such that it can be completed in
24 hours, but it involves multiple teams, the creation of
multiple assets packages, and, in most cases, a deployment and restart
of a shared environment.

In addition, the majority of sites are created in a shared
environment. This is primarily due to the additional overhead required
in spinning up standalone environments. These shared environments also
create a number of complexities due to their lack of isolation.

 - Nefarious or even well meaning clients can affect other clients
   in the shared environments.

 - Restricting clients to a subset of hardware (storage, bandwidth,
   cpu) is incredibly difficult.

 - Scaling an enterprise client out to a dedicated environment is not
   currently possible.

 - Tearing down a client no longer needed is complex and not well supported.

The current approach to site setup has friction with were we want to take the business.

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   high-level
   onboarding
   techincal/index
   questions

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
