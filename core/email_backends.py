# core/email_backends.py
import os
from django.core.mail.backends.base import BaseEmailBackend
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content, To, From, MailSettings, SandBoxMode

def _send_single_message(self, email_message):
    to_emails = [To(email) for email in email_message.to]
    
    # Check if sandbox should be enabled (e.g., from settings or env)
    # Recommended: use a specific setting like SENDGRID_SANDBOX_MODE
    use_sandbox = os.environ.get('SENDGRID_SANDBOX_MODE', 'False') == 'True'

    mail = Mail(
        from_email=From(email_message.from_email),
        to_emails=to_emails,
        subject=email_message.subject,
        plain_text_content=email_message.body,
    )

    # Apply Sandbox Mode
    mail.mail_settings = MailSettings(
        sandbox_mode=SandBoxMode(enable=use_sandbox)
    )


class SendGridBackend(BaseEmailBackend):
    """
    Custom email backend using SendGrid Python Library.
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY environment variable is not set")
    
    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of emails sent.
        """
        if not email_messages:
            return 0
        
        num_sent = 0
        for email_message in email_messages:
            try:
                self._send_single_message(email_message)
                num_sent += 1
            except Exception as e:
                if not self.fail_silently:
                    raise e
        
        return num_sent
    
    def _send_single_message(self, email_message):
        """
        Send a single EmailMessage using SendGrid API.
        """
        # Prepare recipients
        to_emails = [To(email) for email in email_message.to]
        
        # Prepare content
        if email_message.body:
            content = Content("text/plain", email_message.body)
        else:
            # Handle HTML content
            content = Content("text/html", email_message.alternatives[0][0] if email_message.alternatives else "")
        
        # Create Mail object
        mail = Mail(
            from_email=From(email_message.from_email),
            to_emails=to_emails,
            subject=email_message.subject,
            plain_text_content=email_message.body,
        )
        
        # Add HTML content if available
        if email_message.alternatives:
            for content, mimetype in email_message.alternatives:
                if mimetype == 'text/html':
                    mail.content = Content("text/html", content)
        
        # Send email
        sg = SendGridAPIClient(self.api_key)
        response = sg.send(mail)
        
        # Check response
        if response.status_code not in [200, 201, 202]:
            raise Exception(f"SendGrid API error: {response.status_code} - {response.body}")
        
        return response