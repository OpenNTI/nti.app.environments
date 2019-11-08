Site Onboarding
===============

We refer to the act of a person spinning up and gaining access to
their trial site as *Site Onboarding* or *Onboarding*. The onboarding
process starts primarily from marketing pages that prompt users to
begin a free trial. For example:

.. image:: images/cta-example.png

The general flow is as follows:

1. Prompt user for email address.

2. Prompt user for marketing data collection.

3. Validate user email with an email based challenge.

4. Prompt for additional user information.

5. Prompt for site information such as domain name.

6. Spin up site.

7. Complete account setup on site.

8. Complete site onboard on site.


.. note:: An alternative flow is that sales provides existing contacts
          a link to start their free trial. In that scenario users
          likely come in to the process at step 3.

Design has done an audit of several SaaS product trial onboarding
flows. Those flows can be seen in this :download:`document
<documents/flow-annotated.pdf>`.

They have also done some exploration of what a potential NextThought
flow will look like :download:`here <documents/nt-explorations.pdf>`.

.. note:: Initially we will be shooting for a flow that approximates
          the ``Minimal`` flow outlined in :download:`NT Explorations
          <documents/nt-explorations.pdf>`.

HubSpot
-------

Sales and Marketing utilize `HubSpot <https://www.HubSpot.com>`_ as a
CMS and marketing tool. This tool has support for deal / conversion
tracking, automated marketing campaigns, lead qualification and
assignment, etc. In addition, HubSpot has complex call-to-action, form,
and page builders that can be used to collect user information and
trigger workflows.

Some level of integration with HubSpot will need to be facilitated. At
a minimum we need to trigger the site onboarding flow at the
completion of one or more HubSpot CTAs or forms. Ideally we would also
be able to communicate status about the setup and whether the trial
has been accessed so that HubSpot data flows can be used to drive
marketing workflows.

Assertions and Simplifying Assumptions
--------------------------------------

- Onboarding flow needs to be triggered from a number of different
  locations including targeted marketing pages, email flows, sales
  outreach, etc.

- When triggering the onboarding flow via HubSpot we should make
  every attempt to not request data we already have.

- We require a valid email, verified by challenge, to start a trial flow.

- Trials should be limited one per valid email.

.. question:: How strictly do we need limit access to the flow based
              on having collected marketing information?

	      In general we only want people that turn in to leads,
	      i.e People that have gone through the flow and we have
	      collected data to help qualify the lead. However, there
	      will be a number of contacts from other sources. Direct
	      outreach, for example, in which sales or marketing have
	      existing targeted contacts that they want to invite to
	      create sites. In that case we probably don't want to
	      have to have them got through the marketing
	      flow. Presumably these users are already in HubSpot
	      as contacts. We could require some kind of gate on the
	      HubSpot contact (property or specific type of deal) but
	      that adds an additional step for sales to remember to
	      do.

	      Ultimately we want all potential sales in HubSpot, and
	      we want enough marketing data to qualify those leads and
	      get them to the appropriate sales process. Through a
	      normal no-touch flow, the first couple of marketing
	      pages can take care of that. In the direct outreach that
	      seems like that is mostly already done by sales. The
	      hole is someone that figures out how to spin up a site
	      that bypasses the marketing flow. Do we need to guard
	      against that? It probably only happens if people are
	      sending direct links around?

	      It seems like a simplifying assumption to not do
	      that. Given our desire to get people in to the
	      platform, and our desire to put something together
	      quickly it seems like we wait to see if this loophole
	      is actually a problem.

High Level Process
------------------

This section describes the high level site and user creation flow. It
is assumed that users are sent to this flow from marketing outreach,
landing pages, or direct sales outreach.

.. note:: For the purposes of this discussion site onboarding system
          refers to a web application hosted on an separate domain
          from HubSpot or the platform. e.g. ``getstarted.nextthought.com``.

.. note:: Screenshots included are for illustrative purchases. They
          approximate roughtly what we are going for but may change.


1. User arrives at the onboarding system and is presented with a form
   to collect name, email, and username. If the user was brought to
   the flow from the full marketing driven process this information
   will be provided.

   .. image:: images/user-info.png

   .. question:: How is this information communicated?

		 It seems there are two options. Pass all the
		 information in the url (query parameters or state in
		 the fragment), or pass just the HubSpot contact id
		 / email and look up the information from
		 HubSpot. The former seems easiest. The latter seems
		 most useful if we otherwise need to track
		 information in HubSpot or gate based on something
		 in HubSpot.

2. User confirms the information and elects to proceed. At this
   point an email notification with a unique code is sent to the
   user. And the user is sent to a form to enter the code. This step
   is used to verify the email address. The code is a short,
   one time use, limited life code that the user is asked for.

   .. image:: images/email.png

   .. question:: How small can we get the code and have enough
		 entropy to not run in to issues?

		 Design wants a six digit numeric code. Can we get
		 away with that? Do we need to go alphanumeric?

3. User enters the code. If it matches, the user can proceed through
   site setup. If it is invalid, the user shows an error message with
   an option to change the email and/or trigger a new email.

   .. image:: images/email-challenge.png

4. Having entered a valid code the user moves on to selecting a
   domain name for the site. We've established that for trials all
   urls are a subdomain of ``nextthought.com`` and they are assigned
   a random suffix. That is, users can select the prefix of a
   domain that looks like ``<prefix>-1234.nextthought.com``.

   .. image:: images/domain.png

   .. question:: How small and of what characters can we get the suffix to?

		 Again, design desires a short number (4-6) numeric
		 characters. Do we need to go to 4-6 alphanumeric?

   .. question:: What other restrictions do we put here? Ultimately we
		 will want to censor and have a blacklist of domain
		 names that we retain ownership of.  Should we apply
		 those same set of rules to the prefix? At a bare
		 minimum it seems like we would want to censor.

		 This view will need to validate if the entered prefix produces a
		 valid domain and if it is available.

  .. note:: I don't think farming for used domains here is an issue
	    because of the suffix, but it does seem like we could
	    get in to a case where the suffix-less version isn't
	    available once you pay. That might be annoying but
	    there probably isn't anything we can do about it.
	    
5. At this point the user confirms their information and creates their
   site. This triggers the back-end to start spinning up the
   environment for the desired hostname. We expect this to take
   several seconds (not several minutes!).

6. The user is taken to a waiting page while their site is being
   setup. There are a few options for what is displayed here. We'll
   want something to occupy the user. It could be a welcome /
   introduction video, a set of static slides and platform tips, a
   progress bar with various (fake things) that are happening behind
   the scene, or some combination.

   At the same time an email is also dispatched to the user welcoming
   them to the platform and providing them a link in to their
   site. Ideally the link works at any point going forward. If the
   site setup is complete the link redirects them in to the platform. If the
   site is not setup they user would land at the waiting screen.

7. When the environment is setup the dataserver site will exist with
   the user, as a site admin, in the database. However, the user will
   not yet have a password. They'll be landed on a page similar to the
   reset password flow where they can enter a password.

   .. image:: images/set-password.png


8. Finally the user will be logged in to their site.

   .. image:: images/welcome-home.png

..  LocalWords:  Onboarding
