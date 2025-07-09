import json
from django.core.management.base import BaseCommand
from locations.models import Country, State, City
from django.db import transaction

class Command(BaseCommand):
    help = 'Carga datos geográficos de Argentina (País, Provincias y algunas Localidades)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando carga de datos geográficos de Argentina...'))

        argentina_data = {
            "name": "Argentina",
            "states": [
                {
                    "name": "Buenos Aires",
                    "cities": ["La Plata", "Mar del Plata", "Bahía Blanca", "San Nicolás de los Arroyos", "Quilmes", "Tigre", "San Isidro", "Avellaneda", "Lanús", "Lomas de Zamora", "Almirante Brown", "Esteban Echeverría", "Ezeiza", "Florencio Varela", "General San Martín", "Hurlingham", "Ituzaingó", "José C. Paz", "La Matanza", "Malvinas Argentinas", "Merlo", "Moreno", "Morón", "Pilar", "Presidente Perón", "San Fernando", "San Miguel", "Tres de Febrero", "Vicente López", "Berazategui", "Ensenada", "Berisso", "Campana", "Zárate", "Chascomús", "Dolores", "Junín", "Mercedes", "Necochea", "Olavarría", "Pergamino", "Tandil", "Azul"]
                },
                {
                    "name": "Catamarca",
                    "cities": ["San Fernando del Valle de Catamarca", "Belén", "Andalgalá", "Santa María", "Tinogasta"]
                },
                {
                    "name": "Chaco",
                    "cities": ["Resistencia", "Presidencia Roque Sáenz Peña", "Barranqueras", "Villa Ángela", "Fontana"]
                },
                {
                    "name": "Chubut",
                    "cities": ["Rawson", "Comodoro Rivadavia", "Puerto Madryn", "Trelew", "Esquel"]
                },
                {
                    "name": "Ciudad Autónoma de Buenos Aires",
                    "cities": ["Ciudad Autónoma de Buenos Aires"] # CABA es tanto provincia (jurisdicción) como ciudad
                },
                {
                    "name": "Córdoba",
                    "cities": ["Córdoba", "Río Cuarto", "Villa María", "San Francisco", "Villa Carlos Paz", "Alta Gracia", "Jesús María", "Bell Ville", "Marcos Juárez", "La Falda", "Cosquín"]
                },
                {
                    "name": "Corrientes",
                    "cities": ["Corrientes", "Goya", "Paso de los Libres", "Curuzú Cuatiá", "Mercedes"]
                },
                {
                    "name": "Entre Ríos",
                    "cities": ["Paraná", "Concordia", "Gualeguaychú", "Concepción del Uruguay", "Villaguay"]
                },
                {
                    "name": "Formosa",
                    "cities": ["Formosa", "Clorinda", "Pirané", "El Colorado", "Las Lomitas"]
                },
                {
                    "name": "Jujuy",
                    "cities": ["San Salvador de Jujuy", "San Pedro de Jujuy", "La Quiaca", "Palpalá", "Libertador General San Martín"]
                },
                {
                    "name": "La Pampa",
                    "cities": ["Santa Rosa", "General Pico", "Toay", "Realicó", "Eduardo Castex"]
                },
                {
                    "name": "La Rioja",
                    "cities": ["La Rioja", "Chilecito", "Aimogasta", "Chamical", "Chepes"]
                },
                {
                    "name": "Mendoza",
                    "cities": ["Mendoza", "San Rafael", "Godoy Cruz", "Las Heras", "Maipú", "Luján de Cuyo", "Guaymallén", "General Alvear", "Malargüe", "Tunuyán", "San Martín"]
                },
                {
                    "name": "Misiones",
                    "cities": ["Posadas", "Oberá", "Eldorado", "Puerto Iguazú", "Apóstoles"]
                },
                {
                    "name": "Neuquén",
                    "cities": ["Neuquén", "Cutral Có", "Plaza Huincul", "Centenario", "San Martín de los Andes", "Zapala", "Villa La Angostura"]
                },
                {
                    "name": "Río Negro",
                    "cities": ["Viedma", "San Carlos de Bariloche", "General Roca", "Cipolletti", "Villa Regina"]
                },
                {
                    "name": "Salta",
                    "cities": ["Salta", "San Ramón de la Nueva Orán", "Tartagal", "General Güemes", "Cafayate"]
                },
                {
                    "name": "San Juan",
                    "cities": ["San Juan", "Rawson (San Juan)", "Chimbas", "Rivadavia (San Juan)", "Santa Lucía (San Juan)", "Caucete", "Pocito"]
                },
                {
                    "name": "San Luis",
                    "cities": ["San Luis", "Villa Mercedes", "Merlo (San Luis)", "La Punta", "Justo Daract"]
                },
                {
                    "name": "Santa Cruz",
                    "cities": ["Río Gallegos", "Caleta Olivia", "Pico Truncado", "Las Heras (Santa Cruz)", "El Calafate"]
                },
                {
                    "name": "Santa Fe",
                    "cities": ["Santa Fe de la Vera Cruz", "Rosario", "Venado Tuerto", "Rafaela", "Reconquista", "Santo Tomé", "Villa Gobernador Gálvez", "San Lorenzo"]
                },
                {
                    "name": "Santiago del Estero",
                    "cities": ["Santiago del Estero", "La Banda", "Termas de Río Hondo", "Añatuya", "Frías"]
                },
                {
                    "name": "Tierra del Fuego, Antártida e Islas del Atlántico Sur",
                    "cities": ["Ushuaia", "Río Grande", "Tolhuin"]
                },
                {
                    "name": "Tucumán",
                    "cities": ["San Miguel de Tucumán", "Yerba Buena", "Concepción (Tucumán)", "Tafí Viejo", "Banda del Río Salí"]
                }
            ]
        }

        try:
            with transaction.atomic():
                country, created = Country.objects.get_or_create(name=argentina_data["name"])
                if created:
                    self.stdout.write(self.style.SUCCESS(f'País "{country.name}" creado.'))
                else:
                    self.stdout.write(self.style.WARNING(f'País "{country.name}" ya existe.'))

                for state_data in argentina_data["states"]:
                    state, state_created = State.objects.get_or_create(
                        country=country,
                        name=state_data["name"]
                    )
                    if state_created:
                        self.stdout.write(self.style.SUCCESS(f'  Provincia "{state.name}" creada.'))
                    else:
                        self.stdout.write(self.style.WARNING(f'  Provincia "{state.name}" ya existe.'))

                    for city_name in state_data["cities"]:
                        city, city_created = City.objects.get_or_create(
                            state=state,
                            name=city_name
                        )
                        if city_created:
                            self.stdout.write(self.style.SUCCESS(f'    Ciudad "{city.name}" creada.'))
                        # else:
                            # self.stdout.write(self.style.WARNING(f'    Ciudad "{city.name}" ya existe en {state.name}.'))
            
            self.stdout.write(self.style.SUCCESS('Carga de datos de Argentina finalizada con éxito.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error durante la carga de datos: {e}'))
            # Considerar borrar datos si falla en medio de una transacción no atómica,
            # pero con transaction.atomic() esto se maneja automáticamente.

        self.stdout.write(self.style.NOTICE('Para ejecutar este comando, usa: python manage.py load_argentina_data'))
