import time

from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.cache import cache
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DeleteView, DetailView, ListView

from . import conf
from .forms import TicketFilterForm, TicketReportForm
from .models import Ticket
from .signals import ticket_created

PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def parse_throttle(value):
    if not value:
        return None
    count, _, period = value.partition("/")
    return int(count), PERIODS[period.strip()]


def is_throttled(user):
    rate = parse_throttle(conf.get("THROTTLE"))
    if rate is None:
        return False
    limit, seconds = rate
    key = f"snapnote:throttle:{user.pk}:{int(time.time() // seconds)}"
    cache.add(key, 0, timeout=seconds)
    try:
        return cache.incr(key) > limit
    except ValueError:  # expired between add and incr
        return False


class ReportView(View):
    """POST endpoint used by the floating button. Plain Django: no DRF."""

    http_method_names = ["post"]

    def post(self, request):
        user = request.user
        if not user.is_authenticated or not conf.get_callable("CAN_REPORT")(user):
            return JsonResponse({"detail": "forbidden"}, status=403)
        if is_throttled(user):
            return JsonResponse({"detail": "throttled"}, status=429)
        form = TicketReportForm(request.POST, request.FILES)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)
        ticket = form.save(commit=False)
        ticket.reported_by = user
        ticket.save()
        url = ticket.get_absolute_url() if conf.get("ENABLE_MANAGEMENT_VIEWS") else ""
        absolute_url = request.build_absolute_uri(url) if url else ""
        from django.db import transaction

        transaction.on_commit(
            lambda: ticket_created.send(sender=Ticket, ticket=ticket, request_url=absolute_url)
        )
        return JsonResponse({"id": ticket.pk}, status=201)


class ManagementMixin(PermissionRequiredMixin):
    """Login (redirect) and model permission (403) required; can be switched off."""

    def dispatch(self, request, *args, **kwargs):
        if not conf.get("ENABLE_MANAGEMENT_VIEWS"):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["snapnote_base_template"] = conf.get("BASE_TEMPLATE") or "snapnote/base.html"
        return context


class TicketListView(ManagementMixin, ListView):
    permission_required = "snapnote.view_ticket"
    model = Ticket
    paginate_by = 25
    template_name = "snapnote/ticket_list.html"

    def get_queryset(self):
        self.filter_form = TicketFilterForm(self.request.GET)
        return self.filter_form.filter(Ticket.objects.select_related("reported_by"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        params = self.request.GET.copy()
        params.pop("page", None)
        context["query_string"] = params.urlencode()
        return context


class TicketDetailView(ManagementMixin, DetailView):
    permission_required = "snapnote.view_ticket"
    model = Ticket
    template_name = "snapnote/ticket_detail.html"


class TicketDeleteView(ManagementMixin, DeleteView):
    permission_required = "snapnote.delete_ticket"
    model = Ticket
    template_name = "snapnote/ticket_confirm_delete.html"
    success_url = reverse_lazy("snapnote:ticket_list")


class StatusChangeView(ManagementMixin, View):
    permission_required = "snapnote.change_ticket"
    http_method_names = ["post"]
    close = True

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk)
        if self.close:
            ticket.close(request.user)
        else:
            ticket.reopen()
        return HttpResponseRedirect(reverse("snapnote:ticket_detail", kwargs={"pk": ticket.pk}))
