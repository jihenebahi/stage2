from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from datetime import datetime, date, timedelta
from django.http import JsonResponse

from .models import Professeur, Salle, Groupe, Seance, Matiere
from .forms import ProfesseurForm, SalleForm, GroupeForm, SeanceForm
from django.utils import timezone
from django.utils import timezone 
from django.db.models import Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import io
from django.http import HttpResponse

from django.contrib.auth import logout
from django.shortcuts import redirect


import json


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
    """Liste des professeurs avec recherche, pagination et confirmation de suppression"""
    # Trier par id décroissant pour avoir le dernier ajouté en premier
    professeurs = Professeur.objects.all().select_related('matiere').order_by('-id')
    search = request.GET.get('search', '')
    
    if search:
        # Recherche par nom, prénom ET matière
        professeurs = professeurs.filter(
            Q(nom__icontains=search) | 
            Q(prenom__icontains=search) |
            Q(matiere__nom__icontains=search)
        )
    
    # Pagination : 7 professeurs par page
    paginator = Paginator(professeurs, 7)
    page = request.GET.get('page', 1)
    
    try:
        professeurs_page = paginator.page(page)
    except PageNotAnInteger:
        professeurs_page = paginator.page(1)
    except EmptyPage:
        professeurs_page = paginator.page(paginator.num_pages)
    
    return render(request, 'gestion-professeurs.html', {
        'professeurs': professeurs_page,
        'search': search,
        'total_count': professeurs.count()
    })

@login_required
def ajouter_professeur(request):
    """Ajouter un professeur avec validation améliorée"""
    if request.method == 'POST':
        form = ProfesseurForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✓ Professeur ajouté avec succès!')
            return redirect('professeurs')
        else:
            # Afficher les erreurs du formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'❌ {field}: {error}')
    else:
        form = ProfesseurForm()
    
    return render(request, 'gestion-professeurs-form.html', {
        'form': form, 
        'titre': 'Ajouter',
        'matieres': Matiere.objects.all()
    })

@login_required
def modifier_professeur(request, id):
    """Modifier un professeur avec validation améliorée"""
    professeur = get_object_or_404(Professeur, id=id)
    
    if request.method == 'POST':
        form = ProfesseurForm(request.POST, instance=professeur)
        if form.is_valid():
            form.save()
            messages.success(request, '✓ Professeur modifié avec succès!')
            return redirect('professeurs')
        else:
            # Afficher les erreurs du formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'❌ {field}: {error}')
    else:
        # Initialiser le formulaire avec les données du professeur
        form = ProfesseurForm(instance=professeur)
    
    return render(request, 'gestion-professeurs-form.html', {
        'form': form, 
        'titre': 'Modifier',
        'matieres': Matiere.objects.all()
    })

@login_required
def supprimer_professeur(request, id):
    """Supprimer un professeur (suppression AJAX)"""
    professeur = get_object_or_404(Professeur, id=id)
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            if professeur.groupes.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Impossible de supprimer: des groupes sont associés à ce professeur'
                })
            else:
                professeur.delete()
                return JsonResponse({
                    'success': True,
                    'message': '✓ Professeur supprimé avec succès'
                })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Requête invalide'})

@login_required
def liste_groupes(request):
    """Liste des groupes avec recherche en temps réel et pagination"""
    groupes = Groupe.objects.all().select_related('professeur', 'matiere').order_by('-id')
    search = request.GET.get('search', '')
    
    if search:
        # Recherche par nom du groupe, nom du professeur, matière
        groupes = groupes.filter(
            Q(nom__icontains=search) | 
            Q(professeur__nom__icontains=search) |
            Q(professeur__prenom__icontains=search) |
            Q(matiere__nom__icontains=search)
        ).distinct()
    
    # Pagination : 7 groupes par page
    paginator = Paginator(groupes, 7)
    page = request.GET.get('page', 1)
    
    try:
        groupes_page = paginator.page(page)
    except PageNotAnInteger:
        groupes_page = paginator.page(1)
    except EmptyPage:
        groupes_page = paginator.page(paginator.num_pages)
    
    return render(request, 'gestion-groupes.html', {
        'groupes': groupes_page,
        'search': search,
        'total_count': groupes.count()
    })

