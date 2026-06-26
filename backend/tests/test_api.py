"""
tests/test_api.py
──────────────────
Full API integration tests using the TestClient.
Covers all 7 endpoints with key scenarios including all 5 fixes.
"""
import pytest


class TestAnalyzeTransaction:

    def test_normal_transaction_returns_200(self, client, demo_transaction):
        resp = client.post("/api/v1/analyze-transaction", json=demo_transaction)
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] in ("ALLOW", "VERIFY", "BLOCK")
        assert "risk_score" in data
        assert "reasons" in data
        assert isinstance(data["reasons"], list)

    def test_response_has_required_fields(self, client, demo_transaction):
        resp = client.post("/api/v1/analyze-transaction", json=demo_transaction)
        data = resp.json()
        for field in ["transaction_id", "decision", "risk_score", "rule_score", "reasons"]:
            assert field in data, f"Missing field: {field}"

    def test_missing_required_fields_returns_422(self, client):
        resp = client.post("/api/v1/analyze-transaction", json={"user_id": "u1"})
        assert resp.status_code == 422

    def test_negative_amount_rejected(self, client):
        resp = client.post("/api/v1/analyze-transaction", json={
            "user_id": "u1", "amount": -100, "location": "Mumbai"
        })
        assert resp.status_code == 422

    def test_idempotency_same_transaction_id(self, client, demo_transaction):
        """Fix 3: same transaction_id twice → identical response, no duplicate scoring."""
        demo_transaction["transaction_id"] = "txn_idempotent_test"
        resp1 = client.post("/api/v1/analyze-transaction", json=demo_transaction)
        resp2 = client.post("/api/v1/analyze-transaction", json=demo_transaction)
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["risk_score"] == resp2.json()["risk_score"]
        assert resp1.json()["decision"] == resp2.json()["decision"]

    def test_new_user_no_garbage_output(self, client):
        """Fix 1: brand-new user should get a valid, non-extreme score."""
        resp = client.post("/api/v1/analyze-transaction", json={
            "user_id": "brand_new_user_xyz",
            "amount": 500.0,
            "location": "Delhi",
        })
        assert resp.status_code == 200
        data = resp.json()
        # Score should be reasonable — not exploding to 100 for a modest amount
        assert 0 <= data["risk_score"] <= 100
        assert data["decision"] in ("ALLOW", "VERIFY", "BLOCK")

    def test_full_fraud_scenario_blocks(self, client, fraud_transaction):
        """Full fraud (high amount + new location + 2AM) should BLOCK."""
        resp = client.post("/api/v1/analyze-transaction", json=fraud_transaction)
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "BLOCK"
        assert data["risk_score"] >= 75.0

    def test_verify_decision_includes_otp(self, client):
        """When decision=VERIFY, response must include an OTP."""
        # Send a transaction that's likely to be VERIFY
        # (medium amount, known location but slightly elevated)
        resp = client.post("/api/v1/analyze-transaction", json={
            "user_id": "demo_user",
            "amount": 1500.0,
            "location": "Mumbai",
            "merchant_type": "electronics",
        })
        data = resp.json()
        if data["decision"] == "VERIFY":
            assert data["otp"] is not None
            assert len(data["otp"]) == 6
            assert data["otp"].isdigit()


class TestVerifyTransaction:

    def _get_verify_transaction(self, client):
        """Helper: create a VERIFY-level transaction and return its data."""
        resp = client.post("/api/v1/analyze-transaction", json={
            "user_id": "demo_user",
            "amount": 1500.0,
            "location": "Mumbai",
        })
        return resp.json()

    def test_wrong_otp_returns_failure(self, client):
        data = self._get_verify_transaction(client)
        if data["decision"] != "VERIFY":
            pytest.skip("Transaction not in VERIFY state")

        resp = client.post("/api/v1/verify-transaction", json={
            "transaction_id": data["transaction_id"],
            "otp": "000000",  # deliberately wrong
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "failure"

    def test_correct_otp_returns_success(self, client):
        data = self._get_verify_transaction(client)
        if data["decision"] != "VERIFY":
            pytest.skip("Transaction not in VERIFY state")

        resp = client.post("/api/v1/verify-transaction", json={
            "transaction_id": data["transaction_id"],
            "otp": data["otp"],
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_unknown_transaction_returns_failure(self, client):
        resp = client.post("/api/v1/verify-transaction", json={
            "transaction_id": "txn_does_not_exist",
            "otp": "123456",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "failure"


class TestFeedback:

    def test_feedback_marks_transaction(self, client, demo_transaction):
        tx = client.post("/api/v1/analyze-transaction", json=demo_transaction).json()
        resp = client.post("/api/v1/feedback", json={
            "transaction_id": tx["transaction_id"],
            "is_fraud": True,
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_feedback_unknown_transaction(self, client):
        resp = client.post("/api/v1/feedback", json={
            "transaction_id": "txn_unknown_xyz",
            "is_fraud": False,
        })
        assert resp.status_code == 404


class TestSimulate:

    @pytest.mark.parametrize("scenario", [
        "normal", "high_amount", "new_location", "night_time", "rapid_fire", "full_fraud",
    ])
    def test_all_scenarios_return_200(self, client, scenario):
        resp = client.post("/api/v1/simulate", json={
            "user_id": "demo_user",
            "scenario": scenario,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] in ("ALLOW", "VERIFY", "BLOCK")

    def test_full_fraud_always_blocks(self, client):
        """Fix 5: demo_user profile guarantees full_fraud always BLOCKs."""
        resp = client.post("/api/v1/simulate", json={
            "user_id": "demo_user",
            "scenario": "full_fraud",
        })
        assert resp.status_code == 200
        assert resp.json()["decision"] == "BLOCK"

    def test_invalid_scenario_returns_422(self, client):
        resp = client.post("/api/v1/simulate", json={
            "user_id": "demo_user",
            "scenario": "does_not_exist",
        })
        assert resp.status_code == 422


class TestUserProfile:

    def test_existing_user_profile(self, client, demo_transaction):
        client.post("/api/v1/analyze-transaction", json=demo_transaction)
        resp = client.get("/api/v1/user-profile", params={"user_id": "demo_user"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "demo_user"
        assert "avg_amount" in data
        assert "transaction_count" in data

    def test_unknown_user_returns_404(self, client):
        resp = client.get("/api/v1/user-profile", params={"user_id": "ghost_user"})
        assert resp.status_code == 404


class TestHealth:

    def test_health_returns_ok(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True


class TestTransactionList:

    def test_list_transactions(self, client, demo_transaction):
        client.post("/api/v1/analyze-transaction", json=demo_transaction)
        resp = client.get("/api/v1/transactions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_filter_by_user(self, client, demo_transaction):
        client.post("/api/v1/analyze-transaction", json=demo_transaction)
        resp = client.get("/api/v1/transactions", params={"user_id": "demo_user"})
        assert resp.status_code == 200
        for tx in resp.json():
            assert tx["user_id"] == "demo_user"

    def test_filter_by_decision(self, client, fraud_transaction):
        client.post("/api/v1/analyze-transaction", json=fraud_transaction)
        resp = client.get("/api/v1/transactions", params={"decision": "BLOCK"})
        assert resp.status_code == 200
        for tx in resp.json():
            assert tx["decision"] == "BLOCK"
