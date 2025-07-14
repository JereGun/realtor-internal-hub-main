# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from weasyprint import HTML
import io

def send_invoice_email(invoice):
    """
    Genera y envía una factura por correo electrónico.
    """
    if not invoice.customer.email:
        raise ValueError("El cliente no tiene una dirección de correo electrónico.")

    # Generar el PDF en memoria
    html_string = render_to_string('accounting/invoice_pdf.html', {'invoice': invoice})
    html = HTML(string=html_string)
    pdf_file = html.write_pdf()

    # Crear el correo electrónico
    subject = f"Factura Nº {invoice.number}"
    body = "Adjuntamos la factura correspondiente."
    email = EmailMessage(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [invoice.customer.email]
    )

    # Adjuntar el PDF
    email.attach(f'factura_{invoice.number}.pdf', pdf_file, 'application/pdf')

    # Enviar el correo
    email.send()
