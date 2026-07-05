from io import BytesIO
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from django.http import HttpResponse

def generate_invoice_pdf(order):
    buffer = BytesIO()
    
    # Crear el documento PDF con márgenes
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    elements = []
    
    # Estilos de texto
    styles = getSampleStyleSheet()
    
    # Definir paleta de colores premium (Violeta oscuro, gris sofisticado)
    primary_color = colors.HexColor("#6d28d9")   # Violeta Oscuro
    secondary_color = colors.HexColor("#1f2937") # Gris Oscuro
    accent_color = colors.HexColor("#8b5cf6")    # Violeta Claro
    light_bg = colors.HexColor("#f3f4f6")        # Gris Claro
    text_muted = colors.HexColor("#4b5563")      # Gris Texto
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color
    )
    
    subtitle_style = ParagraphStyle(
        'InvoiceSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=text_muted
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=secondary_color
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=secondary_color
    )
    
    bold_style = ParagraphStyle(
        'BoldStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=secondary_color
    )

    right_align_style = ParagraphStyle(
        'RightAlignStyle',
        parent=normal_style,
        alignment=2 # Right align
    )
    
    right_align_bold_style = ParagraphStyle(
        'RightAlignBoldStyle',
        parent=bold_style,
        alignment=2 # Right align
    )

    # 1. ENCABEZADO DE LA EMPRESA (Dos columnas: Datos tienda y Título factura)
    header_data = [
        [
            Paragraph("<b>TIENDA URBANA PREMIUM</b><br/>Av. Mariscal López 1234<br/>Asunción, Paraguay<br/>Tel: +595 981 123456", normal_style),
            Paragraph("<b>FACTURA DE COMPRA</b><br/><font color='#6d28d9'><b>N° #ORD-{:06d}</b></font><br/>Fecha: {}<br/>Estado: PAGADO".format(order.id, order.created_at.strftime('%d/%m/%Y %H:%M')), right_align_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[260, 260])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    
    # Línea divisoria elegante
    divider = Table([[""]], colWidths=[520])
    divider.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 2, primary_color),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(divider)
    elements.append(Spacer(1, 15))
    
    # 2. DATOS DEL CLIENTE Y ENVÍO (Dos columnas)
    billing_data = [
        [
            Paragraph("<b>Cliente:</b>", heading_style),
            Paragraph("<b>Dirección de Envío:</b>", heading_style)
        ],
        [
            Paragraph(f"{order.first_name} {order.last_name}<br/>Email: {order.email}", normal_style),
            Paragraph(f"{order.address}<br/>{order.city}, {order.country}", normal_style)
        ]
    ]
    billing_table = Table(billing_data, colWidths=[260, 260])
    billing_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(billing_table)
    elements.append(Spacer(1, 20))
    
    # 3. TABLA DE ÍTEMS
    # Cabeceras
    items_data = [
        [
            Paragraph("<b>Producto / Variante</b>", bold_style),
            Paragraph("<b>Precio Unitario</b>", right_align_bold_style),
            Paragraph("<b>Cant.</b>", right_align_bold_style),
            Paragraph("<b>Subtotal</b>", right_align_bold_style)
        ]
    ]
    
    # Cargar ítems de la orden
    for item in order.items.all():
        variant_desc = f"<br/><font size='8' color='#4b5563'>Variante: {item.variant.color.name} / Talla {item.variant.size.name}</font>" if item.variant else ""
        prod_desc = f"<b>{item.product.name}</b>{variant_desc}"
        
        # Formatear montos en Gs.
        price_str = f"Gs. {item.price:,.0f}" if item.price >= 1000 else f"${item.price:.2f}"
        sub_str = f"Gs. {item.subtotal:,.0f}" if item.subtotal >= 1000 else f"${item.subtotal:.2f}"
        
        items_data.append([
            Paragraph(prod_desc, normal_style),
            Paragraph(price_str, right_align_style),
            Paragraph(str(item.quantity), right_align_style),
            Paragraph(sub_str, right_align_style)
        ])
        
    items_table = Table(items_data, colWidths=[260, 100, 50, 110])
    
    # Estilar tabla de productos
    t_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
    ])
    
    # Cambiar texto de cabecera a blanco
    for col_idx in range(4):
        items_data[0][col_idx].style.textColor = colors.white
        
    items_table.setStyle(t_style)
    elements.append(items_table)
    elements.append(Spacer(1, 15))
    
    # 4. RESUMEN DE TOTALES Y PAGOS (Dos columnas: Mensaje izquierda, Totales derecha)
    # Formatear totales
    subtotal_num = order.total_amount + order.discount_amount
    subtotal_str = f"Gs. {subtotal_num:,.0f}" if subtotal_num >= 1000 else f"${subtotal_num:.2f}"
    discount_str = f"Gs. -{order.discount_amount:,.0f}" if order.discount_amount >= 1000 else f"${order.discount_amount:.2f}"
    total_str = f"Gs. {order.total_amount:,.0f}" if order.total_amount >= 1000 else f"${order.total_amount:.2f}"
    
    # En Paraguay el IVA 10% está incluido
    iva_num = order.total_amount / Decimal("11")
    iva_str = f"Gs. {iva_num:,.0f}" if iva_num >= 1000 else f"${iva_num:.2f}"
    
    totals_data = [
        [Paragraph("Subtotal:", normal_style), Paragraph(subtotal_str, right_align_style)],
        [Paragraph("Descuento:", normal_style), Paragraph(discount_str, right_align_style)],
        [Paragraph("<b>Total General:</b>", bold_style), Paragraph(f"<b>{total_str}</b>", right_align_bold_style)],
        [Paragraph("<font size='8' color='#6b7280'>IVA Incluido (10%):</font>", normal_style), Paragraph(f"<font size='8' color='#6b7280'>{iva_str}</font>", right_align_style)],
    ]
    totals_table = Table(totals_data, colWidths=[110, 110])
    totals_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,2), (1,2), 1.5, primary_color),
    ]))
    
    payment_method_label = order.get_payment_method_display() or "Tarjeta de Crédito"
    payment_info_html = f"<b>Método de Pago:</b> {payment_method_label}<br/>"
    if order.payment_id:
        payment_info_html += f"<b>ID Transacción:</b> {order.payment_id}<br/>"
    payment_info_html += "<br/>Este documento sirve como comprobante de pago oficial para fines comerciales."
    
    summary_data = [
        [
            Paragraph(payment_info_html, normal_style),
            totals_table
        ]
    ]
    summary_table = Table(summary_data, colWidths=[300, 220])
    summary_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (1,0), (1,0), 30),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 40))
    
    # 5. PIE DE PAGINA (Gracias e información de devolución)
    elements.append(Paragraph("<center><b>¡GRACIAS POR ELEGIR TIENDA URBANA!</b></center>", heading_style))
    elements.append(Spacer(1, 5))
    elements.append(Paragraph("<center><font size='8' color='#6b7280'>Para cambios o devoluciones, contactanos dentro de los 30 días posteriores a tu compra con esta factura. Visitanos en www.tiendaurbana.com.py</font></center>", normal_style))
    
    # Construir el PDF
    doc.build(elements)
    
    # Obtener el contenido del buffer y retornar
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
