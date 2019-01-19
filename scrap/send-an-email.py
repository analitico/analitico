
from django.core.mail import send_mail
import datetime

send_mail(
    'Subject here ' + datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y"),
    'Here is the message.',
    'info@analitico.ai',
    ['gmettifogo@gmail.com'],
    fail_silently=False,
)