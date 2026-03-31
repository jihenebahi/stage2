from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Professeur, Salle, Groupe, Seance, Matiere
import re
from datetime import date
from django.core.exceptions import ValidationError
from django.utils import timezone


class ProfesseurForm(forms.ModelForm):
    class Meta:
        model = Professeur
        fields = ['nom', 'prenom', 'email', 'telephone']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'prenom': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    matiere = forms.ModelChoiceField(
        queryset=Matiere.objects.all(),
        required=True,
        label="Matière",
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Choisir une matière"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and hasattr(self.instance, 'matiere'):
            self.fields['matiere'].initial = self.instance.matiere
    
    def clean_nom(self):
        nom = self.cleaned_data.get('nom')
        if not nom:
            raise ValidationError("Champ obligatoire")
        
        if not re.match(r'^[A-Za-zÀ-ÿ\s\'-]+$', nom):
            raise ValidationError("Seulement des lettres autorisées")
        
        return nom.strip().title()
    
    def clean_prenom(self):
        prenom = self.cleaned_data.get('prenom')
        if not prenom:
            raise ValidationError("Champ obligatoire")
        
        if not re.match(r'^[A-Za-zÀ-ÿ\s\'-]+$', prenom):
            raise ValidationError("Seulement des lettres autorisées")
        
        return prenom.strip().title()
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("Champ obligatoire")
        
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            raise ValidationError("Format email invalide")
        
        professeur_id = self.instance.id if self.instance else None
        if Professeur.objects.filter(email=email).exclude(id=professeur_id).exists():
            raise ValidationError("Cet email est déjà utilisé")
        
        return email.lower()
    
    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone')
        if not telephone:
            raise ValidationError("Champ obligatoire")
        
        telephone = re.sub(r'[\s\-\.]', '', telephone)
        
        tunisian_phone_regex = r'^(?:\+216|00216|216)?([2-9][0-9]{7})$'
        match = re.match(tunisian_phone_regex, telephone)
        
        if not match:
            raise ValidationError("Format téléphone tunisien invalide")
        
        normalized = f"+216{match.group(1)}"
        
        professeur_id = self.instance.id if self.instance else None
        if Professeur.objects.filter(telephone=normalized).exclude(id=professeur_id).exists():
            raise ValidationError("Ce numéro est déjà utilisé")
        
        return normalized
    
    def clean_matiere(self):
        matiere = self.cleaned_data.get('matiere')
        if not matiere:
            raise ValidationError("Champ obligatoire")
        return matiere
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        matiere = self.cleaned_data.get('matiere')
        
        if commit:
            instance.save()
            instance.matiere = matiere
            instance.save()
        
        return instance

class SalleForm(forms.ModelForm):
    class Meta:
        model = Salle
        fields = ['nom', 'capacite']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'capacite': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
    
    def clean_nom(self):
        nom = self.cleaned_data.get('nom')
        if not nom:
            raise ValidationError("Champ obligatoire")
        
        # Vérifier l'unicité
        salle_id = self.instance.id if self.instance else None
        if Salle.objects.filter(nom=nom).exclude(id=salle_id).exists():
            raise ValidationError("Une salle avec ce nom existe déjà")
        
        return nom.strip()
    
    def clean_capacite(self):
        capacite = self.cleaned_data.get('capacite')
        if not capacite:
            raise ValidationError("Champ obligatoire")
        
        if capacite < 1:
            raise ValidationError("La capacité doit être supérieure à 0")
        
        if capacite > 1000:
            raise ValidationError("La capacité ne peut pas dépasser 1000")
        
        return capacite



class GroupeForm(forms.ModelForm):
    class Meta:
        model = Groupe
        fields = ['nom', 'professeur', 'matiere', 'nombre_etudiants']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'professeur': forms.Select(attrs={'class': 'form-control'}),
            'matiere': forms.Select(attrs={'class': 'form-control'}),
            'nombre_etudiants': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrer les matières selon le professeur sélectionné
        if 'professeur' in self.data:
            try:
                professeur_id = int(self.data.get('professeur'))
                professeur = Professeur.objects.get(id=professeur_id)
                if professeur.matiere:
                    self.fields['matiere'].queryset = Matiere.objects.filter(id=professeur.matiere.id)
                else:
                    self.fields['matiere'].queryset = Matiere.objects.none()
            except (ValueError, TypeError, Professeur.DoesNotExist):
                self.fields['matiere'].queryset = Matiere.objects.none()
        elif self.instance and self.instance.pk:
            if self.instance.professeur and self.instance.professeur.matiere:
                self.fields['matiere'].queryset = Matiere.objects.filter(id=self.instance.professeur.matiere.id)
                self.fields['matiere'].initial = self.instance.matiere
            else:
                self.fields['matiere'].queryset = Matiere.objects.none()
        else:
            self.fields['matiere'].queryset = Matiere.objects.none()
    
    def clean_nom(self):
        nom = self.cleaned_data.get('nom')
        if not nom:
            raise ValidationError("Champ obligatoire")
        
        # Vérifier l'unicité du nom du groupe
        groupe_id = self.instance.id if self.instance else None
        if Groupe.objects.filter(nom=nom).exclude(id=groupe_id).exists():
            raise ValidationError("Un groupe avec ce nom existe déjà")
        
        return nom.strip()
    
    def clean_nombre_etudiants(self):
        nombre = self.cleaned_data.get('nombre_etudiants')
        if not nombre:
            raise ValidationError("Champ obligatoire")
        
        if nombre < 1:
            raise ValidationError("Le nombre d'étudiants doit être supérieur à 0")
        
        if nombre > 500:
            raise ValidationError("Le nombre d'étudiants ne peut pas dépasser 500")
        
        return nombre
    
    def clean_professeur(self):
        professeur = self.cleaned_data.get('professeur')
        if not professeur:
            raise ValidationError("Champ obligatoire")
        return professeur
    
    def clean_matiere(self):
        matiere = self.cleaned_data.get('matiere')
        if not matiere:
            raise ValidationError("Champ obligatoire")
        return matiere
    
    def clean(self):
        cleaned_data = super().clean()
        professeur = cleaned_data.get('professeur')
        matiere = cleaned_data.get('matiere')
        nom = cleaned_data.get('nom')
        
        # Vérifier que la matière appartient au professeur
        if professeur and matiere:
            if not professeur.matiere:
                raise ValidationError(
                    f"Le professeur {professeur.nom_complet} n'a pas de matière assignée"
                )
            if professeur.matiere != matiere:
                raise ValidationError(
                    f"Le professeur {professeur.nom_complet} enseigne uniquement: {professeur.matiere.nom}"
                )
        
        # Vérifier qu'un groupe avec le même nom n'existe pas pour ce professeur
        if professeur and nom:
            groupe_id = self.instance.id if self.instance else None
            if Groupe.objects.filter(nom=nom, professeur=professeur).exclude(id=groupe_id).exists():
                raise ValidationError(
                    f"Un groupe nommé '{nom}' existe déjà pour le professeur {professeur.nom_complet}"
                )
        
        return cleaned_data
class SeanceForm(forms.ModelForm):
    class Meta:
        model = Seance
        fields = ['groupe', 'salle', 'date', 'heure_debut', 'heure_fin']
        widgets = {
            'groupe': forms.Select(attrs={'class': 'form-control'}),
            'salle': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': date.today().isoformat()
            }),
            'heure_debut': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'heure_fin': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les groupes qui ont un professeur et une matière
        self.fields['groupe'].queryset = Groupe.objects.filter(professeur__isnull=False, matiere__isnull=False)
        # Filtrer les salles
        self.fields['salle'].queryset = Salle.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        date_seance = cleaned_data.get('date')
        heure_debut = cleaned_data.get('heure_debut')
        heure_fin = cleaned_data.get('heure_fin')
        groupe = cleaned_data.get('groupe')
        salle = cleaned_data.get('salle')

        now = timezone.localtime()

        # Vérification date passée
        if date_seance:
            if date_seance < date.today():
                raise ValidationError("Impossible d'ajouter une séance dans le passé.")
            if date_seance == date.today() and heure_debut and heure_debut <= now.time():
                raise ValidationError("Impossible d'ajouter une séance avec une heure déjà passée.")

        # Vérification heure
        if heure_debut and heure_fin:
            if heure_fin <= heure_debut:
                raise ValidationError("L'heure de fin doit être après l'heure de début.")
            
            # Vérifier la durée minimale (30 minutes)
            try:
                heure_debut_dt = datetime.combine(date.today(), heure_debut)
                heure_fin_dt = datetime.combine(date.today(), heure_fin)
                if (heure_fin_dt - heure_debut_dt).total_seconds() < 1800:
                    raise ValidationError("La durée minimale d'une séance est de 30 minutes.")
            except Exception:
                pass  # Ignorer si les heures ne sont pas valides

        return cleaned_data

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé")
        return email
