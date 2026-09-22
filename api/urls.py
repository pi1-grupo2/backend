from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("events/", views.eventos, name="eventos"),
    path(
        "events/<int:evento_id>/subtasks/",
        views.subtareas_evento,
        name="subtareas-evento",
    ),
    path(
        "events/<int:evento_id>/subtasks/<int:subtarea_id>/",
        views.actualizar_subtarea,
        name="actualizar-subtarea",
    ),
    path(
        "events/<int:evento_id>/progress/",
        views.progreso_evento,
        name="progreso-evento",
    ),
    path(
        "events/<int:evento_id>/conflicts/",
        views.conflictos_evento,
        name="conflictos-evento",
    ),
]
