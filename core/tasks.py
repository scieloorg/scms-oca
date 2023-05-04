import logging

from django.core.mail import EmailMessage
from django.conf import settings

from config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def send_mail(
    self,
    subject,
    content,
    to_list=None,
    bcc_list=None,
    html=True,
    attachment_name=None,
    attachment_content=None,
    attachment_content_type=None,
):
    """
    Send email to list set on ``to_list`` param.
    This tasks consider the settings.DEFAUL_FROM_EMAIL as from_mail param

    :param subject: A string as subject
    :param content: A HTML or a plain text content
    :param to_list: A list or tuple with the e-mails to send message
    :param bcc_list: A list or tuple with the e-mails to send message as BCC
    :param html: Boolean to send as HTML or plain text, default is HTML
    :param attachment_name: String with name of the attachment
    :param attachment_content: String with the attachment content
    :param attachment_content_type: String with the attachment content type
        Ex.: application/pdf

    Return the result of django.core.mail.message.EmailMessage.send

    If any exception occurred the task will be re-executed in 3 minutes until
    default max_retries 3 times, all are celery default params
    """
    logger.info(content)

    if settings.EMAIL_SUBJECT_PREFIX:
        subject = settings.EMAIL_SUBJECT_PREFIX + subject

    msg = EmailMessage(subject, content, settings.DEFAULT_FROM_EMAIL, to_list, bcc_list)

    if attachment_content and attachment_name:
        msg.attach(attachment_name, attachment_content, attachment_content_type)

    if html:
        msg.content_subtype = "html"

    try:
        ret = msg.send()

        if ret:
            logger.info(
                "Successfully sent email message to ({0!r}) (bcc: {1!r}).".format(
                    to_list, bcc_list
                )
            )
        else:
            logger.error(
                "Erro sent email message to ({0!r}) (bcc: {1!r}).".format(
                    to_list, bcc_list
                )
            )

    except Exception as e:
        logger.error(
            "Failed to send email message to ({0!r}) (bcc: {1!r}), traceback: {2!s}".format(
                to_list, bcc_list, e
            )
        )
        raise self.retry(exc=e)
