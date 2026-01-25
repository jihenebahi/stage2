from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Professeur, Salle, Groupe, Seance, Matiere
import re
from datetime import date


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
    
    # Champ personnalisé pour la matière (une seule matière)
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
            # Pré-sélectionner la matière du professeur
            self.fields['matiere'].initial = self.instance.matiere
    
    def clean_nom(self):
        nom = self.cleaned_data.get('nom')
        if not nom:
            raise forms.ValidationError("Le nom est obligatoire")
        
        # Validation alphabétique (lettres, espaces, apostrophes, tirets)
        if not re.match(r'^[A-Za-zÀ-ÿ\s\'-]+$', nom):
            raise forms.ValidationError("Le nom ne doit contenir que des lettres, espaces, apostrophes ou tirets")
        
        return nom.strip().title()
    
    def clean_prenom(self):
        prenom = self.cleaned_data.get('prenom')
        if not prenom:
            raise forms.ValidationError("Le prénom est obligatoire")
        
        # Validation alphabétique
        if not re.match(r'^[A-Za-zÀ-ÿ\s\'-]+$', prenom):
            raise forms.ValidationError("Le prénom ne doit contenir que des lettres, espaces, apostrophes ou tirets")
        
        return prenom.strip().title()
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("L'email est obligatoire")
        
        # Validation format email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            raise forms.ValidationError("Format d'email invalide")
        
        # Vérifier si l'email existe déjà (sauf pour l'instance actuelle)
        professeur_id = self.instance.id if self.instance else None
        if Professeur.objects.filter(email=email).exclude(id=professeur_id).exists():
            raise forms.ValidationError("Cet email est déjà utilisé par un autre professeur")
        
        return email.lower()
    
    def clean_telephone(self):
        telephone = self.cleaned_data.get('telephone')
        if not telephone:
            raise forms.ValidationError("Le téléphone est obligatoire")
        
        # Nettoyer le numéro (supprimer espaces, tirets, points)
        telephone = re.sub(r'[\s\-\.]', '', telephone)
        
        # Validation numéro tunisien
        # Formats acceptés: +216XXXXXXXX, 00216XXXXXXXX, 216XXXXXXXX, XXXXXXXXX (9 chiffres)
        tunisian_phone_regex = r'^(?:\+216|00216|216)?([2-9][0-9]{7})$'
        match = re.match(tunisian_phone_regex, telephone)
        
        if not match:
            raise forms.ValidationError(
                "Numéro de téléphone tunisien invalide. Formats acceptés: "
                "+216XXXXXXXX, 00216XXXXXXXX, 216XXXXXXXX, ou XXXXXXXXX (9 chiffres)"
            )
        
        # Normaliser vers le format +216XXXXXXXX
        normalized = f"+216{match.group(1)}"
        
        # Vérifier l'unicité
        professeur_id = self.instance.id if self.instance else None
        if Professeur.objects.filter(telephone=normalized).exclude(id=professeur_id).exists():
            raise forms.ValidationError("Ce numéro de téléphone est déjà utilisé")
        
        return normalized
    
    def clean_matiere(self):
        matiere = self.cleaned_data.get('matiere')
        if not matiere:
            raise forms.ValidationError("Veuillez sélectionner une matière")
        return matiere
    
    def clean(self):
        cleaned_data = super().clean()
        # Validation supplémentaire si nécessaire
        return cleaned_data
    
    def save(self, commit=True):
        # Sauvegarder les champs de base
        instance = super().save(commit=False)
        
        # Récupérer la matière
        matiere = self.cleaned_data.get('matiere')
        
        if commit:
            instance.save()
            # Assigner la matière unique
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
            raise forms.ValidationError("Le nom de la salle est obligatoire")
        
        # Vérifier l'unicité
        salle_id = self.instance.id if self.instance else None
        if Salle.objects.filter(nom=nom).exclude(id=salle_id).exists():
            raise forms.ValidationError("Une salle avec ce nom existe déjà")
        
        return nom.strip().upper()
    
    def clean_capacite(self):
        capacite = self.cleaned_data.get('capacite')
        if not capacite:
            raise forms.ValidationError("La capacité est obligatoire")
        
        if capacite < 1:
            raise forms.ValidationError("La capacité doit être supérieure à 0")
        
        if capacite > 1000:
            raise forms.ValidationError("La capacité ne peut pas dépasser 1000")
        
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
                # Un seul professeur = une seule matière
                if professeur.matiere:
                    self.fields['matiere'].queryset = Matiere.objects.filter(id=professeur.matiere.id)
                else:
                    self.fields['matiere'].queryset = Matiere.objects.none()
            except (ValueError, TypeError, Professeur.DoesNotExist):
                self.fields['matiere'].queryset = Matiere.objects.none()
        elif self.instance and self.instance.pk:
            # Pour la modification, pré-sélectionner le professeur et sa matière
            if self.instance.professeur and self.instance.professeur.matiere:
                self.fields['matiere'].queryset = Matiere.objects.filter(id=self.instance.professeur.matiere.id)
                # Pré-sélectionner la matière du groupe
                self.fields['matiere'].initial = self.instance.matiere
            else:
                self.fields['matiere'].queryset = Matiere.objects.none()
        else:
            # Initialement, pas de matières sélectionnées
            self.fields['matiere'].queryset = Matiere.objects.none()
    
    def clean_nom(self):
        nom = self.cleaned_data.get('nom')
        if not nom:
            raise forms.ValidationError("Le nom du groupe est obligatoire")
        return nom.strip()
    
    def clean_nombre_etudiants(self):
        nombre = self.cleaned_data.get('nombre_etudiants')
        if not nombre:
            raise forms.ValidationError("Le nombre d'étudiants est obligatoire")
        
        if nombre < 1:
            raise forms.ValidationError("Le nombre d'étudiants doit être supérieur à 0")
        
        if nombre > 500:
            raise forms.ValidationError("Le nombre d'étudiants ne peut pas dépasser 500")
        
        return nombre
    
    def clean(self):
        cleaned_data = super().clean()
        professeur = cleaned_data.get('professeur')
        matiere = cleaned_data.get('matiere')
        
        # Vérifier que la matière appartient au professeur
        if professeur and matiere:
            if professeur.matiere != matiere:
                raise forms.ValidationError(
                    f"Cette matière n'est pas enseignée par le professeur {professeur.nom_complet}. "
                    f"Le professeur enseigne: {professeur.matiere.nom if professeur.matiere else 'Aucune matière'}"
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
                'min': date.today()
            }),
            'heure_debut': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'heure_fin': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_seance = cleaned_data.get('date')
        heure_debut = cleaned_data.get('heure_debut')
        heure_fin = cleaned_data.get('heure_fin')

        if date_seance and date_seance < date.today():
            raise forms.ValidationError("Impossible d'ajouter ou modifier une séance dans le passé.")

        if heure_debut and heure_fin and heure_fin <= heure_debut:
            raise forms.ValidationError("L'heure de fin doit être après l'heure de début.")

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
