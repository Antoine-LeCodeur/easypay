from django.db import models


class Utilisateur(models.Model):
	nomprenom = models.CharField(max_length=120)
	service = models.CharField(max_length=80)
	mail = models.EmailField(unique=True)
	paye = models.DecimalField(max_digits=10, decimal_places=2)

	class Meta:
		db_table = "utilisateur"

	def __str__(self) -> str:
		return f"{self.nomprenom} - {self.service}"
