from django.urls import path
from .views import AskView, HistoryView

urlpatterns = [
    path("ask/", AskView.as_view(), name="ask"),
    path("history/", HistoryView.as_view(), name="history"),
]
