from django.urls import path
from .views import ml_dashboard, predict_individual, train_model_view


urlpatterns = [
    path("dashboard/", ml_dashboard, name="ml_dashboard"),
    path("predict/", predict_individual, name="predict_individual"),
    path("train/", train_model_view, name="train_model"),
]
