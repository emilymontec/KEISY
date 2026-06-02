from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Crea los roles predefinidos (Administrador, Médico, Analista)'

    def handle(self, *args, **kwargs):
        roles = ['Administrador', 'Medico', 'Analista']
        for role in roles:
            group, created = Group.objects.get_or_create(name=role)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Rol "{role}" creado correctamente'))
            else:
                self.stdout.write(self.style.WARNING(f'Rol "{role}" ya existe'))
