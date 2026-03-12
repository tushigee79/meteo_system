from django import forms
from ..models import Device


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()

        kind = cleaned.get("kind")
        other_name = (cleaned.get("other_name") or "").strip()
        catalog_item = cleaned.get("catalog_item")

        if kind == Device.Kind.OTHER and not other_name:
            self.add_error("other_name", "“Бусад” сонгосон бол нэр заавал бөглөнө.")

        if catalog_item and hasattr(catalog_item, "kind") and catalog_item.kind != kind:
            self.add_error("catalog_item", "Каталогийн төрөл таарахгүй.")

        return cleaned