from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string


def send_email(subject, body_text_content, recipient_list, html_content=None):
    email_message = EmailMultiAlternatives(
        subject=subject,
        body=body_text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
    )
    if html_content:
        email_message.attach_alternative(html_content, "text/html")
    email_message.send(fail_silently=True)


def generate_verification_link(request, uid):
    current_site = (
        f"{settings.FRONT_END_URL}/{settings.VERIFICATION_EMAIL_FRONTEND_URL}"
    )
    return f"{current_site}/{uid}/"


def send_verification_email(
    request, recipient_email, verification_link, name, template
):
    subject = "Email Verification"
    context = {"verification_link": verification_link, "name": name, "request": request}
    html_content = render_to_string(template, context)
    message = f"Click the following link to verify your email: {verification_link}"
    recipient_list = [recipient_email]
    send_email(subject, message, recipient_list, html_content)
