from django.db import models

# Create your models here.

class User(models.Model):
    slack_id = models.CharField(max_length=200,primary_key=True)
    redmine_url = models.CharField(max_length=200)
    redmine_key = models.CharField(max_length=200,unique=True)

    def __str__(self):
        return self.slack_id + " " + self.redmine_key
