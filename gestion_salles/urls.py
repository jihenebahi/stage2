from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from emploi_du_temps import views

urlpatterns = [
    path('admin/', admin.site.urls),


    
    # Authentification

    path('', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
   path('logout/', views.logout_view, name='logout'), 
    
    # Dashboard et gestion
    path('dashbord/', views.dashboard, name='dashboard'),
    
    
    # Professeurs
    path('professeurs/', views.liste_professeurs, name='professeurs'),
    path('professeurs/ajouter/', views.ajouter_professeur, name='ajouter_professeur'),
    path('professeurs/modifier/<int:id>/', views.modifier_professeur, name='modifier_professeur'),
    path('professeurs/supprimer/<int:id>/', views.supprimer_professeur, name='supprimer_professeur'),

        path('professeurs/<int:professeur_id>/matieres/', views.get_matieres_professeur, name='professeur_matieres'),
    
    # Groupes
    path('groupes/', views.liste_groupes, name='groupes'),
    path('groupes/ajouter/', views.ajouter_groupe, name='ajouter_groupe'),
    path('groupes/modifier/<int:id>/', views.modifier_groupe, name='modifier_groupe'),
    path('groupes/supprimer/<int:id>/', views.supprimer_groupe, name='supprimer_groupe'),
    
    # Salles
    path('salles/', views.liste_salles, name='salles'),
    path('salles/ajouter/', views.ajouter_salle, name='ajouter_salle'),
    path('salles/modifier/<int:id>/', views.modifier_salle, name='modifier_salle'),
    path('salles/supprimer/<int:id>/', views.supprimer_salle, name='supprimer_salle'),
    
    # Séances
    path('seances/', views.liste_seances, name='seances'),
    path('seances/ajouter/', views.ajouter_seance, name='ajouter_seance'),
    path('seances/modifier/<int:id>/', views.modifier_seance, name='modifier_seance'),
    path('seances/supprimer/<int:id>/', views.supprimer_seance, name='supprimer_seance'),
    
    # Emplois du temps
    path('emplois/salle/', views.emploi_par_salle, name='emploi_salle'),
    path('emplois/professeur/', views.emploi_par_professeur, name='emploi_professeur'),
    path('emplois/groupe/', views.emploi_par_groupe, name='emploi_groupe'),
    path('emplois/export-pdf/', views.generer_pdf, name='export_pdf'),

    # Emploi d'aujourd'hui
    path('emplois/today/', views.emploi_today, name='emploi_today'),

]