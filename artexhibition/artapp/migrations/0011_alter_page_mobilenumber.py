from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('artapp', '0010_alter_customuser_user_type_order_orderit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='page',
            name='mobilenumber',
            field=models.CharField(max_length=15, default='0'),
        ),
    ]