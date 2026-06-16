"""
Tests for the Flask REST API endpoints.
"""
import json
import pytest


class TestHealth:
    def test_health_ok(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.get_json()["data"]["status"] == "ok"


class TestJobsCRUD:
    def test_list_jobs_empty(self, client):
        res = client.get("/api/jobs")
        assert res.status_code == 200
        assert isinstance(res.get_json()["data"], list)

    def test_create_job_success(self, client):
        payload = {
            "name": "API Test Job",
            "url": "https://example.com",
            "scraper_type": "requests",
        }
        res = client.post("/api/jobs", json=payload)
        assert res.status_code == 201
        data = res.get_json()["data"]
        assert data["name"] == "API Test Job"
        assert data["id"] is not None

    def test_create_job_missing_fields(self, client):
        res = client.post("/api/jobs", json={"name": "No URL"})
        assert res.status_code == 400
        assert not res.get_json()["success"]

    def test_get_job(self, client, sample_job):
        res = client.get(f"/api/jobs/{sample_job.id}")
        assert res.status_code == 200
        assert res.get_json()["data"]["id"] == sample_job.id

    def test_get_job_not_found(self, client):
        res = client.get("/api/jobs/999999")
        assert res.status_code == 404

    def test_update_job(self, client, sample_job):
        res = client.put(f"/api/jobs/{sample_job.id}", json={"name": "Renamed Job"})
        assert res.status_code == 200
        assert res.get_json()["data"]["name"] == "Renamed Job"

    def test_delete_job(self, client):
        # Create a job to delete
        create_res = client.post("/api/jobs", json={"name": "Temp", "url": "https://x.com"})
        job_id = create_res.get_json()["data"]["id"]

        del_res = client.delete(f"/api/jobs/{job_id}")
        assert del_res.status_code == 200

        get_res = client.get(f"/api/jobs/{job_id}")
        assert get_res.status_code == 404


class TestRecords:
    def test_list_records_empty(self, client):
        res = client.get("/api/records")
        assert res.status_code == 200
        assert isinstance(res.get_json()["data"], list)

    def test_list_records_filter_by_job(self, client, sample_job):
        res = client.get(f"/api/records?job_id={sample_job.id}")
        assert res.status_code == 200


class TestRuns:
    def test_list_runs(self, client, sample_job):
        res = client.get(f"/api/jobs/{sample_job.id}/runs")
        assert res.status_code == 200
        assert isinstance(res.get_json()["data"], list)
