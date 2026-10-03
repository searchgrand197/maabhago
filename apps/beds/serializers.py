from rest_framework import serializers
from apps.beds.models import Bed, BedCleaningTask, BedRoom, Floor


class BedSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Bed
        fields = ["id", "bed_code", "bed_number", "status", "status_display", "notes", "room"]


class BedRoomWithBedsSerializer(serializers.ModelSerializer):
    """Full room serializer including all beds — used in the floor tree for the bed-picker UI."""
    room_type_display  = serializers.CharField(source="get_room_type_display", read_only=True)
    available_bed_count = serializers.SerializerMethodField()
    total_bed_count     = serializers.SerializerMethodField()
    beds = BedSerializer(many=True, read_only=True)

    class Meta:
        model = BedRoom
        fields = [
            "id", "name", "room_number", "room_type", "room_type_display",
            "is_ac", "daily_charge", "max_beds", "is_active", "notes",
            "available_bed_count", "total_bed_count", "beds",
        ]

    def get_available_bed_count(self, obj):
        return sum(1 for b in obj.beds.all() if b.status == Bed.Status.AVAILABLE)

    def get_total_bed_count(self, obj):
        return obj.beds.count()


class BedRoomSerializer(serializers.ModelSerializer):
    room_type_display   = serializers.CharField(source="get_room_type_display", read_only=True)
    available_bed_count = serializers.SerializerMethodField()
    total_bed_count     = serializers.SerializerMethodField()
    beds = BedSerializer(many=True, read_only=True)
    floor_name   = serializers.CharField(source="floor.name", read_only=True)
    floor_number = serializers.IntegerField(source="floor.floor_number", read_only=True)

    class Meta:
        model = BedRoom
        fields = [
            "id", "name", "room_number", "room_type", "room_type_display",
            "is_ac", "daily_charge", "max_beds", "is_active", "notes",
            "floor", "floor_name", "floor_number",
            "available_bed_count", "total_bed_count", "beds",
        ]

    def get_available_bed_count(self, obj):
        return sum(1 for b in obj.beds.all() if b.status == Bed.Status.AVAILABLE)

    def get_total_bed_count(self, obj):
        return obj.beds.count()


class BedRoomBriefSerializer(serializers.ModelSerializer):
    room_type_display   = serializers.CharField(source="get_room_type_display", read_only=True)
    available_bed_count = serializers.SerializerMethodField()
    total_bed_count     = serializers.SerializerMethodField()

    class Meta:
        model = BedRoom
        fields = [
            "id", "name", "room_number", "room_type", "room_type_display",
            "is_ac", "daily_charge", "max_beds", "is_active",
            "available_bed_count", "total_bed_count",
        ]

    def get_available_bed_count(self, obj):
        return obj.beds.filter(status=Bed.Status.AVAILABLE).count()

    def get_total_bed_count(self, obj):
        return obj.beds.count()


class FloorWithRoomsSerializer(serializers.ModelSerializer):
    """Floor + rooms + beds — single call for the bed-picker UI."""
    rooms        = BedRoomWithBedsSerializer(many=True, read_only=True)
    total_beds   = serializers.SerializerMethodField()
    available_beds = serializers.SerializerMethodField()

    class Meta:
        model = Floor
        fields = [
            "id", "floor_number", "name", "description", "is_active",
            "rooms", "total_beds", "available_beds",
        ]

    def get_total_beds(self, obj):
        return sum(r.beds.count() for r in obj.rooms.all())

    def get_available_beds(self, obj):
        return sum(
            sum(1 for b in r.beds.all() if b.status == Bed.Status.AVAILABLE)
            for r in obj.rooms.all()
        )


class FloorSerializer(serializers.ModelSerializer):
    rooms          = BedRoomBriefSerializer(many=True, read_only=True)
    total_beds     = serializers.SerializerMethodField()
    available_beds = serializers.SerializerMethodField()

    class Meta:
        model = Floor
        fields = [
            "id", "floor_number", "name", "description", "is_active",
            "rooms", "total_beds", "available_beds",
        ]

    def get_total_beds(self, obj):
        return Bed.objects.filter(room__floor=obj).count()

    def get_available_beds(self, obj):
        return Bed.objects.filter(room__floor=obj, status=Bed.Status.AVAILABLE).count()


class FloorBriefSerializer(serializers.ModelSerializer):
    total_beds     = serializers.SerializerMethodField()
    available_beds = serializers.SerializerMethodField()

    class Meta:
        model = Floor
        fields = ["id", "floor_number", "name", "description", "is_active", "total_beds", "available_beds"]

    def get_total_beds(self, obj):
        return Bed.objects.filter(room__floor=obj).count()

    def get_available_beds(self, obj):
        return Bed.objects.filter(room__floor=obj, status=Bed.Status.AVAILABLE).count()


class BedStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = ["status", "notes"]


class BedCleaningTaskSerializer(serializers.ModelSerializer):
    bed_code = serializers.CharField(source="bed.bed_code", read_only=True)
    bed_room = serializers.CharField(source="bed.room.name", read_only=True)
    assigned_staff_name = serializers.SerializerMethodField()

    class Meta:
        model = BedCleaningTask
        fields = [
            "id",
            "hospital",
            "bed",
            "bed_code",
            "bed_room",
            "assigned_staff",
            "assigned_staff_name",
            "status",
            "notes",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["hospital", "started_at", "completed_at", "created_at", "updated_at"]

    def get_assigned_staff_name(self, obj):
        if not obj.assigned_staff_id:
            return ""
        return f"{obj.assigned_staff.first_name} {obj.assigned_staff.last_name}".strip() or obj.assigned_staff.employee_code
