from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, date, timedelta
from django.http import JsonResponse

from .models import Professeur, Salle, Groupe, Seance, Matiere
from .forms import ProfesseurForm, SalleForm, GroupeForm, SeanceForm
from django.utils import timezone
from django.db.models import Count


@login_required
def dashboard(request):
    today = timezone.localdate()

    # Séances d'aujourd'hui (pour "Emploi d'aujourd'hui")
    seances_today = Seance.objects.select_related(
        'groupe__professeur',
        'groupe__matiere',
        'salle'
    ).filter(date=today).order_by('heure_debut')

    # Statistiques pour graphiques
    salles_stats = Salle.objects.annotate(
        total_seances=Count('seances')
    ).order_by('-total_seances')

    prof_stats = Professeur.objects.annotate(
        total_seances=Count('groupes__seances')
    ).order_by('-total_seances')

    groupe_stats = Groupe.objects.annotate(
        total_seances=Count('seances')
    ).order_by('-total_seances')[:6]  # Top 6 groupes

    
    # Courbe : séances par jour (uniquement jours programmés à partir d'aujourd'hui)
    seances_futures = Seance.objects.filter(date__gte=today) \
                                      .values('date') \
                                      .annotate(nb_seances=Count('id')) \
                                      .order_by('date')
    dates_futures = [s['date'].strftime('%d/%m') for s in seances_futures]
    nb_seances_futures = [s['nb_seances'] for s in seances_futures]

    return render(request, 'dashboard.html', {
        'seances_today': seances_today,
        'salles_stats': salles_stats,
        'prof_stats': prof_stats,
        'groupe_stats': groupe_stats,
        'dates_futures': dates_futures,
        'nb_seances_futures': nb_seances_futures,
    })

@login_required
def liste_professeurs(request):
    """Liste des professeurs avec recherche par nom, prénom et matière"""
    professeurs = Professeur.objects.all().select_related('matiere')
    search = request.GET.get('search', '')
    
    if search:
        # Recherche par nom, prénom ET matière
        professeurs = professeurs.filter(
            Q(nom__icontains=search) | 
            Q(prenom__icontains=search) |
            Q(matiere__nom__icontains=search)
        )
    
    return render(request, 'gestion-professeurs.html', {
        'professeurs': professeurs,
        'search': search
    })




@login_required
def ajouter_professeur(request):
    """Ajouter un professeur"""
    if request.method == 'POST':
        form = ProfesseurForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Professeur ajouté avec succès!')
            return redirect('professeurs')
    else:
        form = ProfesseurForm()
    
    return render(request, 'gestion-professeurs-form.html', {
        'form': form, 
        'titre': 'Ajouter',
        'matieres': Matiere.objects.all()
    })

@login_required
def modifier_professeur(request, id):
    """Modifier un professeur"""
    professeur = get_object_or_404(Professeur, id=id)
    
    if request.method == 'POST':
        form = ProfesseurForm(request.POST, instance=professeur)
        if form.is_valid():
            form.save()
            messages.success(request, 'Professeur modifié avec succès!')
            return redirect('professeurs')
    else:
        # Initialiser le formulaire avec les données du professeur
        initial_data = {
            'nom': professeur.nom,
            'prenom': professeur.prenom,
            'email': professeur.email,
            'telephone': professeur.telephone,
            'matiere': professeur.matiere.id if professeur.matiere else None
        }
        form = ProfesseurForm(instance=professeur, initial=initial_data)
    
    return render(request, 'gestion-professeurs-form.html', {
        'form': form, 
        'titre': 'Modifier',
        'matieres': Matiere.objects.all()
    })

@login_required
def supprimer_professeur(request, id):
    """Supprimer un professeur"""
    professeur = get_object_or_404(Professeur, id=id)
    if professeur.groupes.exists():
        messages.error(request, 'Impossible de supprimer: des groupes sont associés')
    else:
        professeur.delete()
        messages.success(request, 'Professeur supprimé')
    return redirect('professeurs')

