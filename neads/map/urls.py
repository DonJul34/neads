from django.urls import path
from . import views

urlpatterns = [
    path('view/', views.map_view, name='map_view'),
    path('ajax/data/', views.ajax_map_data, name='ajax_map_data'),
    path('search/', views.map_search_view, name='map_search'),
    path('api/creators/', views.api_creators, name='api_creators'),
] 