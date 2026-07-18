from django.core.management.base import BaseCommand
from marketplace.models import Producto, ProductActionLog

class Command(BaseCommand):
    help = 'Crea registros de publicación para productos existentes que no tengan uno.'

    def handle(self, *args, **options):
        created = 0
        skipped = 0
        for p in Producto.objects.all():
            exists = ProductActionLog.objects.filter(producto=p, accion__iexact='publicado').exists()
            if not exists:
                actor = p.vendedor if p.vendedor and p.vendedor.is_active else None
                if actor:
                    ProductActionLog.objects.create(producto=p, actor=actor, accion='publicado', fecha=p.fecha_creacion)
                    created += 1
                else:
                    skipped += 1
        self.stdout.write(self.style.SUCCESS(f'Created {created} publication logs, skipped {skipped} without actor.'))
