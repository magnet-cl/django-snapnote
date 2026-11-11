from django.urls import path

from . import views

app_name = "snapnote"

urlpatterns = [
    path("report/", views.ReportView.as_view(), name="report"),
    path("", views.TicketListView.as_view(), name="ticket_list"),
    path("<int:pk>/", views.TicketDetailView.as_view(), name="ticket_detail"),
    path("<int:pk>/close/", views.StatusChangeView.as_view(close=True), name="ticket_close"),
    path("<int:pk>/reopen/", views.StatusChangeView.as_view(close=False), name="ticket_reopen"),
    path("<int:pk>/delete/", views.TicketDeleteView.as_view(), name="ticket_delete"),
]
