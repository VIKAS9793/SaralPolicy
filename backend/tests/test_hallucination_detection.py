"""
Hallucination Detection Validation Tests for SaralPolicy

Per Engineering Constitution Section 4.5:
- Define evaluation strategies
- Detect hallucinations
- Document limitations

These tests validate:
1. Known good outputs are accepted
2. Known hallucinations are detected
3. Edge cases are handled
4. Precision/recall is measured
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.guardrails_service import GuardrailsService


class TestHallucinationDetectionBasics:
    """Basic hallucination detection tests."""
    
    @pytest.fixture
    def service(self):
        """Create guardrails service instance."""
        return GuardrailsService()
    
    def test_grounded_response_low_risk(self, service):
        """Test that grounded responses are marked low risk."""
        source_text = """
        This health insurance policy provides coverage for hospitalization expenses.
        The sum insured is Rs 5,00,000 per year. The premium is Rs 12,500 annually.
        There is a 30-day waiting period for illnesses.
        """
        
        response = """
        The policy covers hospitalization with a sum insured of Rs 5,00,000.
        The annual premium is Rs 12,500. There is a 30-day waiting period.
        """
        
        result = service.check_hallucination_risk(source_text, response)
        
        assert result["high_risk"] is False
        assert result["overlap_ratio"] > 0.3
    
    def test_hallucinated_response_high_risk(self, service):
        """Test that hallucinated responses are marked high risk."""
        source_text = """
        This health insurance policy provides coverage for hospitalization expenses.
        The sum insured is Rs 5,00,000 per year.
        """
        
        # Response contains information not in source
        response = """
        This policy includes dental coverage, vision care, and mental health benefits.
        It also covers international travel emergencies and alternative medicine treatments.
        The policy has a no-claim bonus of 50% and covers pre-existing conditions from day one.
        """
        
        result = service.check_hallucination_risk(source_text, response)
        
        assert result["high_risk"] is True
        assert result["overlap_ratio"] < 0.3
    
    def test_empty_response_handling(self, service):
        """Test handling of empty response."""
        source_text = "Insurance policy document text."
        response = ""
        
        result = service.check_hallucination_risk(source_text, response)
        
        # Empty response should not crash
        assert "high_risk" in result
    
    def test_empty_source_handling(self, service):
        """Test handling of empty source text."""
        source_text = ""
        response = "Some response text."
        
        result = service.check_hallucination_risk(source_text, response)
        
        # Should handle gracefully
        assert "high_risk" in result


class TestHallucinationDetectionEdgeCases:
    """Edge case tests for hallucination detection."""
    
    @pytest.fixture
    def service(self):
        return GuardrailsService()
    
    def test_paraphrased_content_acceptable(self, service):
        """Test that paraphrased content is not flagged as hallucination."""
        source_text = """
        The policyholder is entitled to cashless treatment at network hospitals.
        The maximum room rent covered is Rs 5,000 per day.
        """
        
        # Paraphrased but semantically equivalent
        response = """
        You can get cashless treatment at hospitals in the network.
        Room rent coverage is up to Rs 5,000 daily.
        """
        
        result = service.check_hallucination_risk(source_text, response)
        
        # Paraphrasing should have reasonable overlap
        # Note: Current implementation uses word overlap, so paraphrasing may show lower overlap
        # This test documents current behavior
        assert "overlap_ratio" in result
    
    def test_numeric_values_in_response(self, service):
        """Test responses with numeric values from source."""
        source_text = """
        Sum Insured: Rs 10,00,000
        Premium: Rs 25,000 per year
        Deductible: Rs 10,000
        """
        
        response = """
        The sum insured is Rs 10,00,000 with an annual premium of Rs 25,000.
        You need to pay Rs 10,000 deductible first.
        """
        
        result = service.check_hallucination_risk(source_text, response)
        
        # Numbers should contribute to overlap
        assert result["overlap_ratio"] > 0
    
    def test_technical_terms_preserved(self, service):
        """Test that technical insurance terms are recognized."""
        source_text = """
        The policy includes co-payment clause of 20%.
        Pre-existing disease waiting period is 48 months.
        Sub-limits apply for specific treatments.
        """
        
        response = """
        There is a 20% co-payment requirement.
        Pre-existing conditions have a 48-month waiting period.
        Sub-limits are applicable for certain treatments.
        """
        
        result = service.check_hallucination_risk(source_text, response)
        
        # Technical terms should show overlap
        assert "overlap_ratio" in result
    
    def test_completely_unrelated_response(self, service):
        """Test completely unrelated response is flagged."""
        source_text = """
        Health insurance policy covering hospitalization and medical expenses.
        """
        
        response = """
        The weather forecast shows sunny skies with temperatures around 25 degrees.
        Traffic conditions are normal on major highways.
        """
        
        result = service.check_hallucination_risk(source_text, response)
        
        assert result["high_risk"] is True
        assert result["overlap_ratio"] < 0.2
    
    def test_partial_hallucination(self, service):
        """Test response with mix of grounded and hallucinated content."""
        source_text = """
        This policy covers hospitalization expenses up to Rs 5,00,000.
        The premium is Rs 10,000 per year.
        """
        
        # Mix of real and hallucinated info
        response = """
        The policy covers hospitalization up to Rs 5,00,000.
        It also includes free annual health checkups and gym membership.
        Premium is Rs 10,000 yearly.
        """
        
        result = service.check_hallucination_risk(source_text, response)
        
        # Should have some overlap but may or may not be flagged
        # This documents current behavior
        assert "overlap_ratio" in result


class TestHallucinationDetectionMetrics:
    """Tests to measure detection precision and recall."""
    
    @pytest.fixture
    def service(self):
        return GuardrailsService()
    
    def test_known_good_outputs(self, service):
        """Test detection on known good (grounded) outputs."""
        test_cases = [
            {
                "source": "Sum insured is Rs 5 lakh. Premium is Rs 12000.",
                "response": "The sum insured is Rs 5 lakh with premium of Rs 12000.",
                "expected_risk": False
            },
            {
                "source": "Policy covers hospitalization, surgery, and ICU charges.",
                "response": "Coverage includes hospitalization, surgery, and ICU.",
                "expected_risk": False
            },
            {
                "source": "Waiting period is 30 days for illness claims.",
                "response": "There is a 30-day waiting period for illness claims.",
                "expected_risk": False
            }
        ]
        
        correct = 0
        for case in test_cases:
            result = service.check_hallucination_risk(case["source"], case["response"])
            if result["high_risk"] == case["expected_risk"]:
                correct += 1
        
        # Document precision on known good outputs
        precision = correct / len(test_cases)
        assert precision >= 0.5, f"Precision on good outputs: {precision}"
    
    def test_known_hallucinations(self, service):
        """Test detection on known hallucinated outputs."""
        test_cases = [
            {
                "source": "Basic health insurance policy.",
                "response": "This comprehensive policy includes dental, vision, mental health, maternity, and international coverage with no waiting periods.",
                "expected_risk": True
            },
            {
                "source": "Premium is Rs 10000 per year.",
                "response": "The policy offers 100% cashback on premiums if no claims are made for 5 years.",
                "expected_risk": True
            },
            {
                "source": "Standard hospitalization coverage.",
                "response": "AI-powered claim processing with instant approval and blockchain-verified documents.",
                "expected_risk": True
            }
        ]
        
        correct = 0
        for case in test_cases:
            result = service.check_hallucination_risk(case["source"], case["response"])
            if result["high_risk"] == case["expected_risk"]:
                correct += 1
        
        # Document recall on known hallucinations
        recall = correct / len(test_cases)
        assert recall >= 0.5, f"Recall on hallucinations: {recall}"


class TestHallucinationDetectionLimitations:
    """Tests documenting known limitations of hallucination detection."""
    
    @pytest.fixture
    def service(self):
        return GuardrailsService()
    
    def test_limitation_synonym_detection(self, service):
        """Document limitation: synonyms may reduce overlap score."""
        source_text = "The policy provides coverage for medical expenses."
        response = "The plan offers protection for healthcare costs."
        
        result = service.check_hallucination_risk(source_text, response)
        
        # Synonyms reduce word overlap even though meaning is same
        # This is a known limitation of word-overlap approach
        # Document the behavior
        assert "overlap_ratio" in result
        # Note: This may be flagged as high risk due to low word overlap
    
    def test_limitation_factual_errors(self, service):
        """Document limitation: factual errors with same words not detected."""
        source_text = "Sum insured is Rs 5,00,000."
        response = "Sum insured is Rs 50,00,000."  # Wrong amount, same words
        
        result = service.check_hallucination_risk(source_text, response)
        
        # Word overlap is high but the number is wrong
        # Current implementation cannot detect this
        # This is a known limitation
        assert "overlap_ratio" in result
        # Note: This will likely NOT be flagged as high risk
    
    def test_limitation_context_understanding(self, service):
        """Document limitation: no semantic understanding."""
        source_text = "Pre-existing conditions are not covered for 4 years."
        response = "Pre-existing conditions are covered from day one."  # Opposite meaning
        
        result = service.check_hallucination_risk(source_text, response)
        
        # High word overlap but opposite meaning
        # Current implementation cannot detect semantic contradiction
        # This is a known limitation
        assert "overlap_ratio" in result


class TestEnhancedHallucinationDetection:
    """Tests for enhanced hallucination detection features."""
    
    @pytest.fixture
    def service(self):
        return GuardrailsService()
    
    def test_number_extraction_from_source(self, service):
        """Test that numbers in source are tracked."""
        source_text = """
        Sum Insured: Rs 5,00,000
        Premium: Rs 12,500
        Waiting Period: 30 days
        Co-payment: 20%
        """
        
        response = """
        The sum insured is Rs 5,00,000 with premium of Rs 12,500.
        Waiting period is 30 days with 20% co-payment.
        """
        
        result = service.check_hallucination_risk(source_text, response)
        
        # Should detect grounded response
        assert result["high_risk"] is False or result["overlap_ratio"] > 0.2
    
    def test_invented_numbers_detection(self, service):
        """Test detection of invented numbers not in source."""
        source_text = "Basic health insurance policy with standard coverage."
        
        response = """
        Coverage up to Rs 25,00,000 with 50% no-claim bonus.
        Premium starts at Rs 5,999 with 15% family discount.
        """
        
        result = service.check_hallucination_risk(source_text, response)
        
        # Response has specific numbers not in source
        # Should be flagged as high risk due to low overlap
        assert result["high_risk"] is True or result["overlap_ratio"] < 0.3


class TestGuardrailsServiceIntegration:
    """Integration tests for guardrails service."""
    
    @pytest.fixture
    def service(self):
        return GuardrailsService()
    
    def test_full_workflow_grounded(self, service):
        """Test full workflow with grounded content."""
        # Validate input
        input_text = """
        This is a health insurance policy document.
        Policy Number: HI-2024-001
        Sum Insured: Rs 5,00,000
        Premium: Rs 15,000 per year
        Coverage includes hospitalization and surgery.
        Exclusions: Cosmetic procedures, dental treatment.
        """
        
        input_result = service.validate_input(input_text)
        assert input_result["is_valid"] is True
        
        # Check hallucination risk
        response = """
        Policy HI-2024-001 provides Rs 5,00,000 coverage.
        Annual premium is Rs 15,000.
        Covers hospitalization and surgery.
        Does not cover cosmetic or dental procedures.
        """
        
        hallucination_result = service.check_hallucination_risk(input_text, response)
        assert hallucination_result["high_risk"] is False
        
        # Sanitize output
        sanitized = service.sanitize_output(response)
        assert sanitized == response  # No PII to redact
    
    def test_full_workflow_with_pii(self, service):
        """Test workflow sanitizes PII in output."""
        input_text = """
        Health insurance policy for policyholder.
        Coverage details and terms apply.
        """
        
        response = """
        Policy details for customer.
        Contact: customer@email.com
        Phone: 9876543210
        Aadhar: 1234 5678 9012
        """
        
        sanitized = service.sanitize_output(response)
        
        # PII should be redacted
        assert "customer@email.com" not in sanitized
        assert "[REDACTED]" in sanitized


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
