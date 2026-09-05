from rest_framework import serializers
from .models import EnvironmentalSource,ExternalRecord,ExternalSnapshot,SourceState,SyncRun
class SourceStateSerializer(serializers.ModelSerializer):
    class Meta:model=SourceState;exclude=["source"]
class EnvironmentalSourceSerializer(serializers.ModelSerializer):
    sync_state=SourceStateSerializer(read_only=True)
    class Meta:model=EnvironmentalSource;fields="__all__"
class SyncRunSerializer(serializers.ModelSerializer):
    class Meta:model=SyncRun;fields="__all__"
class ExternalSnapshotSerializer(serializers.ModelSerializer):
    class Meta:model=ExternalSnapshot;fields="__all__"
class ExternalRecordSerializer(serializers.ModelSerializer):
    class Meta:model=ExternalRecord;fields="__all__"
