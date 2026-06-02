from django.urls import path
from .views import predict_individual, train_model_view

urlpatterns = [
    path('predict/', predict_individual, name='predict_individual'),
    path('train/', train_model_view, name='train_model'),
]