@login_required
def liste_groupes(request):
    """Liste des groupes"""
    groupes = Groupe.objects.all().select_related('professeur', 'matiere')
    search = request.GET.get('search', '')
    
    if search:
        # Créer un Q object combiné pour le nom complet du professeur
        search_query = (
            Q(nom__icontains=search) | 
            Q(matiere__nom__icontains=search) |
            Q(professeur__nom__icontains=search) |
            Q(professeur__prenom__icontains=search) |
            Q(professeur__nom__icontains=search.split()[0])  # Premier mot comme nom
        )
        
        # Si la recherche contient un espace, essayer de combiner nom et prénom
        if ' ' in search:
            parts = search.split()
            if len(parts) >= 2:
                search_query |= Q(professeur__nom__icontains=parts[0]) & Q(professeur__prenom__icontains=parts[1])
        
        groupes = groupes.filter(search_query).distinct()
    
    return render(request, 'gestion-groupes.html', {
        'groupes': groupes,
        'search': search
    })

@login_required
def ajouter_groupe(request):
    """Ajouter un groupe"""
    if request.method == 'POST':
        form = GroupeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Groupe ajouté avec succès!')
            return redirect('groupes')
    else:
        form = GroupeForm()
    
    # Ajoutez toutes les matières au contexte pour le chargement initial
    matieres = Matiere.objects.all()
    return render(request, 'gestion-groupes-form.html', {
        'form': form, 
        'titre': 'Ajouter',
        'matieres': matieres
    })

@login_required
def modifier_groupe(request, id):
    """Modifier un groupe"""
    groupe = get_object_or_404(Groupe, id=id)
    
    if request.method == 'POST':
        form = GroupeForm(request.POST, instance=groupe)
        if form.is_valid():
            form.save()
            messages.success(request, 'Groupe modifié avec succès!')
            return redirect('groupes')
        else:
            # Si le formulaire est invalide, on passe quand même les matières
            matieres = Matiere.objects.all()
            return render(request, 'gestion-groupes-form.html', {
                'form': form, 
                'titre': 'Modifier',
                'matieres': matieres
            })
    else:
        # Mode GET - pré-remplir le formulaire
        form = GroupeForm(instance=groupe)
        
        # Forcer la mise à jour du queryset de matière
        if groupe.professeur and groupe.professeur.matiere:
            form.fields['matiere'].queryset = Matiere.objects.filter(id=groupe.professeur.matiere.id)
            form.fields['matiere'].initial = groupe.matiere
    
    matieres = Matiere.objects.all()
    return render(request, 'gestion-groupes-form.html', {
        'form': form, 
        'titre': 'Modifier',
        'matieres': matieres
    })

@login_required
def get_matieres_professeur(request, professeur_id):
    """API pour récupérer la matière d'un professeur"""
    try:
        professeur = Professeur.objects.get(id=professeur_id)
        if professeur.matiere:
            data = [{"id": professeur.matiere.id, "nom": professeur.matiere.nom}]
        else:
            data = []
        return JsonResponse(data, safe=False)
    except Professeur.DoesNotExist:
        return JsonResponse([], safe=False)
    
@login_required
def supprimer_groupe(request, id):
    """Supprimer un groupe"""
    groupe = get_object_or_404(Groupe, id=id)
    if groupe.seances.exists():
        messages.error(request, 'Impossible de supprimer: des séances sont programmées')
    else:
        groupe.delete()
        messages.success(request, 'Groupe supprimé')
    return redirect('groupes')

@login_required
def liste_salles(request):
    """Liste des salles"""
    salles = Salle.objects.all()
    search = request.GET.get('search', '')
    if search:
        salles = salles.filter(nom__icontains=search)
    return render(request, 'gestion-salles.html', {'salles': salles, 'search': search})

