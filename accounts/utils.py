import requests
from pygeocoder import Geocoder, GeocoderError

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.mail import EmailMultiAlternatives
from django.template import loader
from django.utils import timezone

from core.utils import get_date_a_month_later, send_admin_email


def init_kwargs(model, arg_dict):
    return {
        k: v for k, v in arg_dict.items() if k in [
            f.name for f in model._meta.get_fields()
        ]
    }


def send_welcome_email(user_cc):
    user = user_cc.user
    role = user.get_role()
    referral_token = user.referral_token
    to_email = user.email
    referral_link = '{}/registration?token={}'.format(settings.HOSTNAME_PROTOCOL,
        referral_token)

    if role == 'instructor':
        cta = "Get $5 in Cash"
        text = "Invite your colleagues to join Nabi, and get $5 in cash"
        bullet = "Invite your colleagues to join Nabi, and get $5 in cash."
        todo = "Make sure your profile is 100% complete."
    else:
        cta = "Give 20% off, Get $5"
        text = "Give your friends 20% off music lessons when they book lessons from your referral link. You get $5 in cash!"
        bullet = "Invite your friends to join Nabi, and get $5 in cash."
        todo = "Make sure your student details are set."

    context = {
        'referral_link': referral_link, 'referral_text': text,
        'referral_cta': cta, 'referral_bullet': bullet, 'todo': todo }
    text_content = loader.render_to_string('welcome_to_nabi_plain.html', context)
    html_content = loader.render_to_string('welcome_to_nabi.html', context)
    from_email = 'Nabi Music <' + settings.DEFAULT_FROM_EMAIL + '>'
    subject = 'Welcome to Nabi Music!'
    email_message = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email_message.attach_alternative(html_content, 'text/html')
    email_message.send()


