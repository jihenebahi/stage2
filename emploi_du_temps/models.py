from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
class Matiere(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.nom


class Professeur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telephone = models.CharField(max_length=20, unique=True)
    matiere = models.ForeignKey(Matiere, on_delete=models.SET_NULL, null=True, blank=True, related_name='professeurs')
    
    class Meta:
        verbose_name_plural = "professeurs"
    
    def __str__(self):
        return f"{self.prenom} {self.nom}"
    
    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"
    
    @property
    def matiere_nom(self):
        return self.matiere.nom if self.matiere else "Aucune matière"


class Salle(models.Model):
    nom = models.CharField(max_length=50, unique=True)
    capacite = models.IntegerField()
    
    def __str__(self):
        return f"{self.nom} ({self.capacite} places)"

class Groupe(models.Model):
    nom = models.CharField(max_length=100)
    professeur = models.ForeignKey(Professeur, on_delete=models.CASCADE, related_name='groupes')
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='groupes')
    nombre_etudiants = models.IntegerField()
    
    class Meta:
        unique_together = ('nom', 'professeur', 'matiere')
    
    def __str__(self):
        return f"{self.nom} - {self.professeur} - {self.matiere}"

class Seance(models.Model):
    groupe = models.ForeignKey(Groupe, on_delete=models.CASCADE, related_name='seances')
    salle = models.ForeignKey(Salle, on_delete=models.CASCADE, related_name='seances')
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()

    class Meta:
        ordering = ['date', 'heure_debut']

    def __str__(self):
        return f"{self.groupe} - {self.salle} - {self.date} {self.heure_debut}"

    def est_passee(self):
        """Vérifie si la séance est déjà passée"""
        now = timezone.now()
        return timezone.make_aware(
            timezone.datetime.combine(self.date, self.heure_fin)
        ) < now

    def valider_seance(self, exclude_id=None):
        """Vérifie les conflits pour cette séance"""
        conflits = []

        # Vérifier la salle
        conflits_salle = Seance.objects.filter(
            salle=self.salle,
            date=self.date
        )
        if exclude_id:
            conflits_salle = conflits_salle.exclude(id=exclude_id)
        conflits_salle = conflits_salle.filter(
            Q(heure_debut__lt=self.heure_fin, heure_fin__gt=self.heure_debut)
        )

        if conflits_salle.exists():
            conflits.append(f"❌ Salle {self.salle.nom} déjà occupée à cette date et heure")

        # Vérifier le professeur
        conflits_prof = Seance.objects.filter(
            groupe__professeur=self.groupe.professeur,
            date=self.date
        )
        if exclude_id:
            conflits_prof = conflits_prof.exclude(id=exclude_id)
        conflits_prof = conflits_prof.filter(
            Q(heure_debut__lt=self.heure_fin, heure_fin__gt=self.heure_debut)
        )

        if conflits_prof.exists():
            conflits.append(f"❌ Professeur {self.groupe.professeur.nom_complet} indisponible à cette date et heure")

        # Vérifier le groupe
        conflits_groupe = Seance.objects.filter(
            groupe=self.groupe,
            date=self.date
        )
        if exclude_id:
            conflits_groupe = conflits_groupe.exclude(id=exclude_id)
        conflits_groupe = conflits_groupe.filter(
            Q(heure_debut__lt=self.heure_fin, heure_fin__gt=self.heure_debut)
        )

        if conflits_groupe.exists():
            conflits.append(f"❌ Groupe {self.groupe.nom} déjà programmé à cette date et heure")

        # Vérifier la capacité de la salle
        if self.groupe.nombre_etudiants > self.salle.capacite:
            conflits.append(
                f"❌ Capacité insuffisante (groupe: {self.groupe.nombre_etudiants} élèves, salle: {self.salle.capacite} places)"
            )

        return conflits