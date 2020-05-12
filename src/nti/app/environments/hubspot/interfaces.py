from zope import interface


class IHubspotClient(interface.Interface):
    """
    A client object for interacting with hubspot
    """

    def fetch_contact_by_email(email):
        """
        Lookup the hubspot contact information by the provided email. Returns
        None if no contact can be found.
        """

    def create_contact(email, name, phone, product_interest):
        """
        Create a new contact in hubspot with the given email, name, phone,
        and product interest. Returns the created contact or None if no contact was created.
        """

    def update_contact(email, name, phone, product_interest):
        """
        Update the existing hubspot contact matched by the provided email with a
        new name, phone, and product_interest.
        """

    def update_contact_with_properties(email, props):
        """
        Update the existing hubspot contact as matched by email with
        the provided properties.
        """

    def upsert_contact(email, name, phone, product_interest='LMS'):
        """
        Upsert a hubspot contact with the given email, name, phone, and
        product_interest. Matches are performed by email address.
        """
