import io
from urllib.parse import urlsplit

from django import forms
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

from . import conf
from .models import Ticket

ALLOWED_FORMATS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}


def clean_image(upload):
    """Validates size and dimensions, rejects non raster formats and re-encodes with Pillow."""
    max_bytes = conf.get("MAX_UPLOAD_MB") * 1024 * 1024
    if upload.size > max_bytes:
        raise forms.ValidationError(
            _("The image is too large (max %(mb)s MB)."), params={"mb": conf.get("MAX_UPLOAD_MB")}
        )
    try:
        upload.seek(0)
        image = Image.open(upload)
        fmt = image.format
        if fmt not in ALLOWED_FORMATS:
            raise forms.ValidationError(_("Unsupported image format."))
        limit = conf.get("MAX_DIMENSION")
        if max(image.size) > limit:
            raise forms.ValidationError(
                _("The image is too large (max %(px)s px per side)."), params={"px": limit}
            )
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise forms.ValidationError(_("Upload a valid image.")) from None
    if fmt == "JPEG" and image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    out = io.BytesIO()
    # Saving a fresh image drops metadata and any trailing payload.
    image.save(out, format=fmt)
    return ContentFile(
        out.getvalue(), name=f"{upload.name.rsplit('.', 1)[0]}.{ALLOWED_FORMATS[fmt]}"
    )


class TicketReportForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("title", "description", "page_url", "screenshot", "annotations")

    def clean_page_url(self):
        value = self.cleaned_data["page_url"].strip()
        if urlsplit(value).scheme not in ("http", "https"):
            raise forms.ValidationError(_("Enter an http or https URL."))
        return value

    def _clean_file(self, name):
        upload = self.cleaned_data.get(name)
        # Falsy when nothing was uploaded (or an empty FieldFile).
        if not upload or not hasattr(upload, "size"):
            return upload
        return clean_image(upload)

    def clean_screenshot(self):
        return self._clean_file("screenshot")

    def clean_annotations(self):
        return self._clean_file("annotations")


class TicketFilterForm(forms.Form):
    q = forms.CharField(label=_("Search"), required=False)
    status = forms.ChoiceField(
        label=_("Status"), required=False, choices=[("", _("All"))] + Ticket.Status.choices
    )

    jira = forms.ChoiceField(
        label="Jira",
        required=False,
        choices=[
            ("", _("All")),
            ("ok", _("In Jira")),
            ("failed", _("Jira failed")),
            ("none", _("No Jira")),
        ],
    )

    def filter(self, queryset):
        if not self.is_valid():
            return queryset
        queryset = queryset.search(self.cleaned_data["q"]).jira(self.cleaned_data["jira"])
        if self.cleaned_data["status"]:
            queryset = queryset.filter(status=self.cleaned_data["status"])
        return queryset
