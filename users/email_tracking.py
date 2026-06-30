from django.core.mail import EmailMessage

from .models import EmailLog


def _create_logs(subject, recipients, from_email, body='', status=EmailLog.Status.SENT, error_message='', context_type='', triggered_by=None):
    for recipient in recipients:
        EmailLog.objects.create(
            recipient=recipient,
            subject=subject,
            from_email=from_email or '',
            body=body or '',
            context_type=context_type,
            status=status,
            error_message=error_message,
            triggered_by=triggered_by,
        )


def send_tracked_email_message(email_message, context_type='', triggered_by=None):
    recipients = list(email_message.to or [])
    try:
        result = email_message.send(fail_silently=False)
    except Exception as error:
        _create_logs(
            subject=email_message.subject,
            recipients=recipients,
            from_email=email_message.from_email,
            body=email_message.body,
            status=EmailLog.Status.FAILED,
            error_message=str(error),
            context_type=context_type,
            triggered_by=triggered_by,
        )
        raise

    _create_logs(
        subject=email_message.subject,
        recipients=recipients,
        from_email=email_message.from_email,
        body=email_message.body,
        status=EmailLog.Status.SENT,
        context_type=context_type,
        triggered_by=triggered_by,
    )
    return result


def send_tracked_mail(subject, message, from_email, recipient_list, context_type='', triggered_by=None):
    email_message = EmailMessage(subject, message, from_email, recipient_list)
    return send_tracked_email_message(
        email_message,
        context_type=context_type,
        triggered_by=triggered_by,
    )