@login_required
def ajouter_groupe(request):
    """Ajouter un groupe avec validation améliorée"""
    if request.method == 'POST':
        form = GroupeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✓ Groupe ajouté avec succès!')
            return redirect('groupes')
        else:
            # Afficher les erreurs du formulaire de manière plus claire
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f'❌ {error}')
                    else:
                        messages.error(request, f'❌ {field}: {error}')
    else:
        form = GroupeForm()
    
    matieres = Matiere.objects.all()
    return render(request, 'gestion-groupes-form.html', {
        'form': form, 
        'titre': 'Ajouter',
        'matieres': matieres
    })

@login_required
def modifier_groupe(request, id):
    """Modifier un groupe avec validation améliorée"""
    groupe = get_object_or_404(Groupe, id=id)
    
    if request.method == 'POST':
        form = GroupeForm(request.POST, instance=groupe)
        if form.is_valid():
            form.save()
            messages.success(request, '✓ Groupe modifié avec succès!')
            return redirect('groupes')
        else:
            # Afficher les erreurs du formulaire de manière plus claire
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, f'❌ {error}')
                    else:
                        messages.error(request, f'❌ {field}: {error}')
            matieres = Matiere.objects.all()
            return render(request, 'gestion-groupes-form.html', {
                'form': form, 
                'titre': 'Modifier',
                'matieres': matieres
            })
    else:
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
def supprimer_groupe(request, id):
    """Supprimer un groupe (suppression AJAX)"""
    groupe = get_object_or_404(Groupe, id=id)
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            if groupe.seances.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Impossible de supprimer: des séances sont programmées pour ce groupe'
                })
            else:
                groupe.delete()
                return JsonResponse({
                    'success': True,
                    'message': '✓ Groupe supprimé avec succès'
                })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Requête invalide'})

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
def liste_salles(request):
    """Liste des salles avec recherche en temps réel et pagination"""
    salles = Salle.objects.all().order_by('-id')
    search = request.GET.get('search', '')
    
    if search:
        salles = salles.filter(nom__icontains=search)
    
    # Pagination : 7 salles par page
    paginator = Paginator(salles, 7)
    page = request.GET.get('page', 1)
    
    try:
        salles_page = paginator.page(page)
    except PageNotAnInteger:
        salles_page = paginator.page(1)
    except EmptyPage:
        salles_page = paginator.page(paginator.num_pages)
    
    return render(request, 'gestion-salles.html', {
        'salles': salles_page,
        'search': search,
        'total_count': salles.count()
    })

@login_required
def ajouter_salle(request):
    """Ajouter une salle avec validation améliorée"""
    if request.method == 'POST':
        form = SalleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✓ Salle ajoutée avec succès!')
            return redirect('salles')
        else:
            # Afficher les erreurs du formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'❌ {field}: {error}')
    else:
        form = SalleForm()
    
    return render(request, 'gestion-salles-form.html', {
        'form': form, 
        'titre': 'Ajouter'
    })

@login_required
def modifier_salle(request, id):
    """Modifier une salle avec validation améliorée"""
    salle = get_object_or_404(Salle, id=id)
    
    if request.method == 'POST':
        form = SalleForm(request.POST, instance=salle)
        if form.is_valid():
            form.save()
            messages.success(request, '✓ Salle modifiée avec succès!')
            return redirect('salles')
        else:
            # Afficher les erreurs du formulaire
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'❌ {field}: {error}')
    else:
        form = SalleForm(instance=salle)
    
    return render(request, 'gestion-salles-form.html', {
        'form': form, 
        'titre': 'Modifier'
    })

@login_required
def supprimer_salle(request, id):
    """Supprimer une salle (suppression AJAX)"""
    salle = get_object_or_404(Salle, id=id)
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            if salle.seances.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Impossible de supprimer: des séances sont programmées dans cette salle'
                })
            else:
                salle.delete()
                return JsonResponse({
                    'success': True,
                    'message': '✓ Salle supprimée avec succès'
                })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Requête invalide'})
@login_required


@login_required
def liste_seances(request):
    """Liste des séances avec filtre par date"""
    from datetime import datetime
    
    # Récupérer le filtre date
    date_filter = request.GET.get('date_filter', '')
    
    # Base de la requête triée par date
    seances = Seance.objects.all().select_related('groupe', 'salle', 'groupe__professeur').order_by('date', 'heure_debut')
    
    # Appliquer le filtre si une date est spécifiée
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            seances = seances.filter(date=filter_date)
        except ValueError:
            pass
    
    # Pagination
    paginator = Paginator(seances, 7)
    page = request.GET.get('page', 1)
    
    try:
        seances_page = paginator.page(page)
    except PageNotAnInteger:
        seances_page = paginator.page(1)
    except EmptyPage:
        seances_page = paginator.page(paginator.num_pages)
    
    return render(request, 'gestion-seances.html', {
        'seances': seances_page,
        'date_filter_value': date_filter,
        'total_count': seances.count(),
    })
