from app.main import app


def test_expected_routes_are_registered() -> None:
    # OpenAPI resolves nested/deferred IncludedRouter entries in recent FastAPI versions.
    paths = set(app.openapi()["paths"])
    assert "/api/v1/health" in paths
    assert "/api/v1/health/database" in paths
    assert "/api/v1/users" in paths
    assert "/api/v1/farms" in paths
    assert "/api/v1/farms/{farm_id}/boundary" in paths
    assert "/api/v1/farms/{farm_id}/validation" in paths
    assert "/api/v1/blocks" in paths
    assert "/api/v1/blocks/validate-geometry" in paths
    assert "/api/v1/blocks/by-location" in paths
    assert "/api/v1/blocks/{block_id}/validation" in paths
    assert "/api/v1/telegram/webhook" in paths
    assert "/api/v1/knowledge/search" in paths
