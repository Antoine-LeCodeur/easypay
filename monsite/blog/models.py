from django.db import models
from django.utils import timezone


class Utilisateur(models.Model):
	nomprenom = models.CharField(max_length=120)
	service = models.CharField(max_length=80)
	mail = models.EmailField(unique=True)
	paye = models.DecimalField(max_digits=10, decimal_places=2)

	class Meta:
		db_table = "utilisateur"

	def __str__(self) -> str:
		return f"{self.nomprenom} - {self.service}"


class Historique(models.Model):
	utilisateur = models.ForeignKey(
		Utilisateur,
		on_delete=models.CASCADE,
		related_name="historiques",
		db_column="id_utilisateur",
	)
	date = models.DateField(auto_now_add=True)
	heure = models.TimeField(auto_now_add=True)
	heures_sup = models.DecimalField(max_digits=6, decimal_places=2, default=0)
	prime = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	mois = models.PositiveSmallIntegerField()
	annee = models.PositiveSmallIntegerField()

	class Meta:
		db_table = "historique"
		constraints = [
			models.UniqueConstraint(
				fields=["utilisateur", "mois", "annee"],
				name="unique_historique_utilisateur_mois",
			),
		]

	def save(self, *args, **kwargs) -> None:
		if not self.mois or not self.annee:
			today = timezone.localdate()
			self.mois = today.month
			self.annee = today.year
		super().save(*args, **kwargs)

	def __str__(self) -> str:
		return f"{self.utilisateur.nomprenom} - {self.mois}/{self.annee}"
