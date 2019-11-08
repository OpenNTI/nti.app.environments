=========================
 Technical Documentation
=========================

Data Model
==========

There are two primary data model components.

Customers
---------

Customers represent users which own sites. Customers are identified by
email address. Conceptually customers may own many sites. In practice it is
typically one.

.. autointerface:: nti.onboarding.models.interfaces.ICustomer

.. note:: Initially we plan to limit one trial site per customer. As
          customers are identified by emails that means one site per
          verified email address. If this tool evolves in to something
          that tracks all sites/environments we may need to lift this
          restriction.

Sites
-----


Auththentication
================

Users in this system login with their email addresses. How they are
challenged for credentials depends on their type.

Authentication of admin users will be performed using Google
OAuth. This will be locked to the ``nextthought.com`` domain.

More interesting is the authentication of external users. As
conceptualized, external users will interact with the system to spin
up their trial sites. Once a user creates their site, there is no need for
them to interact with the system.

External users will be challenged by sending a one-time password (OTP)
to their email account. They will authenticate by clicking a link in
the email (similar to a reset password flow) or by entering the code
in the email in to a webpage.

.. note:: It's possible the external users could use this system to
          recover their site url should they forget it. In that case
          and OTP email challenge still seems fine.

.. note:: We could also consider using this system for license
          management. In which case we may need to revisit this. That
          flow remains an open question and we kick that can down the road.

One-time password challenges
----------------------------

When challenging the user we want a link that they can click to
authenticate *OR* a code that they can type into a password-like text
field. We're aiming for a balance beteween security and low friction
for users. Naturally codes generated to satisfy those requirements are
often at two ends of the spectrum. If dev had their way we would
generate a hex encoded uuid. If design had their way we would generate
a 4 digit numeric pin. Surely there is a compromise.

We need a code with enough entropy that we mitigate risk of brute
forcing. There's a really great discussion of this topic `here
<https://github.com/portier/portier-broker/issues/69>`_. Based on that
discussion I'd be comfortable with 12 characters chosen from the
`z-base-32
<http://philzimmermann.com/docs/human-oriented-base-32-encoding.txt>`_'s
alphabet. That should get us to 60 bits of entropy. If the code is
one-time use, expires after a reasonable short time (4 hours?), and we
restrict the number of incorrect guesses before invalidating the code,
it seems that should be good enough.

Twelve alphanumeric characters is still a large burden for a user to
remember and/or key in correctly, especially if they just glance at it
in a notification. Perhaps in the synchronous flow of setting up the
site we can do better and only require the user to key in half the
code. If the generated OTP is 12 characters and we prefill half of
those in to the challenge form when prompting the user, they only need
to key in the last 6 characters of the code. Unless we are subject to
a MITM attack (such that an attacker can see the half of the code in
the challenge form), we are running over ssl right?, this is no less
secure than the full 12 character code. The only way I see this is
less secure is if the attacker has access to the challenge form
(i.e. it's left up at a shared computer). Were limiting to a handful
of attempts at a given code, and expiring it in a relatively short
window. Surely that becomes a non issue?

.. note:: Why let the user type in the code? Why not just use the link
          in the email? It's likely that a user will receive the
          challenge email on a different device from where they are
          going through the process (for example notification on their
          phone when going through the process at their machine). That
          flow of swapping devices "is a pain".

With that out of the way, the mechanics of email-based OTP
authentication are pretty straightforward.

1. The user starts the process by providing their email.
2. The server generates a code as described above and stores a triplet
   of the form ``(code, time, attempts)`` with the email
   address. ``time`` is the current time, and ``attempts`` starts at
   ``0``.
3. The server disptaches an email two the provided address. The email
   contains to pieces of information.

   - An encoded link that contains the the email address and the otp.
   - The second half of the generated code in plain text.

4. The user is presented with a form containing hidden fields for the
   email, and the first half of the generated code. An additional
   field prompts the user for 6 characters (corresponding to the
   second half of the generated code in email).

5. The user answers the challenge by clicking the link in the email or
   submitting the form. At which point the submitted code is compared
   with the code stored against the email. If the code does not match
   the attempts are incremented. If the code has expired or the max
   attempts has been reached the process must start over.

6. Upon succesful challenge a **session** auht_tkt is created that
   will identify the user for the rest of their session.

