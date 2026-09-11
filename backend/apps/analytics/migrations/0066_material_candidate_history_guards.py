from django.db import migrations


def install(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    CREATE FUNCTION analytics_material_candidate_guard() RETURNS trigger AS $$
    BEGIN
      IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Material candidate history is immutable'; END IF;
      IF TG_OP = 'UPDATE' THEN
        IF OLD.status = 'promoted_to_draft' OR
           (to_jsonb(OLD) - ARRAY['status','promoted_factor_id','promoted_version_id','promoted_by_id','promoted_at']) IS DISTINCT FROM
           (to_jsonb(NEW) - ARRAY['status','promoted_factor_id','promoted_version_id','promoted_by_id','promoted_at'])
        THEN RAISE EXCEPTION 'Material candidate evidence is immutable'; END IF;
      END IF;
      IF NEW.source_indicator_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM knowledge_oekobaudatenvironmentalindicatorfact i
        WHERE i.id=NEW.source_indicator_id AND i.profile_id=NEW.source_profile_id
      ) THEN RAISE EXCEPTION 'Material indicator must belong to profile'; END IF;
      IF NEW.status IN ('ready_for_review','rejected','promoted_to_draft') AND NOT EXISTS (
        SELECT 1 FROM analytics_materialfactorcandidatereview r
        WHERE r.id=(SELECT max(id) FROM analytics_materialfactorcandidatereview WHERE candidate_id=NEW.id)
        AND r.decision=CASE WHEN NEW.status='rejected' THEN 'rejected' ELSE 'approved' END
      ) THEN RAISE EXCEPTION 'Material transition requires human review'; END IF;
      IF NEW.status='promoted_to_draft' AND NOT EXISTS (
        SELECT 1 FROM analytics_versionfactorambiental v JOIN analytics_factorambiental f ON f.id=v.factor_id
        WHERE v.id=NEW.promoted_version_id AND f.id=NEW.promoted_factor_id AND f.organizacion_id IS NULL
        AND v.estado='borrador' AND v.contexto->>'source_candidate_id'=NEW.id::text
        AND f.contexto->>'source_candidate_id'=NEW.id::text
      ) THEN RAISE EXCEPTION 'Material promotion requires its own global draft'; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    CREATE TRIGGER analytics_material_candidate_guard BEFORE INSERT OR UPDATE OR DELETE
    ON analytics_materialenvironmentalfactorcandidate FOR EACH ROW EXECUTE FUNCTION analytics_material_candidate_guard();

    CREATE FUNCTION analytics_material_review_guard() RETURNS trigger AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN RAISE EXCEPTION 'Material reviews are immutable'; END IF;
      PERFORM 1 FROM analytics_materialenvironmentalfactorcandidate WHERE id=NEW.candidate_id FOR UPDATE;
      IF EXISTS (SELECT 1 FROM analytics_materialenvironmentalfactorcandidate WHERE id=NEW.candidate_id AND status='promoted_to_draft')
      THEN RAISE EXCEPTION 'Promoted candidate review is frozen'; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    CREATE TRIGGER analytics_material_review_guard BEFORE INSERT OR UPDATE OR DELETE
    ON analytics_materialfactorcandidatereview FOR EACH ROW EXECUTE FUNCTION analytics_material_review_guard();

    CREATE FUNCTION analytics_material_factor_guard() RETURNS trigger AS $$
    BEGIN
      IF TG_TABLE_NAME='analytics_factorambiental' THEN
        IF EXISTS (SELECT 1 FROM analytics_materialenvironmentalfactorcandidate WHERE promoted_factor_id=OLD.id) THEN
          IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Material factor provenance is protected'; END IF;
          IF OLD.contexto IS DISTINCT FROM NEW.contexto OR OLD.organizacion_id IS DISTINCT FROM NEW.organizacion_id
            OR OLD.unidad_entrada IS DISTINCT FROM NEW.unidad_entrada OR OLD.unidad_resultado IS DISTINCT FROM NEW.unidad_resultado
            OR OLD.sustancia_impacto IS DISTINCT FROM NEW.sustancia_impacto
            OR OLD.categoria IS DISTINCT FROM NEW.categoria
          THEN RAISE EXCEPTION 'Material factor provenance is protected'; END IF;
        END IF;
      ELSE
        IF EXISTS (SELECT 1 FROM analytics_materialenvironmentalfactorcandidate WHERE promoted_version_id=OLD.id) THEN
          IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Material version provenance is protected'; END IF;
          IF (to_jsonb(OLD)-ARRAY['estado','vigencia_desde','vigencia_hasta']) IS DISTINCT FROM
             (to_jsonb(NEW)-ARRAY['estado','vigencia_desde','vigencia_hasta'])
          THEN RAISE EXCEPTION 'Material version provenance is protected'; END IF;
        END IF;
      END IF;
      IF TG_OP='DELETE' THEN RETURN OLD; END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    CREATE TRIGGER analytics_material_factor_guard BEFORE UPDATE OR DELETE ON analytics_factorambiental
    FOR EACH ROW EXECUTE FUNCTION analytics_material_factor_guard();
    CREATE TRIGGER analytics_material_version_guard BEFORE UPDATE OR DELETE ON analytics_versionfactorambiental
    FOR EACH ROW EXECUTE FUNCTION analytics_material_factor_guard();
    """)


def uninstall(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("""
    DROP TRIGGER IF EXISTS analytics_material_version_guard ON analytics_versionfactorambiental;
    DROP TRIGGER IF EXISTS analytics_material_factor_guard ON analytics_factorambiental;
    DROP TRIGGER IF EXISTS analytics_material_review_guard ON analytics_materialfactorcandidatereview;
    DROP TRIGGER IF EXISTS analytics_material_candidate_guard ON analytics_materialenvironmentalfactorcandidate;
    DROP FUNCTION IF EXISTS analytics_material_factor_guard();
    DROP FUNCTION IF EXISTS analytics_material_review_guard();
    DROP FUNCTION IF EXISTS analytics_material_candidate_guard();
    """)


class Migration(migrations.Migration):
    dependencies = [("analytics", "0065_material_factor_candidates")]
    operations = [migrations.RunPython(install, uninstall)]