from django.utils import timezone
from datetime import datetime, date, timedelta

@login_required
@login_required
@login_required
@login_required
def ajouter_seance(request):
    """Ajouter une séance avec vérification des conflits et solutions"""
    now = timezone.localtime()
    conflits = []
    solutions = []

    if request.method == 'POST':
        form = SeanceForm(request.POST)
        if form.is_valid():
            seance = form.save(commit=False)

            # Vérification date/heure passée
            if seance.date < date.today():
                conflits.append("❌ La date est déjà passée")
                solutions.append("📅 Proposez une date à partir de demain")
                solutions.append(f"📅 Suggestion: {(date.today() + timedelta(days=1)).strftime('%d/%m/%Y')}")
                
            elif seance.date == date.today() and seance.heure_debut <= now.time():
                conflits.append("❌ L'heure de début est déjà passée")
                heure_suggestion = (now + timedelta(hours=1)).strftime("%H:%M")
                heure_suggestion_fin = (now + timedelta(hours=2)).strftime("%H:%M")
                solutions.append(f"⏰ Proposez une heure après {heure_suggestion}")
                solutions.append(f"⏰ Suggestion: {heure_suggestion} - {heure_suggestion_fin}")
                
            else:
                # Vérifier les conflits
                conflits = seance.valider_seance()
                
                if conflits:
                    # Générer des solutions pour les autres conflits
                    solutions = generer_solutions(seance, conflits)
                else:
                    seance.save()
                    messages.success(request, '✓ Séance ajoutée avec succès!')
                    return redirect('seances')
        else:
            # Afficher les erreurs du formulaire sans le '__all__'
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        conflits.append(f"❌ {error}")
                    else:
                        conflits.append(f"❌ {field}: {error}")
    else:
        form = SeanceForm()

    return render(request, 'gestion-seances-form.html', {
        'form': form,
        'titre': 'Ajouter',
        'solutions': solutions,
        'conflits': conflits
    })


@login_required
def modifier_seance(request, id):
    """Modifier une séance avec vérification des conflits"""
    seance = get_object_or_404(Seance, id=id)
    now = timezone.localtime()
    conflits = []
    solutions = []

    if request.method == 'POST':
        form = SeanceForm(request.POST, instance=seance)
        if form.is_valid():
            seance_modifiee = form.save(commit=False)

            # Vérification date/heure passée
            if seance_modifiee.date < date.today():
                conflits.append("❌ La date est déjà passée")
                solutions.append("📅 Proposez une date à partir de demain")
                solutions.append(f"📅 Suggestion: {(date.today() + timedelta(days=1)).strftime('%d/%m/%Y')}")
                
            elif seance_modifiee.date == date.today() and seance_modifiee.heure_debut <= now.time():
                conflits.append("❌ L'heure de début est déjà passée")
                heure_suggestion = (now + timedelta(hours=1)).strftime("%H:%M")
                heure_suggestion_fin = (now + timedelta(hours=2)).strftime("%H:%M")
                solutions.append(f"⏰ Proposez une heure après {heure_suggestion}")
                solutions.append(f"⏰ Suggestion: {heure_suggestion} - {heure_suggestion_fin}")
                
            else:
                # Vérifier les conflits en excluant la séance actuelle
                conflits = seance_modifiee.valider_seance(exclude_id=id)
                
                if conflits:
                    # Générer des solutions
                    solutions = generer_solutions(seance_modifiee, conflits)
                else:
                    seance_modifiee.save()
                    messages.success(request, '✓ Séance modifiée avec succès!')
                    return redirect('seances')
        else:
            # Afficher les erreurs du formulaire sans le '__all__'
            for field, errors in form.errors.items():
                for error in errors:
                    if field == '__all__':
                        conflits.append(f"❌ {error}")
                    else:
                        conflits.append(f"❌ {field}: {error}")
    else:
        form = SeanceForm(instance=seance)

    return render(request, 'gestion-seances-form.html', {
        'form': form,
        'titre': 'Modifier',
        'solutions': solutions,
        'conflits': conflits
    })
