from django.db import migrations


SQL = """
CREATE FUNCTION ec3_immutable_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'EC3 evidence and decisions are immutable'; END;
$$;
CREATE TRIGGER ec3_epd_immutable BEFORE UPDATE OR DELETE ON ec3_epdversion
FOR EACH ROW EXECUTE FUNCTION ec3_immutable_guard();
CREATE TRIGGER ec3_review_immutable BEFORE UPDATE OR DELETE ON ec3_review
FOR EACH ROW EXECUTE FUNCTION ec3_immutable_guard();
CREATE FUNCTION ec3_candidate_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'EC3 candidate history is protected'; END IF;
 IF NEW.material_id IS DISTINCT FROM OLD.material_id
 OR NEW.epd_version_id IS DISTINCT FROM OLD.epd_version_id
 OR NEW.created_by_id IS DISTINCT FROM OLD.created_by_id
 OR NEW.created_at IS DISTINCT FROM OLD.created_at
 OR (OLD.promoted_version_id IS NOT NULL AND NEW.promoted_version_id IS DISTINCT FROM OLD.promoted_version_id)
 OR (OLD.mapping_id IS NOT NULL AND NEW.mapping_id IS DISTINCT FROM OLD.mapping_id)
 THEN RAISE EXCEPTION 'EC3 candidate identity is immutable'; END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER ec3_candidate_history BEFORE UPDATE OR DELETE ON ec3_candidate
FOR EACH ROW EXECUTE FUNCTION ec3_candidate_guard();
CREATE FUNCTION ec3_factor_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME = 'analytics_factorambiental' THEN
  IF EXISTS (SELECT 1 FROM ec3_candidate c JOIN analytics_versionfactorambiental v ON v.id = c.promoted_version_id WHERE v.factor_id = OLD.id)
  THEN RAISE EXCEPTION 'EC3 promoted factor evidence is immutable'; END IF;
 ELSIF EXISTS (SELECT 1 FROM ec3_candidate WHERE promoted_version_id = OLD.id) THEN
  IF TG_OP = 'DELETE' OR (to_jsonb(NEW) - 'estado') IS DISTINCT FROM (to_jsonb(OLD) - 'estado')
  THEN RAISE EXCEPTION 'EC3 promoted version evidence is immutable'; END IF;
 END IF;
 IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER ec3_factor_evidence BEFORE UPDATE OR DELETE ON analytics_factorambiental
FOR EACH ROW EXECUTE FUNCTION ec3_factor_guard();
CREATE TRIGGER ec3_version_evidence BEFORE UPDATE OR DELETE ON analytics_versionfactorambiental
FOR EACH ROW EXECUTE FUNCTION ec3_factor_guard();
CREATE FUNCTION ec3_snapshot_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.record_kind = 'ec3_epd' THEN RAISE EXCEPTION 'EC3 snapshot evidence is immutable'; END IF;
 IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER ec3_snapshot_evidence BEFORE UPDATE OR DELETE ON knowledge_externalsnapshot
FOR EACH ROW EXECUTE FUNCTION ec3_snapshot_guard();
"""

REVERSE = """
DROP TRIGGER IF EXISTS ec3_snapshot_evidence ON knowledge_externalsnapshot;
DROP FUNCTION IF EXISTS ec3_snapshot_guard();
DROP TRIGGER IF EXISTS ec3_version_evidence ON analytics_versionfactorambiental;
DROP TRIGGER IF EXISTS ec3_factor_evidence ON analytics_factorambiental;
DROP FUNCTION IF EXISTS ec3_factor_guard();
DROP TRIGGER IF EXISTS ec3_candidate_history ON ec3_candidate;
DROP FUNCTION IF EXISTS ec3_candidate_guard();
DROP TRIGGER IF EXISTS ec3_review_immutable ON ec3_review;
DROP TRIGGER IF EXISTS ec3_epd_immutable ON ec3_epdversion;
DROP FUNCTION IF EXISTS ec3_immutable_guard();
"""


def forward(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(SQL)


def backward(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(REVERSE)


class Migration(migrations.Migration):
    dependencies = [("ec3", "0001_initial")]
    operations = [migrations.RunPython(forward, backward)]
