@staff_member_required
def station_map_view(request):
    """Зөвхөн 1 Location (сонгосон цэг) map дээр харуулна"""
    loc_id = request.GET.get("id")
    if not loc_id:
        return render(
            request,
            "inventory/location_map_one.html",
            {"locations_json": "[]", "single": True}
        )

    loc = get_object_or_404(
        Location.objects
        .select_related("aimag_ref")
        .annotate(device_count=Count("devices")),
        id=loc_id
    )

    point = [{
        "id": loc.id,
        "name": loc.name,
        "lat": float(loc.latitude),
        "lon": float(loc.longitude),
        "type": loc.location_type,
        "aimag": loc.aimag_ref.name if loc.aimag_ref else "Тодорхойгүй",
        "device_count": int(loc.device_count or 0),
    }]

    return render(
        request,
        "inventory/location_map_one.html",
        {
            "locations_json": json.dumps(point, cls=DjangoJSONEncoder),
            "single": True
        }
    )
