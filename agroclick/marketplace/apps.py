from django.apps import AppConfig
from django.db.models.signals import post_migrate


class MarketplaceConfig(AppConfig):
    name = 'marketplace'

    def ready(self):
        from django.contrib.auth.models import User
        from marketplace.models import Perfil

        def create_demo_users(sender, **kwargs):
            if sender.name != 'marketplace':
                return
            if User.objects.filter(username='admin').exists():
                return

            demo_users = [
                {
                    'username': 'admin',
                    'email': 'admin@example.com',
                    'password': 'admin123',
                    'is_staff': True,
                    'is_superuser': True,
                    'rol': 'admin',
                    'aprobado': True,
                },
                {
                    'username': 'vendedor1',
                    'email': 'vendedor1@example.com',
                    'password': 'vendedor123',
                    'is_staff': False,
                    'is_superuser': False,
                    'rol': 'vendedor',
                    'aprobado': True,
                },
                {
                    'username': 'comprador1',
                    'email': 'comprador1@example.com',
                    'password': 'comprador123',
                    'is_staff': False,
                    'is_superuser': False,
                    'rol': 'comprador',
                    'aprobado': True,
                },
            ]

            for data in demo_users:
                user, created = User.objects.get_or_create(
                    username=data['username'],
                    defaults={
                        'email': data['email'],
                        'is_staff': data['is_staff'],
                        'is_superuser': data['is_superuser'],
                    },
                )
                if created:
                    user.set_password(data['password'])
                    user.save()
                else:
                    user.email = data['email']
                    user.is_staff = data['is_staff']
                    user.is_superuser = data['is_superuser']
                    user.save()

                if data['rol'] == 'admin':
                    continue

                perfil, _ = Perfil.objects.get_or_create(usuario=user)
                perfil.rol = data['rol']
                perfil.aprobado = data['aprobado']
                perfil.save()

        post_migrate.connect(create_demo_users, sender=sender)
