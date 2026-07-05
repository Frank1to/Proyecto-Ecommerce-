from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(blank=True, choices=[('stripe', 'Stripe'), ('mercadopago', 'MercadoPago')], max_length=20, null=True, verbose_name='Método de Pago'),
        ),
    ]