def send_referral_invitation_email(user, email):
    referral_token = user.referral_token
    date_limit = get_date_a_month_later(timezone.now())
    referral_url = '{}/referral/{}'.format(settings.HOSTNAME_PROTOCOL, referral_token)

    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['referral_email'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": email},
            "customProperties": [
                {"name": "first_name", "value": user.first_name},
                {"name": "last_name", "value": user.last_name},
                {"name": "date_limit", "value": date_limit.strftime('%m/%d/%Y')},
                {"name": "referral_url", "value": referral_url},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Referral email could not be send",
                         """Email referring another person could not be send, with data {}.

                         The status_code for API's response was {} and content: {}""".format(
                             data,
                             resp.status_code,
                             resp.content.decode()
                             )
                         )
        return False
    return True


def add_to_email_list(user, list_name):
    """Add email of user to Sendgrid's email list, including first_name and last_name if are non-empty"""
    header = {'Authorization': 'Bearer {}'.format(settings.EMAIL_HOST_PASSWORD), 'Content-type': 'application/json'}
    contact = {'email': user.email}
    if user.first_name:
        contact['first_name'] = user.first_name
    if user.last_name:
        contact['last_name'] = user.last_name
    response = requests.put('{}marketing/contacts'.format(settings.SENDGRID_API_BASE_URL),
                            json={'list_ids': [settings.SENDGRID_CONTACT_LIST_IDS.get(list_name)],
                                  'contacts': [contact]},
                            headers=header
                            )
    if response.status_code != 202:
        send_admin_email("[INFO] Contact couldn't be added to {} list".format(list_name),
                         """The contact {} could not be added to {} list in Sendgrid.
                         The status_code for API's response was {} and content: {}""".format(list_name,
                                                                                             contact,
                                                                                             response.status_code,
                                                                                             response.content.decode())
                         )


def add_to_email_list_v2(user, list_names, remove_list_names=None):
    """Add user's email and referral token to HubSpot's lists, including first_name and last_name if are non-empty"""
    if settings.ENVIRON_TYPE != 'production':   # only add account to list in production environment
        return None
    if remove_list_names is None:
        remove_list_names = []
    # first, check if contact exists already in HubSpot
    target_url = f'https://api.hubapi.com/contacts/v1/contact/email/{user.email}/profile?hapikey={settings.HUBSPOT_API_KEY}'
    resp = requests.get(target_url)
    if resp.status_code == 200:
        contact_id = resp.json().get('vid')
    elif resp.status_code == 404:
        # then, create contact
        target_url = f'https://api.hubapi.com/contacts/v1/contact?hapikey={settings.HUBSPOT_API_KEY}'
        property_list = [{'property': 'email', 'value': user.email},
                         {'property': 'referral_token', 'value': user.referral_token}]
        if user.first_name:
            property_list.append({'property': 'firstname', 'value': user.first_name})
        if user.last_name:
            property_list.append({'property': 'lastname', 'value': user.last_name})
        resp = requests.post(target_url, json={'properties': property_list})
        if resp.status_code == 200:
            contact_id = resp.json().get('vid')
        else:
            send_admin_email("[INFO] Contact couldn't be created",
                             f"""The contact {property_list} could not be created in HubSpot.
    
                             The status_code for API's response was {resp.status_code} and content: {resp.content.decode()}"""
                             )
            return None
    else:
        send_admin_email("[INFO] Contact couldn't be searched",
                         f"""The contact {user.email} could not be searched in HubSpot.
    
                         The status_code for API's response was {resp.status_code} and content: {resp.content.decode()}"""
                         )
        return None

    # now, add contact to required list
    for list_name in list_names:
        list_id = settings.HUBSPOT_CONTACT_LIST_IDS[list_name]
        target_url = f'https://api.hubapi.com/contacts/v1/lists/{list_id}/add?hapikey={settings.HUBSPOT_API_KEY}'
        resp = requests.post(target_url, json={'emails': [user.email]})
        if resp.status_code != 200:
            send_admin_email(f"[INFO] Contact couldn't be added to list {list_name}",
                             f"""The contact {user.email} could not be added to list {list_name} in HubSpot.
    
                             The status_code for API's response was {resp.status_code} and content: {resp.content.decode()}"""
                             )

    # finally, delete contact from specified list
    for remove_list_name in remove_list_names:
        list_id = settings.HUBSPOT_CONTACT_LIST_IDS[remove_list_name]
        target_url = f'https://api.hubapi.com/contacts/v1/lists/{list_id}/remove?hapikey={settings.HUBSPOT_API_KEY}'
        resp = requests.post(target_url, json={'vids': [contact_id]})
        if resp.status_code != 200:
            send_admin_email(f"[INFO] Contact couldn't be deleted from list {remove_list_name}",
                             f"""The contact {user.email} could not be added to list {remove_list_name} in HubSpot.

                             The status_code for API's response was {resp.status_code} and content: {resp.content.decode()}"""
                             )


def remove_contact_from_email_list(contact_id, email, list_name):
    """Remove email of user from Sendgrid's email list"""
    header = {'Authorization': 'Bearer {}'.format(settings.EMAIL_HOST_PASSWORD), 'Content-type': 'application/json'}
    target_url = '{}marketing/lists/{}/contacts?contact_ids={}'.format(settings.SENDGRID_API_BASE_URL,
                                                                       settings.SENDGRID_CONTACT_LIST_IDS.get(list_name),
                                                                       contact_id)
    response = requests.delete(target_url, headers=header)
    if response.status_code != 202:
        send_admin_email("[INFO] Contact couldn't be removed from {} list".format(list_name),
                         """The contact {} (id: {}) could not be removed from {} list in Sendgrid.

                         The status_code for API's response was {} and content: {}""".format(email,
                                                                                             contact_id,
                                                                                             list_name,
                                                                                             response.status_code,
                                                                                             response.content.decode())
                         )


def send_reset_password_email(email, token):
    """Use HubSpot'a API to send email. Return True if response is successful, return False otherwise"""
    target_url = 'https://api.hubapi.com/email/public/v1/singleEmail/send?hapikey={}'.format(settings.HUBSPOT_API_KEY)
    passw_reset_link = '{}/forgot-password?token={}'.format(settings.HOSTNAME_PROTOCOL, token)
    data = {"emailId": settings.HUBSPOT_TEMPLATE_IDS['password_reset'],
            "message": {"from": f'Nabi Music <{settings.DEFAULT_FROM_EMAIL}>', "to": email},
            "customProperties": [
                {"name": "password_reset_link", "value": passw_reset_link},
            ]
            }
    resp = requests.post(target_url, json=data)
    if resp.status_code != 200:
        send_admin_email("[INFO] Reset password email could not be send",
                         """An email for reset password could not be send to email {}.

                         The status_code for API's response was {} and content: {}""".format(email,
                                                                                             resp.status_code,
                                                                                             resp.content.decode()
                                                                                             )
                         )
        return False
    return True


def get_stripe_customer_id(user):
    """This function allow to obtain the stripe_customer_id from provided user"""
    if user.is_parent():
        return user.parent.stripe_customer_id
    elif user.is_student():
        return user.student.stripe_customer_id
    else:
        return None


def get_geopoint_from_location(location):
    assert location != ''
    geocoder = Geocoder(api_key=settings.GOOGLE_MAPS_API_KEY)
    try:
        results = geocoder.geocode(location)
    except GeocoderError.G_GEO_ZERO_RESULTS:
        return None
    except GeocoderError as e:
        raise Exception(e.status, e.response)
    return Point(results[0].coordinates[1], results[0].coordinates[0], srid=4326)


def get_availaibility_field_name_from_dt(datetime_obj, tz_target):
    localize_datetime = datetime_obj.astimezone(timezone.pytz.timezone(tz_target))
    field_name = localize_datetime.strftime('%A').lower()[:3]
    if localize_datetime.hour >= 18:
        if localize_datetime.hour < 21:
            field_name += '6to9'
        else:
            return ''
    elif localize_datetime.hour >= 15:
        field_name += '3to6'
    elif localize_datetime.hour >= 12:
        field_name += '12to3'
    elif localize_datetime.hour >= 10:
        field_name += '10to12'
    elif localize_datetime.hour >= 8:
        field_name += '8to10'
    else:
        return ''
    return field_name
