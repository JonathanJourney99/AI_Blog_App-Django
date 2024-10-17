from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class BlogPost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    youtube_title = models.CharField(max_length=255)  # Added max_length
    youtube_link = models.URLField()
    generated_content = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.youtube_title
