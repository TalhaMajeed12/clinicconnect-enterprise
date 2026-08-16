from flask import current_app
from html import escape
from email.message import EmailMessage
import smtplib

def send_email(subject, recipient, body_html):
    """Send an HTML email"""
    try:
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        if not sender:
            sender = current_app.config.get('MAIL_USERNAME')
            
        if not sender:
            print("❌ No sender email configured!")
            return False
        
        username = current_app.config.get('MAIL_USERNAME')
        password = current_app.config.get('MAIL_PASSWORD')
        if not username or not password:
            current_app.logger.warning('SMTP credentials are not configured')
            return False

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient
        msg.set_content('Open this message in an HTML-capable email client.')
        msg.add_alternative(body_html, subtype='html')

        timeout = current_app.config.get('MAIL_TIMEOUT', 10)
        with smtplib.SMTP(
            current_app.config.get('MAIL_SERVER', 'smtp.gmail.com'),
            current_app.config.get('MAIL_PORT', 587),
            timeout=timeout,
        ) as smtp:
            smtp.ehlo()
            if current_app.config.get('MAIL_USE_TLS', True):
                smtp.starttls()
                smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(msg)
        print(f"✅ Email sent successfully to {recipient}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")
        return False


def send_otp_email(recipient, otp_code, purpose="verification"):
    """Send OTP email"""
    subject = f"ClinicConnect - Your OTP for {purpose}"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2563eb; color: white; padding: 15px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ padding: 20px; background-color: #f8fafc; }}
            .otp {{ font-size: 32px; font-weight: bold; color: #2563eb; text-align: center; padding: 20px; letter-spacing: 5px; }}
            .footer {{ color: #64748b; font-size: 12px; margin-top: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🏥 ClinicConnect</h2>
            </div>
            <div class="content">
                <h3>Your OTP for {purpose}</h3>
                <p>Please use the following OTP to complete your {purpose}:</p>
                <div class="otp">{otp_code}</div>
                <p>This OTP expires in <strong>5 minutes</strong>.</p>
                <p>If you didn't request this, please ignore this email.</p>
            </div>
            <div class="footer">
                &copy; 2026 ClinicConnect. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(subject, recipient, body_html)


def send_appointment_confirmation(recipient, patient_name, doctor_name, appointment_date):
    """Send appointment confirmation email"""
    subject = "ClinicConnect - Appointment Confirmed!"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #16a34a; color: white; padding: 15px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ padding: 20px; background-color: #f8fafc; }}
            .details {{ background-color: white; padding: 15px; border-radius: 8px; }}
            .footer {{ color: #64748b; font-size: 12px; margin-top: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>✅ Appointment Confirmed!</h2>
            </div>
            <div class="content">
                <h3>Dear {patient_name},</h3>
                <p>Your appointment has been confirmed successfully.</p>
                <div class="details">
                    <p><strong>👨‍⚕️ Doctor:</strong> Dr. {doctor_name}</p>
                    <p><strong>📅 Date & Time:</strong> {appointment_date}</p>
                    <p><strong>💰 Fee:</strong> PKR 2,000 (PKR 500 paid as deposit)</p>
                </div>
                <p>Please arrive <strong>10 minutes</strong> before your scheduled time.</p>
                <p>For any changes, please contact us at least 24 hours in advance.</p>
            </div>
            <div class="footer">
                &copy; 2026 ClinicConnect. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(subject, recipient, body_html)


def send_password_reset_email(recipient, otp_code):
    """Send password reset email"""
    subject = "ClinicConnect - Password Reset Request"
    
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f59e0b; color: white; padding: 15px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ padding: 20px; background-color: #f8fafc; }}
            .otp {{ font-size: 32px; font-weight: bold; color: #f59e0b; text-align: center; padding: 20px; letter-spacing: 5px; }}
            .footer {{ color: #64748b; font-size: 12px; margin-top: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>🔐 Password Reset Request</h2>
            </div>
            <div class="content">
                <p>You requested to reset your password.</p>
                <p>Your OTP for password reset is:</p>
                <div class="otp">{otp_code}</div>
                <p>This OTP expires in <strong>5 minutes</strong>.</p>
                <p>If you didn't request this, please ignore this email.</p>
            </div>
            <div class="footer">
                &copy; 2026 ClinicConnect. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(subject, recipient, body_html) 


def send_password_reset_link(recipient, reset_url):
    """Send a single-use password reset link without logging its token."""
    safe_url = escape(reset_url, quote=True)
    body_html = f"""
    <!DOCTYPE html>
    <html><body style="font-family: Arial, sans-serif;">
      <div style="max-width: 600px; margin: auto; padding: 20px;">
        <h2>ClinicConnect password reset</h2>
        <p>A password reset was requested for your account.</p>
        <p><a href="{safe_url}">Reset your password</a></p>
        <p>This single-use link expires in 30 minutes.</p>
        <p>If you did not request this, ignore this email.</p>
      </div>
    </body></html>
    """
    return send_email('ClinicConnect - Reset your password', recipient, body_html)