def generer_solutions(seance, conflits):
    """Génère des solutions basées sur les conflits"""
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    solutions = []
    
    # Vérifier si le conflit est lié à la date/heure passée
    if any("date" in c.lower() or "passée" in c.lower() for c in conflits):
        now = timezone.localtime()
        solutions.append("📅 Proposez une date ultérieure (à partir de demain)")
        solutions.append(f"📅 Suggestion: {date.today() + timedelta(days=1)}")
        if "heure" in " ".join(conflits).lower():
            heure_suggestion = (now + timedelta(hours=1)).strftime("%H:%M")
            solutions.append(f"⏰ Suggestion d'heure: {heure_suggestion}")
        return solutions
    
    # Solution pour la salle
    if any("Salle" in c for c in conflits):
        salles_disponibles = Salle.objects.exclude(
            seances__date=seance.date,
            seances__heure_debut__lt=seance.heure_fin,
            seances__heure_fin__gt=seance.heure_debut
        ).filter(
            capacite__gte=seance.groupe.nombre_etudiants
        )
        if salles_disponibles.exists():
            solutions.append(
                f"🏢 Salles disponibles à cette date/heure : "
                f"{', '.join(s.nom for s in salles_disponibles[:5])}"
            )
    
    # Solution pour le professeur ou groupe
    if any("Professeur" in c or "Groupe" in c for c in conflits):
        # Proposer des dates alternatives dans les 7 prochains jours
        for delta in range(1, 8):
            futur_date = seance.date + timedelta(days=delta)
            
            # Vérifier si le créneau est disponible à cette date
            conflits_date = Seance.objects.filter(
                date=futur_date
            ).filter(
                Q(groupe=seance.groupe) | Q(groupe__professeur=seance.groupe.professeur)
            ).filter(
                Q(heure_debut__lt=seance.heure_fin, heure_fin__gt=seance.heure_debut)
            )
            
            if not conflits_date.exists():
                solutions.append(
                    f"📅 Le {futur_date.strftime('%d/%m/%Y')} à {seance.heure_debut.strftime('%H:%M')} - {seance.heure_fin.strftime('%H:%M')}, "
                    f"le groupe et le professeur sont libres"
                )
                break
        
        # Proposer des créneaux alternatifs dans la même journée
        creneaux = [("08:00", "10:00"), ("10:00", "12:00"), ("14:00", "16:00"), ("16:00", "18:00"), ("18:00", "20:00")]
        for debut, fin in creneaux:
            heure_debut_test = datetime.strptime(debut, "%H:%M").time()
            heure_fin_test = datetime.strptime(fin, "%H:%M").time()
            
            conflits_horaire = Seance.objects.filter(
                date=seance.date
            ).filter(
                Q(groupe=seance.groupe) | Q(groupe__professeur=seance.groupe.professeur)
            ).filter(
                Q(heure_debut__lt=heure_fin_test, heure_fin__gt=heure_debut_test)
            )
            
            if not conflits_horaire.exists():
                # Vérifier aussi la salle
                salle_dispo = Salle.objects.filter(
                    capacite__gte=seance.groupe.nombre_etudiants
                ).exclude(
                    seances__date=seance.date,
                    seances__heure_debut__lt=heure_fin_test,
                    seances__heure_fin__gt=heure_debut_test
                )
                
                if salle_dispo.exists():
                    solutions.append(
                        f"⏰ Le {seance.date.strftime('%d/%m/%Y')} à {debut} - {fin}, "
                        f"le groupe et le professeur sont libres"
                    )
                    break
    
    # Solution pour la capacité
    if any("Capacité" in c for c in conflits):
        salles_plus_grandes = Salle.objects.filter(
            capacite__gte=seance.groupe.nombre_etudiants
        ).exclude(
            seances__date=seance.date,
            seances__heure_debut__lt=seance.heure_fin,
            seances__heure_fin__gt=seance.heure_debut
        )[:5]
        
        if salles_plus_grandes.exists():
            solutions.append(
                f"🏢 Salles avec capacité suffisante : "
                f"{', '.join(s.nom for s in salles_plus_grandes)}"
            )
    
    return solutions
