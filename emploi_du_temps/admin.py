from django.contrib import admin
from .models import Matiere, Professeur, Salle, Groupe, Seance

@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ['nom']
    search_fields = ['nom']

@admin.register(Professeur)
class ProfesseurAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'email', 'telephone', 'matiere_nom']
    list_filter = ['matiere']  # Changé de 'matieres' à 'matiere'
    search_fields = ['nom', 'prenom', 'email', 'matiere__nom']
    # Supprimé filter_horizontal car ce n'est plus un ManyToManyField
    
    def matiere_nom(self, obj):
        return obj.matiere.nom if obj.matiere else "Aucune matière"
    matiere_nom.short_description = 'Matière'
    matiere_nom.admin_order_field = 'matiere__nom'

@admin.register(Salle)
class SalleAdmin(admin.ModelAdmin):
    list_display = ['nom', 'capacite']
    list_filter = ['capacite']
    search_fields = ['nom']

@admin.register(Groupe)
class GroupeAdmin(admin.ModelAdmin):
    list_display = ['nom', 'professeur', 'matiere', 'nombre_etudiants']
    list_filter = ['professeur', 'matiere']
    search_fields = ['nom', 'professeur__nom', 'professeur__prenom', 'matiere__nom']

@admin.register(Seance)
class SeanceAdmin(admin.ModelAdmin):
    list_display = ['groupe', 'salle', 'date', 'heure_debut', 'heure_fin']
    list_filter = ['date', 'salle', 'groupe__professeur']
    search_fields = ['groupe__nom', 'salle__nom', 'groupe__professeur__nom']
    date_hierarchy = 'date'

