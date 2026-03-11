from django import forms
from .models import Device, Location, Aimag, SumDuureg


class DeviceAdminForm(forms.ModelForm):
    admin_aimag = forms.ModelChoiceField(
        queryset=Aimag.objects.none(),
        required=False,
        label="Аймаг / Улаанбаатар",
    )
    admin_sum = forms.ModelChoiceField(
        queryset=SumDuureg.objects.none(),
        required=False,
        label="Сум / Дүүрэг",
    )

    class Meta:
        model = Device
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        used_aimag_ids = (
            Location.objects.exclude(aimag_ref_id__isnull=True)
            .values_list("aimag_ref_id", flat=True)
            .distinct()
        )

        self.fields["admin_aimag"].queryset = Aimag.objects.filter(
            id__in=used_aimag_ids
        ).order_by("name")

        self.fields["location"].queryset = Location.objects.select_related(
            "aimag_ref", "sum_ref"
        ).order_by("name")

        self.fields["admin_aimag"].label_from_instance = lambda obj: obj.name
        self.fields["admin_sum"].label_from_instance = lambda obj: obj.name
        self.fields["location"].label_from_instance = lambda obj: obj.name

        instance = self.instance if getattr(self, "instance", None) and self.instance.pk else None

        aimag_id = None
        sum_id = None

        if self.is_bound:
            raw_aimag = self.data.get("admin_aimag") or ""
            raw_sum = self.data.get("admin_sum") or ""

            try:
                aimag_id = int(raw_aimag) if raw_aimag else None
            except (TypeError, ValueError):
                aimag_id = None

            try:
                sum_id = int(raw_sum) if raw_sum else None
            except (TypeError, ValueError):
                sum_id = None

        if (
            not aimag_id
            and instance
            and instance.location_id
            and instance.location
            and instance.location.aimag_ref_id
        ):
            aimag_id = instance.location.aimag_ref_id

        if (
            not sum_id
            and instance
            and instance.location_id
            and instance.location
            and instance.location.sum_ref_id
        ):
            sum_id = instance.location.sum_ref_id

        if aimag_id:
            self.fields["admin_aimag"].initial = aimag_id

        if aimag_id:
            self.fields["admin_sum"].queryset = SumDuureg.objects.filter(
                aimag_id=aimag_id
            ).order_by("name")
        else:
            self.fields["admin_sum"].queryset = SumDuureg.objects.none()

        if sum_id:
            self.fields["admin_sum"].initial = sum_id

        qs = Location.objects.select_related("aimag_ref", "sum_ref").order_by("name")

        if aimag_id:
            qs = qs.filter(aimag_ref_id=aimag_id)

        if sum_id:
            qs = qs.filter(sum_ref_id=sum_id)

        self.fields["location"].queryset = qs

        if instance and instance.location_id:
            self.fields["location"].queryset = (
                self.fields["location"].queryset
                | Location.objects.filter(pk=instance.location_id)
            ).distinct().order_by("name")

    def clean(self):
        cleaned_data = super().clean()

        selected_aimag = cleaned_data.get("admin_aimag")
        selected_sum = cleaned_data.get("admin_sum")
        selected_location = cleaned_data.get("location")

        if selected_sum and selected_aimag:
            if selected_sum.aimag_id != selected_aimag.id:
                self.add_error(
                    "admin_sum",
                    "Сонгосон сум/дүүрэг нь сонгосон аймагт хамаарахгүй байна.",
                )

        if selected_location:
            if selected_aimag and selected_location.aimag_ref_id != selected_aimag.id:
                self.add_error(
                    "location",
                    "Сонгосон байршил нь сонгосон аймагтай тохирохгүй байна.",
                )

            if selected_sum and selected_location.sum_ref_id != selected_sum.id:
                self.add_error(
                    "location",
                    "Сонгосон байршил нь сонгосон сум/дүүрэгтэй тохирохгүй байна.",
                )

        return cleaned_data