@login_required
def ajouter_salle(request):
    """Ajouter une salle"""
    if request.method == 'POST':
        form = SalleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salle ajoutée avec succès!')
            return redirect('salles')
    else:
        form = SalleForm()
    return render(request, 'gestion-salles-form.html', {'form': form, 'titre': 'Ajouter'})

@login_required
def modifier_salle(request, id):
    """Modifier une salle"""
    salle = get_object_or_404(Salle, id=id)
    if request.method == 'POST':
        form = SalleForm(request.POST, instance=salle)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salle modifiée avec succès!')
            return redirect('salles')
    else:
        form = SalleForm(instance=salle)
    return render(request, 'gestion-salles-form.html', {'form': form, 'titre': 'Modifier'})

@login_required
def supprimer_salle(request, id):
    """Supprimer une salle"""
    salle = get_object_or_404(Salle, id=id)
    if salle.seances.exists():
        messages.error(request, 'Impossible de supprimer: des séances sont programmées')
    else:
        salle.delete()
        messages.success(request, 'Salle supprimée')
    return redirect('salles')

@login_required
def liste_seances(request):
    """Liste des séances (suppression auto des séances passées)"""
    for seance in Seance.objects.all():
        if seance.est_passee():
            seance.delete()

    seances = Seance.objects.all()
    return render(request, 'gestion-seances.html', {
        'seances': seances
    })


@login_required
def ajouter_seance(request):
    from datetime import datetime
    from django.utils import timezone

    now = timezone.localtime()  # Heure actuelle locale

    if request.method == 'POST':
        form = SeanceForm(request.POST)
        if form.is_valid():
            seance = form.save(commit=False)
            
            # Vérification date + heure déjà passée
            if seance.date == date.today() and seance.heure_debut <= now.time():
                messages.error(request, "Impossible d'ajouter une séance avec une heure déjà passée.")
            elif seance.date < date.today():
                messages.error(request, "Impossible d'ajouter une séance dans le passé.")
            else:
                conflits = seance.valider_seance()
                if conflits:
                    for conflit in conflits:
                        messages.error(request, conflit)
                else:
                    seance.save()
                    messages.success(request, 'Séance ajoutée avec succès')
                    return redirect('seances')
    else:
        form = SeanceForm()

    return render(request, 'gestion-seances-form.html', {
        'form': form,
        'titre': 'Ajouter'
    })



@login_required
def modifier_seance(request, id):
    from datetime import date
    from django.utils import timezone

    seance = get_object_or_404(Seance, id=id)
    now = timezone.localtime()  # Heure actuelle locale

    if request.method == 'POST':
        form = SeanceForm(request.POST, instance=seance)
        if form.is_valid():
            seance_modifiee = form.save(commit=False)

            # Vérification si date/heure est déjà passée
            if seance_modifiee.date < date.today():
                messages.error(request, "Impossible de modifier une séance dans le passé.")
            elif seance_modifiee.date == date.today() and seance_modifiee.heure_debut <= now.time():
                messages.error(request, "Impossible de modifier une séance avec une heure déjà passée.")
            else:
                # Vérification des conflits
                conflits = seance_modifiee.valider_seance()
                if conflits:
                    for conflit in conflits:
                        messages.error(request, conflit)
                else:
                    seance_modifiee.save()
                    messages.success(request, 'Séance modifiée avec succès')
                    return redirect('seances')
    else:
        form = SeanceForm(instance=seance)

    return render(request, 'gestion-seances-form.html', {
        'form': form,
        'titre': 'Modifier'
    })


@login_required
def supprimer_seance(request, id):
    seance = get_object_or_404(Seance, id=id)
    seance.delete()
    messages.success(request, 'Séance supprimée')
    return redirect('seances')

