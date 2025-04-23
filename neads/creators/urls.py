from django.urls import path
from . import views
from neads.map.views import api_creators

urlpatterns = [
    path('gallery/', views.gallery_view, name='gallery_view'),
    path('detail/<int:creator_id>/', views.creator_detail, name='creator_detail'),
    path('edit/<int:creator_id>/', views.creator_edit, name='creator_edit'),
    path('add/', views.creator_add, name='creator_add'),
    path('upload-media/<int:creator_id>/', views.media_upload, name='upload_media'),
    path('search/', views.search_view, name='search_view'),
    path('api/creators/', api_creators, name='api_creators'),
    path('api/creators/map-search/', views.api_map_search, name='api_map_search'),
    path('api/cities/', views.api_cities, name='api_cities'),
    path('ajax-search/', views.ajax_filter_results, name='ajax_search'),
    path('toggle-favorite/<int:creator_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('add-favorite/<int:creator_id>/', views.toggle_favorite, name='add_favorite'),
    path('remove-favorite/<int:creator_id>/', views.toggle_favorite, name='remove_favorite'),
    path('rate/<int:creator_id>/', views.rate_creator, name='rate_creator'),
    path('discover/', views.discover_view, name='discover'),
    path('toggle-verification/<int:creator_id>/', views.toggle_verification, name='toggle_verification'),
    path('delete-creator/<int:creator_id>/', views.delete_creator, name='delete_creator'),
    path('delete-rating/<int:rating_id>/', views.delete_rating, name='delete_rating'),
    path('list/', views.creators_list, name='creators_list'),
] 