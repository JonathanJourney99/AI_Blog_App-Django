from django.urls import path
from . import views
# shift + alt+  down arrow key -> copy same to next lines
urlpatterns = [
    path('', views.index, name='index'),    
    path('login', views.user_login, name='login'),
    path('signup', views.user_signup, name='signup'),
    path('logout', views.user_logout, name='logout'),
    path('generate-blog', views.generate_blog, name='genreate-blog'),
    path('blog-list', views.blog_list, name='blog-list'),
    path('blog-details/<int:blog_id>/', views.blog_details, name='blog-details'),
]