@login_required
def supprimer_seance(request, id):
    """Supprimer une séance (suppression AJAX)"""
    seance = get_object_or_404(Seance, id=id)
    
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            seance.delete()
            return JsonResponse({
                'success': True,
                'message': '✓ Séance supprimée avec succès'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Requête invalide'})

@login_required
def supprimer_seances_multiple(request):
    """Supprimer plusieurs séances sélectionnées"""
    if request.method == 'POST':
        ids = request.POST.get('ids', '')
        
        if ids:
            # Séparer les IDs par virgule et nettoyer
            ids_list = [id_val.strip() for id_val in ids.split(',') if id_val.strip()]
            
            try:
                # Convertir en entiers
                ids_int = [int(id_val) for id_val in ids_list]
                count = Seance.objects.filter(id__in=ids_int).count()
                
                if count > 0:
                    Seance.objects.filter(id__in=ids_int).delete()
                    messages.success(request, f'✓ {count} séance(s) supprimée(s) avec succès!')
                else:
                    messages.warning(request, '⚠ Aucune séance trouvée')
                    
            except ValueError as e:
                messages.error(request, f'❌ Erreur: IDs invalides')
            except Exception as e:
                messages.error(request, f'❌ Erreur lors de la suppression: {str(e)}')
        else:
            messages.error(request, '❌ Aucune séance sélectionnée')
    
    return redirect('seances')
@login_required
def emploi_par_salle(request):
    """Emploi du temps par salle"""
    from datetime import date, timedelta
    
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
    
    # Si pas de filtres de date, ne pas limiter
    # Trier par date
    seances = seances.order_by('date', 'heure_debut')
    
    # Compter les statistiques
    total_seances = seances.count()
    
    # Compter les séances passées
    today = date.today()
    seances_passees = 0
    for seance in seances:
        if seance.date < today:
            seances_passees += 1
    
    # Ajouter l'information si la séance est passée
    for seance in seances:
        seance.est_passee = seance.date < today
    
    # Récupérer la salle sélectionnée
    salle_selectionnee = None
    if salle_id:
        try:
            salle_selectionnee = Salle.objects.get(id=salle_id)
        except Salle.DoesNotExist:
            pass
    
    salles = Salle.objects.all()
    
    return render(request, 'emploi-par-salle.html', {
        'seances': seances,
        'salles': salles,
        'salle_selectionnee': salle_selectionnee,
        'salle_id': salle_id,
        'date_debut': date_debut or '',
        'date_fin': date_fin or '',
        'total_seances': total_seances,
        'seances_passees': seances_passees,
    })


@login_required
def emploi_par_professeur(request):
    """Emploi du temps par professeur"""
    from datetime import date
    
    professeur_id = request.GET.get('professeur')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    seances = Seance.objects.all()
    
    if professeur_id:
        seances = seances.filter(groupe__professeur_id=professeur_id)
    
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
    
    # Compter les séances passées
    today = date.today()
    seances_passees = 0
    for seance in seances:
        if seance.date < today:
            seances_passees += 1
    
    # Ajouter l'information si la séance est passée
    for seance in seances:
        seance.est_passee = seance.date < today
    
    professeurs = Professeur.objects.all()
    professeur_selectionne = None
    
    if professeur_id:
        try:
            professeur_selectionne = Professeur.objects.get(id=professeur_id)
        except Professeur.DoesNotExist:
            pass
    
    return render(request, 'emploi-par-professeur.html', {
        'seances': seances,
        'professeurs': professeurs,
        'professeur_selectionne': professeur_selectionne,
        'professeur_id': professeur_id,
        'date_debut': date_debut or '',
        'date_fin': date_fin or '',
        'total_seances': total_seances,
        'seances_passees': seances_passees,
    })


@login_required
def emploi_par_groupe(request):
    """Emploi du temps par groupe"""
    from datetime import date
    
    groupe_id = request.GET.get('groupe')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    
    seances = Seance.objects.all()
    
    if groupe_id:
        seances = seances.filter(groupe_id=groupe_id)
    
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
    
    # Compter les séances passées
    today = date.today()
    seances_passees = 0
    for seance in seances:
        if seance.date < today:
            seances_passees += 1
    
    # Ajouter l'information si la séance est passée
    for seance in seances:
        seance.est_passee = seance.date < today
    
    groupes = Groupe.objects.all()
    groupe_selectionne = None
    
    if groupe_id:
        try:
            groupe_selectionne = Groupe.objects.get(id=groupe_id)
        except Groupe.DoesNotExist:
            pass
    
    return render(request, 'emploi-par-groupe.html', {
        'seances': seances,
        'groupes': groupes,
        'groupe_selectionne': groupe_selectionne,
        'groupe_id': groupe_id,
        'date_debut': date_debut or '',
        'date_fin': date_fin or '',
        'total_seances': total_seances,
        'seances_passees': seances_passees,
    })
@login_required
def generer_pdf(request):
    """Générer PDF pour l'emploi du temps"""
    import io
    from datetime import datetime, date
    from django.http import HttpResponse
    from django.shortcuts import get_object_or_404
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    
    # Récupérer les paramètres
    type_view = request.GET.get('type', 'salle')
    element_id = request.GET.get('id')
    
    # Récupérer les séances selon le type (sans filtre de date)
    seances = Seance.objects.all()
    titre = ""
    sous_titre = ""
    
    if type_view == 'salle' and element_id:
        salle = get_object_or_404(Salle, id=element_id)
        seances = seances.filter(salle=salle)
        titre = f"Emploi du temps - Salle : {salle.nom}"
        sous_titre = f"Capacité : {salle.capacite} places"
    elif type_view == 'professeur' and element_id:
        professeur = get_object_or_404(Professeur, id=element_id)
        seances = seances.filter(groupe__professeur=professeur)
        titre = f"Emploi du temps - Professeur : {professeur.nom_complet}"
        sous_titre = f"Email : {professeur.email} | Tél : {professeur.telephone}"
    elif type_view == 'groupe' and element_id:
        groupe = get_object_or_404(Groupe, id=element_id)
        seances = seances.filter(groupe=groupe)
        titre = f"Emploi du temps - Groupe : {groupe.nom}"
        sous_titre = f"Professeur : {groupe.professeur.nom_complet} | Matière : {groupe.matiere.nom} | Élèves : {groupe.nombre_etudiants}"
    else:
        return HttpResponse("Paramètres invalides", status=400)
    
    # Trier les séances par date
    seances = seances.order_by('date', 'heure_debut')
    
    # Compter les séances
    total_seances = seances.count()
    
    # Compter les séances passées
    today = date.today()
    seances_passees = 0
    for seance in seances:
        if seance.date < today:
            seances_passees += 1
    
    # Créer le PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#0f1e33'),
        alignment=1,
        spaceAfter=20
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=1,
        spaceAfter=10
    )
    
    # Contenu
    story = []
    
    # Titre
    story.append(Paragraph(titre, title_style))
    story.append(Paragraph(sous_titre, subtitle_style))
    
    # Informations sur les séances
    info_text = f"Total : {total_seances} séance(s) | Passées : {seances_passees}"
    story.append(Paragraph(info_text, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Préparer les données du tableau
    if seances:
        # En-têtes
        data = [['Date', 'Heure', 'Groupe', 'Professeur', 'Salle', 'Matière']]
        
        # Données
        for seance in seances:
            statut = " (Passée)" if seance.date < today else ""
            data.append([
                seance.date.strftime('%d/%m/%Y') + statut,
                f"{seance.heure_debut.strftime('%H:%M')} - {seance.heure_fin.strftime('%H:%M')}",
                seance.groupe.nom,
                seance.groupe.professeur.nom_complet,
                seance.salle.nom,
                seance.groupe.matiere.nom
            ])
        
        # Créer le tableau
        table = Table(data, colWidths=[2.5*cm, 3*cm, 3*cm, 4*cm, 2.5*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f1e33')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        
        # Colorer les lignes des séances passées
        row_index = 1
        for seance in seances:
            if seance.date < today:
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#f8d7da')),
                    ('TEXTCOLOR', (0, row_index), (-1, row_index), colors.HexColor('#888888')),
                ]))
            row_index += 1
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Légende
        legend_text = "Légende : Les séances sur fond rouge sont passées"
        story.append(Paragraph(legend_text, styles['Italic']))
        
    else:
        story.append(Paragraph("Aucune séance trouvée.", styles['Normal']))
    
    # Pied de page
    story.append(Spacer(1, 30))
    story.append(Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Italic']))
    
    # Générer le PDF
    doc.build(story)
    
    # Retourner le PDF
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="emploi_du_temps_{type_view}_{element_id}.pdf"'
    return response
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
from django.contrib.auth import logout
from django.shortcuts import redirect

def logout_view(request):
    """Déconnexion personnalisée"""
    logout(request)
    return redirect('login')