@login_required
def emploi_par_salle(request):
    """Emploi du temps par salle - version finale sans filtres personnalisés"""
    salle_id = request.GET.get('salle')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    # Filtrer les séances
    seances = Seance.objects.all()
    
    if salle_id:
        seances = seances.filter(salle_id=salle_id)
    
    if date_debut:
        try:
            seances = seances.filter(date__gte=date_debut)
        except ValueError:
            pass
    
    if date_fin:
        try:
            seances = seances.filter(date__lte=date_fin)
        except ValueError:
            pass
    
    # Trier par date
    seances = seances.order_by('date', 'heure_debut')
    
    # Compter les statistiques
    total_seances = seances.count()
    
    # Récupérer la salle sélectionnée
    salle_selectionnee = None
    if salle_id:
        try:
            salle_selectionnee = Salle.objects.get(id=salle_id)
        except Salle.DoesNotExist:
            pass
    
    salles = Salle.objects.all()
    
    # Dates par défaut
    if not date_debut:
        date_debut = date.today().strftime('%Y-%m-%d')
    if not date_fin:
        date_fin = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    return render(request, 'emploi-par-salle.html', {
        'seances': seances,
        'salles': salles,
        'salle_selectionnee': salle_selectionnee,
        'salle_id': salle_id,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_seances': total_seances,
    })

@login_required
def emploi_par_professeur(request):
    """Emploi du temps par professeur"""
    professeur_id = request.GET.get('professeur')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    seances = Seance.objects.all()
    
    if professeur_id:
        seances = seances.filter(groupe__professeur_id=professeur_id)
    
    if date_debut:
        seances = seances.filter(date__gte=date_debut)
    
    if date_fin:
        seances = seances.filter(date__lte=date_fin)
    
    # Compter les statistiques
    total_seances = seances.count()
    
    professeurs = Professeur.objects.all()
    professeur_selectionne = None
    
    if professeur_id:
        try:
            professeur_selectionne = Professeur.objects.get(id=professeur_id)
        except Professeur.DoesNotExist:
            pass
    
    # Dates par défaut
    if not date_debut:
        date_debut = date.today().strftime('%Y-%m-%d')
    if not date_fin:
        date_fin = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    return render(request, 'emploi-par-professeur.html', {
        'seances': seances.order_by('date', 'heure_debut'),
        'professeurs': professeurs,
        'professeur_selectionne': professeur_selectionne,
        'professeur_id': professeur_id,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_seances': total_seances,
    })

@login_required
def emploi_par_groupe(request):
    """Emploi du temps par groupe"""
    groupe_id = request.GET.get('groupe')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    seances = Seance.objects.all()
    
    if groupe_id:
        seances = seances.filter(groupe_id=groupe_id)
    
    if date_debut:
        seances = seances.filter(date__gte=date_debut)
    
    if date_fin:
        seances = seances.filter(date__lte=date_fin)
    
    # Compter les statistiques
    total_seances = seances.count()
    
    groupes = Groupe.objects.all()
    groupe_selectionne = None
    
    if groupe_id:
        try:
            groupe_selectionne = Groupe.objects.get(id=groupe_id)
        except Groupe.DoesNotExist:
            pass
    
    # Dates par défaut
    if not date_debut:
        date_debut = date.today().strftime('%Y-%m-%d')
    if not date_fin:
        date_fin = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    return render(request, 'emploi-par-groupe.html', {
        'seances': seances.order_by('date', 'heure_debut'),
        'groupes': groupes,
        'groupe_selectionne': groupe_selectionne,
        'groupe_id': groupe_id,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'total_seances': total_seances,
    })

@login_required
def generer_pdf(request):
    """Générer PDF (simplifié pour l'instant)"""
    from django.http import HttpResponse
    return HttpResponse("Fonction PDF à implémenter")


from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):
    """Déconnexion personnalisée"""
    logout(request)
    return redirect('login')

from django.shortcuts import render
from django.utils import timezone
from .models import Seance  # ton modèle des séances

def emploi_today(request):
    today = timezone.localdate()
    seances_today = Seance.objects.select_related(
        'groupe__professeur',
        'groupe__matiere',
        'salle'
    ).filter(date=today).order_by('heure_debut')

    return render(request, 'emploi_today.html', {
        'seances_today': seances_today,
        'today': today
    })

